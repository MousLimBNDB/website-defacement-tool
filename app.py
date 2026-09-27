import os
import shutil
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import sys

# Reconfigure standard streams to UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import database
import scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("monitoring.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# Request schemas for FastAPI validation
class TargetCreate(BaseModel):
    url: str
    name: str

class TargetUpdate(BaseModel):
    url: str
    name: str

class ToggleTarget(BaseModel):
    is_active: bool

class SettingsUpdate(BaseModel):
    webhook_url: str = ""
    webhook_payload_format: str = "n8n"  # 'n8n', 'standard', 'detailed'
    webhook_trigger_on: str = "defacement"  # 'defacement', 'anomaly', 'all'
    check_interval: float = 5.0
    check_interval_unit: str = "minutes"  # 'seconds', 'minutes', 'hours', 'days'
    similarity_threshold: float = 0.98
    use_llm: bool = True
    browser_engine: str = "firefox"  # 'firefox', 'chromium', 'auto'
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2-vision"

class WebhookTestRequest(BaseModel):
    webhook_url: str
    webhook_payload_format: str = "n8n"

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database and background scheduler on startup...")
    database.init_db()

    os.makedirs("static/screenshots", exist_ok=True)

    scheduler.start_scheduler()
    yield
    logger.info("Shutting down background scheduler...")
    scheduler.stop_scheduler()

app = FastAPI(title="Website Defacement Watcher", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serves the front-end dashboard Single Page Application (SPA)."""
    return FileResponse("templates/index.html")

# --- Target Management Endpoints ---

@app.get("/api/targets")
async def get_targets():
    return database.get_targets()

@app.post("/api/targets")
async def add_new_target(target: TargetCreate):
    url = target.url.strip()
    name = target.name.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    target_id = database.add_target(url, name)
    if not target_id:
        raise HTTPException(status_code=400, detail="Failed to add target website.")

    scheduler.sync_scheduler_jobs()
    return {"status": "success", "id": target_id}

@app.put("/api/targets/{target_id}")
async def update_existing_target(target_id: int, request: TargetUpdate):
    target = database.get_target(target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found.")

    url = request.url.strip()
    name = request.name.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    database.update_target(target_id, url, name)
    scheduler.sync_scheduler_jobs()
    return {"status": "success", "id": target_id}

@app.post("/api/targets/{target_id}/toggle")
async def toggle_target(target_id: int, request: ToggleTarget):
    target = database.get_target(target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found.")

    database.update_target_status(target_id, 1 if request.is_active else 0)
    scheduler.sync_scheduler_jobs()
    return {"status": "success", "is_active": request.is_active}

@app.post("/api/targets/{target_id}/reset-baseline")
async def reset_target_baseline(target_id: int, background_tasks: BackgroundTasks):
    target = database.get_target(target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found.")

    latest_log = database.get_latest_log(target_id)
    baseline_path = f"static/screenshots/{target_id}/baseline.png"

    if latest_log and latest_log.get('screenshot_path'):
        current_img_path = latest_log['screenshot_path'].lstrip('/')
        try:
            shutil.copy(current_img_path, baseline_path)
            logger.info(f"Updated baseline image for target {target_id} using {current_img_path}")

            database.add_log(
                target_id=target_id,
                similarity_score=1.0,
                is_defaced=0,
                confidence=0,
                change_type="Baseline Reset",
                analysis_summary="Baseline reset manually by administrator.",
                screenshot_path=f"/static/screenshots/{target_id}/baseline.png",
                diff_path="",
                status="SUCCESS"
            )
            return {"status": "success", "message": "Baseline updated successfully."}
        except Exception as e:
            logger.error(f"Failed to reset baseline for target {target_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to copy image to baseline.")
    else:
        logger.info(f"No current screenshot found to use as baseline. Triggering immediate check.")
        background_tasks.add_task(scheduler.run_check_for_target, target_id)
        return {"status": "triggered", "message": "Check triggered immediately to establish baseline."}

@app.delete("/api/targets/{target_id}")
async def delete_monitored_target(target_id: int):
    target = database.get_target(target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found.")

    database.delete_target(target_id)

    target_dir = f"static/screenshots/{target_id}"
    if os.path.exists(target_dir):
        try:
            shutil.rmtree(target_dir)
        except Exception as e:
            logger.error(f"Failed to delete screenshot folder {target_dir}: {e}")

    scheduler.sync_scheduler_jobs()
    return {"status": "success", "message": "Target deleted successfully."}

# --- Logs & Stats Endpoints ---

@app.get("/api/logs")
async def get_logs(target_id: int = None, limit: int = 50):
    return database.get_logs(target_id, limit)

@app.get("/api/stats")
async def get_dashboard_stats():
    targets = database.get_targets()
    logs = database.get_logs(limit=100)

    total_sites = len(targets)
    active_sites = sum(1 for t in targets if t['is_active'])
    total_checks = len(database.get_logs(limit=10000))

    active_defacements = 0
    for target in targets:
        latest = database.get_latest_log(target['id'])
        if latest and latest['is_defaced'] == 1:
            active_defacements += 1

    success_checks = sum(1 for l in logs if l['status'] == 'SUCCESS')
    success_rate = (success_checks / len(logs) * 100) if logs else 100

    return {
        "total_sites": total_sites,
        "active_sites": active_sites,
        "total_checks": total_checks,
        "active_defacements": active_defacements,
        "system_status": "DEFACEMENT_ALERT" if active_defacements > 0 else "SECURE",
        "reliability_rate": round(success_rate, 1)
    }

# --- Settings & Webhook Endpoints ---

@app.get("/api/settings")
async def get_system_settings():
    return database.get_settings()

@app.post("/api/settings")
async def update_system_settings(settings: SettingsUpdate):
    settings_dict = settings.model_dump()
    database.save_settings(settings_dict)

    scheduler.sync_scheduler_jobs()
    return {"status": "success", "message": "Settings updated successfully."}

@app.post("/api/test-webhook")
async def test_webhook_endpoint(request: WebhookTestRequest):
    """Sends a sample test alert payload to the user's n8n webhook URL to verify connection."""
    url = request.webhook_url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Webhook URL is empty.")

    payload = scheduler.build_webhook_payload(
        target_id=999,
        name="n8n Integration Test Site",
        url="https://n8n.io",
        similarity_score=0.885,
        is_defaced=True,
        confidence=98,
        change_type="Test Defacement Alert",
        summary="Test notification payload sent from Website Defacement Sentinel to verify n8n Webhook connection.",
        screenshot_path="/static/screenshots/demo/current.png",
        diff_path="/static/screenshots/demo/diff.png",
        popup_path="",
        format_type=request.webhook_payload_format
    )

    res = scheduler.send_webhook_alert(payload, url)
    if res.get("status") == "success":
        return {"status": "success", "message": res.get("message")}
    else:
        raise HTTPException(status_code=400, detail=res.get("message", "Failed to connect to Webhook."))

if __name__ == "__main__":
    import uvicorn
    database.init_db()
    uvicorn.run(app, host="127.0.0.1", port=8000)
