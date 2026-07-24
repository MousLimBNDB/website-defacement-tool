import os
import logging
import asyncio
from datetime import datetime
import json
import urllib.request
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# pyrefly: ignore [missing-import]
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import database
import screenshot_engine
import image_comparator
import ai_analyzer

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()

async def run_check_for_target(target_id: int):
    """
    Performs a full monitoring check on a single target website.
    This includes capturing, comparing, analyzing via LLM (if needed), and alerting.
    """
    target = database.get_target(target_id)
    if not target or not target['is_active']:
        logger.info(f"Target ID {target_id} not found or inactive. Skipping.")
        return
        
    url = target['url']
    name = target['name']
    logger.info(f"Running monitoring check for {name} ({url})")
    
    # Establish folders
    target_dir = f"screenshots/{target_id}"
    os.makedirs(target_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    baseline_path = f"{target_dir}/baseline.png"
    current_path = f"{target_dir}/current_{timestamp}.png"
    diff_path = f"{target_dir}/diff_{timestamp}.png"
    
    # Relative paths for database storage and dashboard serving
    rel_current_path = f"static/screenshots/{target_id}/current_{timestamp}.png"
    rel_diff_path = f"static/screenshots/{target_id}/diff_{timestamp}.png"
    
    # 1. Capture the current screenshot
    # Note: FastAPI static serving will link from static/screenshots to local screenshots directory
    # So we'll save screenshots directly to a path that is accessible.
    # Let's save them under static/screenshots so FastAPI can serve them static-file-wise.
    static_target_dir = f"static/screenshots/{target_id}"
    os.makedirs(static_target_dir, exist_ok=True)
    
    baseline_path = f"{static_target_dir}/baseline.png"
    current_path = f"{static_target_dir}/current_{timestamp}.png"
    diff_path = f"{static_target_dir}/diff_{timestamp}.png"
    
    # Database relative paths for web rendering
    db_screenshot_path = f"/static/screenshots/{target_id}/current_{timestamp}.png"
    db_diff_path = f"/static/screenshots/{target_id}/diff_{timestamp}.png"
    
    success = await screenshot_engine.capture_screenshot(url, current_path)
    if not success:
        database.add_log(
            target_id=target_id,
            similarity_score=0.0,
            is_defaced=0,
            confidence=0,
            change_type="Error",
            analysis_summary="Failed to capture screenshot. The website might be offline or blocked.",
            screenshot_path="",
            diff_path="",
            status="FAILED",
            error_message="Playwright browser failed to capture page screenshot."
        )
        # Trigger an alert if the site is completely unreachable
        trigger_unreachable_alert(name, url)
        return
        
    # 2. Check if baseline exists. If not, set current as baseline and exit.
    if not os.path.exists(baseline_path):
        import shutil
        shutil.copy(current_path, baseline_path)
        logger.info(f"No baseline found for {name}. Setting current capture as baseline.")
        database.add_log(
            target_id=target_id,
            similarity_score=1.0,
            is_defaced=0,
            confidence=0,
            change_type="Baseline Created",
            analysis_summary="Baseline screenshot established. Future checks will be compared against this.",
            screenshot_path=f"/static/screenshots/{target_id}/baseline.png",
            diff_path="",
            status="SUCCESS"
        )
        return

    # 3. Compare current screenshot against baseline
    settings = database.get_settings()
    threshold = float(settings.get("similarity_threshold", 0.98))
    
    similarity = image_comparator.compare_screenshots(baseline_path, current_path, diff_path)
    
    # 4. Determine if we need to call the LLM
    is_defaced = 0
    confidence = 0
    change_type = "No Change"
    analysis_summary = f"No meaningful visual changes detected. Similarity score: {similarity:.4f}"
    
    # If similarity is below the threshold, invoke AI visual analysis
    if similarity < threshold:
        logger.info(f"Similarity score {similarity:.4f} is below threshold {threshold}. Querying AI provider...")
        analysis = ai_analyzer.analyze_defacement(baseline_path, current_path, diff_path)
        
        is_defaced = 1 if analysis.get("is_defaced") else 0
        confidence = analysis.get("confidence", 0)
        change_type = analysis.get("change_type", "Unknown")
        analysis_summary = analysis.get("analysis_summary", "")
        
        # 5. Trigger alerting if Gemini confirms defacement
        if is_defaced:
            trigger_defacement_alert(name, url, change_type, confidence, analysis_summary)
    else:
        logger.info(f"Similarity score {similarity:.4f} is above threshold {threshold}. Skipping LLM.")
        
    # 6. Save log details to DB
    database.add_log(
        target_id=target_id,
        similarity_score=similarity,
        is_defaced=is_defaced,
        confidence=confidence,
        change_type=change_type,
        analysis_summary=analysis_summary,
        screenshot_path=db_screenshot_path,
        diff_path=db_diff_path if similarity < threshold else "",
        status="SUCCESS"
    )

def trigger_defacement_alert(target_name: str, url: str, change_type: str, confidence: int, summary: str):
    logger.warning(f"🚨 DEFACEMENT DETECTED for {target_name} ({url})! Confidence: {confidence}%. Type: {change_type}")
    
    settings = database.get_settings()
    webhook_url = settings.get("webhook_url")
    email_to = settings.get("alert_email_to")
    
    # Send Discord / Slack Webhook alert
    if webhook_url:
        try:
            payload = {
                "content": f"🚨 **Website Defacement Alert!** 🚨\n**Site**: {target_name} ({url})\n**Change Type**: {change_type}\n**AI Confidence**: {confidence}%\n**Summary**: {summary}"
            }
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json', 'User-Agent': 'DefacementWatcher'}
            )
            with urllib.request.urlopen(req) as response:
                logger.info("Alert webhook sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")

    # Send Email alert
    if email_to:
        send_email_alert(
            to_email=email_to,
            subject=f"🚨 DEFACEMENT ALERT: {target_name}",
            body=f"Website defacement warning for {target_name} ({url})\n\nDetails:\n- Classification: {change_type}\n- AI Confidence: {confidence}%\n- Summary: {summary}\n\nPlease check your monitoring dashboard immediately."
        )

def trigger_unreachable_alert(target_name: str, url: str):
    logger.warning(f"⚠️ Website unreachable alert: {target_name} ({url})")
    settings = database.get_settings()
    webhook_url = settings.get("webhook_url")
    email_to = settings.get("alert_email_to")
    
    if webhook_url:
        try:
            payload = {
                "content": f"⚠️ **Website Unreachable Alert!** ⚠️\n**Site**: {target_name} ({url})\nFailed to capture screenshot. The site might be offline."
            }
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json', 'User-Agent': 'DefacementWatcher'}
            )
            with urllib.request.urlopen(req) as response:
                pass
        except Exception as e:
            logger.error(f"Failed to send webhook unreachable alert: {e}")

    if email_to:
        send_email_alert(
            to_email=email_to,
            subject=f"⚠️ UNREACHABLE ALERT: {target_name}",
            body=f"Failed to connect to and screenshot website: {target_name} ({url}). The site might be down."
        )

def send_email_alert(to_email: str, subject: str, body: str):
    settings = database.get_settings()
    smtp_host = settings.get("smtp_host")
    smtp_port = int(settings.get("smtp_port", 587))
    smtp_user = settings.get("smtp_user")
    smtp_pass = settings.get("smtp_password")
    
    if not smtp_host or not smtp_user or not smtp_pass:
        logger.info("SMTP configuration incomplete. Email alert skipped.")
        return
        
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()
        logger.info("Alert email sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")

# Scheduler orchestration
def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started successfully.")
        sync_scheduler_jobs()

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped.")

def sync_scheduler_jobs():
    """Reads active targets from DB and schedules them at the configured interval."""
    # Remove existing jobs
    scheduler.remove_all_jobs()
    
    settings = database.get_settings()
    interval_mins = int(settings.get("check_interval_mins", 5))
    
    targets = database.get_targets()
    active_count = 0
    now = datetime.now()
    for target in targets:
        if target['is_active']:
            # Run first check immediately, then check every N minutes
            job_id = f"check_{target['id']}"
            scheduler.add_job(
                func=run_check_for_target,
                args=[target['id']],
                trigger="interval",
                minutes=interval_mins,
                id=job_id,
                replace_existing=True,
                next_run_time=now
            )
            active_count += 1
            logger.info(f"Scheduled check job for {target['name']} every {interval_mins} minutes.")
            
    logger.info(f"Synchronized scheduler jobs. Active targets monitoring: {active_count}")
