import sys
import json
import logging
import argparse

import database

logger = logging.getLogger(__name__)

def log_normal_event(
    target_id: int,
    url: str,
    similarity_score: float,
    screenshot_path: str = "",
    diff_path: str = "",
    popup_path: str = "",
    is_baseline: bool = False
) -> dict:
    """
    Node 8: Log Normal Event.
    Persists normal monitoring checks and baseline establishments to PostgreSQL defacement_logs table.
    """
    change_type = "Baseline Established" if is_baseline else "No Change"
    summary = (
        "Clean baseline snapshot initialized." if is_baseline else
        f"Site visual integrity verified. Similarity score: {similarity_score:.4f}."
    )
    status = "BASELINE" if is_baseline else "NORMAL"

    log_id = database.add_log(
        target_id=target_id,
        url=url,
        similarity_score=similarity_score,
        is_defaced=False,
        confidence=0,
        change_type=change_type,
        analysis_summary=summary,
        screenshot_path=screenshot_path,
        diff_path=diff_path,
        popup_screenshot_path=popup_path,
        status=status
    )

    logger.info(f"[Target {target_id}] Normal event logged to database (Log ID: {log_id})")

    return {
        "event_logged": True,
        "log_id": log_id,
        "target_id": target_id,
        "url": url,
        "status": status,
        "similarity_score": similarity_score,
        "summary": summary
    }

def main():
    parser = argparse.ArgumentParser(description="Node 8: Log Normal Event into PostgreSQL for n8n")
    parser.add_argument("--target-id", type=int, required=True, help="Target ID")
    parser.add_argument("--url", required=True, help="Target website URL")
    parser.add_argument("--similarity", type=float, default=1.0, help="Similarity score (0.0 - 1.0)")
    parser.add_argument("--screenshot", default="", help="Current screenshot path")
    parser.add_argument("--diff", default="", help="Visual diff screenshot path")
    parser.add_argument("--popup", default="", help="Popup screenshot path")
    parser.add_argument("--baseline-created", action="store_true", help="Set if this capture was set as baseline")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    res = log_normal_event(
        target_id=args.target_id,
        url=args.url,
        similarity_score=args.similarity,
        screenshot_path=args.screenshot,
        diff_path=args.diff,
        popup_path=args.popup,
        is_baseline=args.baseline_created
    )
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
