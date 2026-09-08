import os
import sys
import json
import logging
import asyncio
import argparse
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
import database
import node_targets
import screenshot_engine
import image_comparator
import node_similarity_check
import ollama_analyzer
import node_alert
import node_logger

logger = logging.getLogger(__name__)

# Global APScheduler instance
scheduler = AsyncIOScheduler()

async def execute_monitoring_pipeline_for_target(target: dict) -> dict:
    """
    Executes the full end-to-end defacement monitoring pipeline for a single target.
    This exactly mirrors the n8n node flow.
    """
    target_id = target.get("id", 1)
    url = target.get("url")
    name = target.get("name", url)
    ignored_selectors = target.get("ignored_selectors", "")
    target_selectors = target.get("target_selectors", "")

    logger.info(f"===> [Target {target_id}: {name}] Starting monitoring check for {url}")

    # Node 3: Playwright Screenshot Engine
    capture_res = await screenshot_engine.capture_website(
        url=url,
        target_id=target_id,
        ignored_selectors=ignored_selectors,
        target_selectors=target_selectors
    )

    if not capture_res.get("success"):
        error_msg = capture_res.get("error", "Failed to capture screenshot")
        logger.error(f"[Target {target_id}] Capture failed: {error_msg}")
        database.add_log(
            target_id=target_id,
            url=url,
            similarity_score=0.0,
            is_defaced=False,
            confidence=0,
            change_type="Connection/Capture Error",
            analysis_summary=f"Playwright screenshot capture failed: {error_msg}",
            status="FAILED",
            error_message=error_msg
        )
        return {"status": "FAILED", "error": error_msg}

    current_path = capture_res["current_path"]
    baseline_path = capture_res["baseline_path"]
    popup_path = capture_res.get("popup_path", "")
    timestamp = capture_res["timestamp"]

    # If baseline was just created, log baseline event and finish
    if capture_res.get("is_baseline_created"):
        logger.info(f"[Target {target_id}] Baseline image initialized. Logging event.")
        node_logger.log_normal_event(
            target_id=target_id,
            url=url,
            similarity_score=1.0,
            screenshot_path=current_path,
            popup_path=popup_path,
            is_baseline=True
        )
        return {"status": "BASELINE_INITIALIZED", "target_id": target_id}

    # Node 4: Pillow Image Comparator (Canvas Expansion)
    diff_dir = config.SCREENSHOTS_DIR / str(target_id)
    diff_path = str(diff_dir / f"diff_{timestamp}.png")
    
    comp_res = image_comparator.compare_screenshots(
        baseline_path=baseline_path,
        current_path=current_path,
        diff_path=diff_path,
        threshold=config.PIXEL_DIFF_THRESHOLD
    )
    similarity = comp_res.get("similarity_score", 0.0)

    # Node 5: Similarity Score Check & Threshold Router
    route_info = node_similarity_check.check_similarity(
        similarity=similarity,
        threshold=config.SIMILARITY_THRESHOLD,
        target_id=target_id,
        url=url,
        baseline_path=baseline_path,
        current_path=current_path,
        diff_path=diff_path,
        popup_path=popup_path
    )

    # Branching logic
    if route_info["is_below_threshold"]:
        logger.warning(
            f"[Target {target_id}] Similarity {similarity:.4f} < Threshold {config.SIMILARITY_THRESHOLD}. "
            "Routing to Ollama Multimodal AI Engine..."
        )
        
        # Node 6: Multimodal AI Engine (Ollama Qwen3:4B on VM)
        ai_res = ollama_analyzer.analyze_defacement(
            baseline_path=baseline_path,
            current_path=current_path,
            diff_path=diff_path,
            popup_path=popup_path,
            target_id=target_id,
            url=url
        )

        is_defaced = ai_res.get("is_defaced", False)
        popup_defaced = ai_res.get("popup_defaced", False)
        confidence = ai_res.get("confidence", 0)
        change_type = ai_res.get("change_type", "Unknown")
        summary = ai_res.get("analysis_summary", "")

        if is_defaced or popup_defaced:
            # Node 7: Incident Alerting Engine (Webhook + DB)
            logger.critical(f"🚨 DEFACEMENT CONFIRMED for {url}! Triggering alerts...")
            alert_res = node_alert.trigger_alert(
                target_id=target_id,
                url=url,
                change_type=change_type,
                confidence=confidence,
                summary=summary,
                similarity_score=similarity,
                screenshot_path=current_path,
                diff_path=diff_path,
                popup_path=popup_path
            )
            return {"status": "DEFACEMENT_ALERTED", "alert": alert_res}
        else:
            logger.info(f"[Target {target_id}] AI determined change is benign: {change_type}")
            node_logger.log_normal_event(
                target_id=target_id,
                url=url,
                similarity_score=similarity,
                screenshot_path=current_path,
                diff_path=diff_path,
                popup_path=popup_path,
                is_baseline=False
            )
            return {"status": "BENIGN_CHANGE_LOGGED", "change_type": change_type}
    else:
        # Node 8: Log Normal Event
        logger.info(f"[Target {target_id}] Similarity {similarity:.4f} >= Threshold. Visual integrity intact.")
        node_logger.log_normal_event(
            target_id=target_id,
            url=url,
            similarity_score=similarity,
            screenshot_path=current_path,
            diff_path="",
            popup_path=popup_path,
            is_baseline=False
        )
        return {"status": "NORMAL_LOGGED", "similarity": similarity}

async def run_all_targets_once():
    """Runs one monitoring iteration across all active targets."""
    targets = node_targets.get_targets(active_only=True)
    logger.info(f"Running monitoring iteration for {len(targets)} active targets...")
    for target in targets:
        try:
            await execute_monitoring_pipeline_for_target(target)
        except Exception as e:
            logger.error(f"Error checking target {target.get('id')}: {e}", exc_info=True)

def start_continuous_scheduler():
    """Starts APScheduler with interval triggers for continuous background execution."""
    database.init_db()
    targets = node_targets.get_targets(active_only=True)
    
    for target in targets:
        t_id = target.get("id")
        mins = target.get("check_interval_mins", 5)
        job_id = f"job_target_{t_id}"
        scheduler.add_job(
            func=execute_monitoring_pipeline_for_target,
            args=[target],
            trigger="interval",
            minutes=mins,
            id=job_id,
            replace_existing=True,
            next_run_time=datetime.now()
        )
        logger.info(f"Scheduled monitoring job for Target {t_id} ({target.get('name')}) every {mins} mins.")

    scheduler.start()
    logger.info("APScheduler interval runner is active.")

def main():
    parser = argparse.ArgumentParser(description="Node 2: APScheduler Pipeline Runner")
    parser.add_argument("--run-once", action="store_true", help="Execute single check across active targets and exit")
    parser.add_argument("--target-id", type=int, default=None, help="Check only specific target ID")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    database.init_db()

    if args.target_id:
        targets = node_targets.get_targets(target_id=args.target_id)
        if not targets:
            print(f"Target ID {args.target_id} not found.")
            return
        asyncio.run(execute_monitoring_pipeline_for_target(targets[0]))
    elif args.run_once:
        asyncio.run(run_all_targets_once())
    else:
        start_continuous_scheduler()
        try:
            asyncio.get_event_loop().run_forever()
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
            logger.info("Scheduler stopped.")

if __name__ == "__main__":
    main()
