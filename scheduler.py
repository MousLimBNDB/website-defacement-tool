import os
import logging
import asyncio
from datetime import datetime
import json
import urllib.request
import urllib.error

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import database
import screenshot_engine
import image_comparator
import ai_analyzer

logger = logging.getLogger(__name__)

# Global APScheduler instance
scheduler = AsyncIOScheduler()

def build_webhook_payload(
    target_id: int,
    name: str,
    url: str,
    similarity_score: float,
    is_defaced: bool,
    confidence: int,
    change_type: str,
    summary: str,
    screenshot_path: str,
    diff_path: str,
    popup_path: str,
    format_type: str = "n8n"
) -> dict:
    """
    Constructs structured JSON data payload for n8n/custom webhook based on configured format.
    Formats: 'n8n', 'standard', 'detailed'.
    """
    timestamp_str = datetime.now().isoformat()

    if format_type == "standard":
        return {
            "event": "defacement_detected" if is_defaced else "audit_check_event",
            "site": name,
            "url": url,
            "similarity": similarity_score,
            "change_type": change_type,
            "confidence": confidence,
            "summary": summary,
            "timestamp": timestamp_str
        }
    elif format_type == "detailed":
        return {
            "version": "1.0",
            "pipeline": "website_defacement_tool",
            "target": {
                "id": target_id,
                "name": name,
                "url": url
            },
            "metrics": {
                "similarity_score": similarity_score,
                "confidence": confidence,
                "is_defaced": is_defaced
            },
            "analysis": {
                "change_type": change_type,
                "summary": summary
            },
            "artifacts": {
                "current_screenshot": screenshot_path,
                "visual_diff": diff_path,
                "isolated_popup": popup_path
            },
            "timestamp": timestamp_str
        }
    else:  # Default: 'n8n' format
        return {
            "target_id": target_id,
            "target_name": name,
            "target_url": url,
            "status": "DEFACEMENT_ALERT" if is_defaced else "AUDIT_CHECK",
            "similarity_score": similarity_score,
            "is_defaced": is_defaced,
            "confidence": confidence,
            "change_type": change_type,
            "analysis_summary": summary,
            "screenshot_path": screenshot_path,
            "diff_path": diff_path,
            "popup_path": popup_path,
            "timestamp": timestamp_str
        }

def send_webhook_alert(payload: dict, webhook_url: str) -> dict:
    """
    Sends JSON payload to the configured n8n / webhook endpoint.
    Returns result dict with status and detailed HTTP diagnostic code / message.
    """
    if not webhook_url or not webhook_url.strip():
        logger.info("No webhook URL configured. Skipping webhook transmission.")
        return {"status": "skipped", "message": "No webhook URL configured."}

    webhook_url = webhook_url.strip()
    try:
        req_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            webhook_url,
            data=req_data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'DefacementWatcher-n8n-Integration'
            }
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            http_code = response.status
            logger.info(f"Successfully delivered alert payload to webhook ({webhook_url}). HTTP status: {http_code}")
            return {
                "status": "success",
                "http_code": http_code,
                "message": f"Successfully delivered payload to n8n webhook (HTTP {http_code})!"
            }
    except urllib.error.HTTPError as he:
        if he.code == 404:
            diag = (
                f"n8n Webhook Error HTTP 404 (Not Found):\n"
                f"• If using n8n Test URL (contains '/webhook-test/'): Click 'Listen for Test Event' inside n8n workflow editor first.\n"
                f"• If using n8n Production URL (contains '/webhook/'): Ensure your n8n workflow toggle switch is set to ACTIVE."
            )
        elif he.code == 405:
            diag = (
                f"n8n Webhook Error HTTP 405 (Method Not Allowed):\n"
                f"• In your n8n Webhook Node parameters, change 'HTTP Method' from GET to POST."
            )
        elif he.code in (401, 403):
            diag = f"n8n Webhook Error HTTP {he.code}: Endpoint requires authentication credentials."
        else:
            diag = f"n8n Webhook Error HTTP {he.code}: {he.reason}"

        logger.error(diag)
        return {"status": "error", "http_code": he.code, "message": diag}
    except urllib.error.URLError as ue:
        diag = (
            f"n8n Webhook Connection Error: {ue.reason}.\n"
            f"• Check that n8n is running and accessible at '{webhook_url}'.\n"
            f"• If running n8n in Docker or WSL VM, use the host IP (e.g. http://172.17.0.1:5678/...) instead of localhost."
        )
        logger.error(diag)
        return {"status": "error", "http_code": 0, "message": diag}
    except Exception as e:
        diag = f"Failed to deliver payload to webhook '{webhook_url}': {e}"
        logger.error(diag)
        return {"status": "error", "http_code": 0, "message": diag}

async def run_check_for_target(target_id: int):
    """
    Performs full monitoring check on a target website.
    Flow: Capture -> Compare Canvas -> AI Evaluation -> Webhook Alert -> DB Log.
    """
    target = database.get_target(target_id)
    if not target or not target['is_active']:
        logger.info(f"Target ID {target_id} not found or inactive. Skipping.")
        return

    url = target['url']
    name = target['name']
    logger.info(f"Running monitoring check for '{name}' ({url})")

    settings = database.get_settings()
    browser_engine = settings.get("browser_engine", "firefox")
    webhook_url = settings.get("webhook_url", "").strip()
    payload_format = settings.get("webhook_payload_format", "n8n")
    webhook_trigger_on = settings.get("webhook_trigger_on", "defacement").lower()

    static_target_dir = f"static/screenshots/{target_id}"
    os.makedirs(static_target_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    baseline_path = f"{static_target_dir}/baseline.png"
    current_path = f"{static_target_dir}/current_{timestamp}.png"
    diff_path = f"{static_target_dir}/diff_{timestamp}.png"
    popup_path = f"{static_target_dir}/popup_{timestamp}.png"

    db_screenshot_path = f"/static/screenshots/{target_id}/current_{timestamp}.png"
    db_diff_path = f"/static/screenshots/{target_id}/diff_{timestamp}.png"
    db_popup_path = f"/static/screenshots/{target_id}/popup_{timestamp}.png"

    # 1. Capture current screenshot
    capture_res = await screenshot_engine.capture_screenshot(
        url=url,
        output_path=current_path,
        popup_output_path=popup_path,
        browser_engine=browser_engine
    )

    if not capture_res.get("success"):
        error_msg = capture_res.get("error", "Failed to capture page screenshot.")
        logger.error(f"Target '{name}' ({url}) capture failed: {error_msg}")
        database.add_log(
            target_id=target_id,
            similarity_score=0.0,
            is_defaced=0,
            confidence=0,
            change_type="Connection Error",
            analysis_summary=f"Failed to capture screenshot: {error_msg}",
            screenshot_path="",
            diff_path="",
            popup_path="",
            status="FAILED",
            error_message=error_msg
        )

        if webhook_url:
            payload = build_webhook_payload(
                target_id, name, url, 0.0, False, 0,
                "Connection Error", f"Site unreachable: {error_msg}",
                "", "", "", payload_format
            )
            send_webhook_alert(payload, webhook_url)
        return

    if not capture_res.get("popup_captured") or not os.path.exists(popup_path):
        db_popup_path = ""
        popup_path = ""

    # 2. Check baseline
    if not os.path.exists(baseline_path):
        import shutil
        shutil.copy(current_path, baseline_path)
        logger.info(f"Baseline created for '{name}'. Future checks will compare against this.")
        database.add_log(
            target_id=target_id,
            similarity_score=1.0,
            is_defaced=0,
            confidence=0,
            change_type="Baseline Created",
            analysis_summary="Baseline screenshot established.",
            screenshot_path=f"/static/screenshots/{target_id}/baseline.png",
            diff_path="",
            popup_path=db_popup_path,
            status="SUCCESS"
        )
        if webhook_url and webhook_trigger_on == "all":
            payload = build_webhook_payload(
                target_id, name, url, 1.0, False, 0,
                "Baseline Created", "Baseline screenshot established.",
                f"/static/screenshots/{target_id}/baseline.png", "", db_popup_path, payload_format
            )
            send_webhook_alert(payload, webhook_url)
        return

    # 3. Canvas expansion image comparison
    threshold = float(settings.get("similarity_threshold", 0.98))
    similarity = image_comparator.compare_screenshots(baseline_path, current_path, diff_path)

    # 4. Evaluate defacement
    is_defaced = 0
    confidence = 0
    change_type = "No Change"
    analysis_summary = f"No meaningful visual changes detected. Similarity score: {similarity:.4f}"

    if similarity < threshold:
        logger.info(f"Similarity {similarity:.4f} is below threshold {threshold}. Querying AI analyzer...")
        analysis = ai_analyzer.analyze_defacement(
            baseline_path=baseline_path,
            current_path=current_path,
            diff_path=diff_path,
            popup_path=popup_path
        )
        is_defaced = 1 if analysis.get("is_defaced") else 0
        confidence = analysis.get("confidence", 0)
        change_type = analysis.get("change_type", "Visual Anomaly")
        analysis_summary = analysis.get("analysis_summary", "")

        # Send Webhook on Defacement or Anomaly
        if webhook_url and (is_defaced or webhook_trigger_on in ("anomaly", "all")):
            logger.info(f"Sending webhook alert to '{webhook_url}' for target '{name}' (Defaced: {bool(is_defaced)})...")
            payload = build_webhook_payload(
                target_id, name, url, similarity, bool(is_defaced), confidence,
                change_type, analysis_summary, db_screenshot_path,
                db_diff_path, db_popup_path, payload_format
            )
            send_webhook_alert(payload, webhook_url)
    else:
        logger.info(f"Similarity {similarity:.4f} is above threshold {threshold}. Skipping AI evaluation.")
        if webhook_url and webhook_trigger_on == "all":
            payload = build_webhook_payload(
                target_id, name, url, similarity, False, 0,
                "No Change", analysis_summary, db_screenshot_path,
                "", db_popup_path, payload_format
            )
            send_webhook_alert(payload, webhook_url)

    # 5. Record log entry
    database.add_log(
        target_id=target_id,
        similarity_score=similarity,
        is_defaced=is_defaced,
        confidence=confidence,
        change_type=change_type,
        analysis_summary=analysis_summary,
        screenshot_path=db_screenshot_path,
        diff_path=db_diff_path if similarity < threshold else "",
        popup_path=db_popup_path,
        status="SUCCESS"
    )

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler background engine started.")
        sync_scheduler_jobs()

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler engine stopped.")

def sync_scheduler_jobs():
    """Reads active targets and settings from DB and schedules interval jobs with units."""
    scheduler.remove_all_jobs()

    settings = database.get_settings()
    try:
        check_interval = float(settings.get("check_interval", settings.get("check_interval_mins", 5)))
    except (ValueError, TypeError):
        check_interval = 5.0

    unit = str(settings.get("check_interval_unit", "minutes")).lower().strip()

    trigger_kwargs = {}
    if unit == "seconds":
        trigger_kwargs["seconds"] = max(5.0, check_interval)
    elif unit == "hours":
        trigger_kwargs["hours"] = max(0.1, check_interval)
    elif unit == "days":
        trigger_kwargs["days"] = max(1.0, check_interval)
    else:
        trigger_kwargs["minutes"] = max(0.5, check_interval)

    targets = database.get_targets()
    active_count = 0
    now = datetime.now()

    for target in targets:
        if target['is_active']:
            job_id = f"check_{target['id']}"
            scheduler.add_job(
                func=run_check_for_target,
                args=[target['id']],
                trigger="interval",
                id=job_id,
                replace_existing=True,
                next_run_time=now,
                **trigger_kwargs
            )
            active_count += 1
            logger.info(f"Scheduled check job for '{target['name']}' every {check_interval} {unit}.")

    logger.info(f"Synchronized APScheduler. Active monitoring targets: {active_count}")
