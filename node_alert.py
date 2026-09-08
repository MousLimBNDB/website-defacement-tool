import os
import sys
import json
import logging
import argparse
import urllib.request
from datetime import datetime

import config
import database

logger = logging.getLogger(__name__)

def trigger_alert(
    target_id: int,
    url: str,
    change_type: str,
    confidence: int,
    summary: str,
    similarity_score: float = 0.0,
    screenshot_path: str = "",
    diff_path: str = "",
    popup_path: str = "",
    webhook_url: str = None
) -> dict:
    """
    Node 7: Incident Alerting Engine.
    Dispatches defacement alerts to Webhook (Discord/Slack/n8n Webhook)
    and records the incident into PostgreSQL defacement_incidents table.
    """
    target_webhook = webhook_url or config.ALERT_WEBHOOK_URL
    alert_delivered = False
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Construct alert payload
    alert_payload = {
        "event": "DEFACEMENT_DETECTED",
        "timestamp": now_str,
        "target_id": target_id,
        "url": url,
        "change_type": change_type,
        "confidence": confidence,
        "similarity_score": similarity_score,
        "summary": summary,
        "screenshot_path": screenshot_path,
        "diff_path": diff_path,
        "popup_path": popup_path,
        "content": (
            f"🚨 **DEFACEMENT INCIDENT ALERT** 🚨\n"
            f"- **Target**: {url} (ID: {target_id})\n"
            f"- **Classification**: {change_type}\n"
            f"- **AI Confidence**: {confidence}%\n"
            f"- **Similarity**: {similarity_score:.4f}\n"
            f"- **Summary**: {summary}\n"
            f"- **Time**: {now_str}"
        )
    }

    # Send Webhook if URL is configured
    if target_webhook:
        try:
            req_data = json.dumps(alert_payload).encode("utf-8")
            req = urllib.request.Request(
                target_webhook,
                data=req_data,
                headers={"Content-Type": "application/json", "User-Agent": "DefacementMonitor/2.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                logger.info(f"Alert Webhook delivered successfully (HTTP {resp.status}).")
                alert_delivered = True
        except Exception as e:
            logger.error(f"Failed to deliver alert webhook: {e}")
    else:
        logger.info("No ALERT_WEBHOOK_URL configured. Alert logged to database only.")

    # Record incident in PostgreSQL / SQLite
    incident_id = database.add_incident(
        target_id=target_id,
        url=url,
        change_type=change_type,
        confidence=confidence,
        summary=summary,
        alert_sent=alert_delivered
    )

    # Also record in defacement_logs
    database.add_log(
        target_id=target_id,
        url=url,
        similarity_score=similarity_score,
        is_defaced=True,
        confidence=confidence,
        change_type=change_type,
        analysis_summary=summary,
        screenshot_path=screenshot_path,
        diff_path=diff_path,
        popup_screenshot_path=popup_path,
        status="DEFACED"
    )

    return {
        "alert_triggered": True,
        "incident_id": incident_id,
        "webhook_delivered": alert_delivered,
        "target_id": target_id,
        "url": url,
        "change_type": change_type,
        "confidence": confidence
    }

def main():
    parser = argparse.ArgumentParser(description="Node 7: Incident Alerting Engine (Webhook + PostgreSQL)")
    parser.add_argument("--target-id", type=int, required=True, help="Target ID")
    parser.add_argument("--url", required=True, help="Target website URL")
    parser.add_argument("--change-type", default="Defacement", help="Change classification")
    parser.add_argument("--confidence", type=int, default=95, help="AI Confidence score (0-100)")
    parser.add_argument("--summary", default="", help="Summary of defacement")
    parser.add_argument("--similarity", type=float, default=0.0, help="Visual similarity score")
    parser.add_argument("--screenshot", default="", help="Current screenshot path")
    parser.add_argument("--diff", default="", help="Visual diff screenshot path")
    parser.add_argument("--popup", default="", help="Popup screenshot path")
    parser.add_argument("--webhook", default=None, help="Webhook URL override")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    res = trigger_alert(
        target_id=args.target_id,
        url=args.url,
        change_type=args.change_type,
        confidence=args.confidence,
        summary=args.summary,
        similarity_score=args.similarity,
        screenshot_path=args.screenshot,
        diff_path=args.diff,
        popup_path=args.popup,
        webhook_url=args.webhook
    )
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
