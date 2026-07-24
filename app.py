import os
import shutil
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import sys

# Reconfigure standard streams to UTF-8 to prevent UnicodeEncodeError on Windows terminals
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

# Set up logging configuration
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

class ToggleTarget(BaseModel):
    is_active: bool

class SettingsUpdate(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    alert_email_to: str
    webhook_url: str
    check_interval_mins: int
    similarity_threshold: float
    ai_provider: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2-vision"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Initializing system on startup...")
    database.init_db()
    
    # Ensure static directories exist
    os.makedirs("static/screenshots", exist_ok=True)
    
    # Start APScheduler background jobs
    scheduler.start_scheduler()
    yield
    # Shutdown actions
    logger.info("Shutting down background scheduler...")
    scheduler.stop_scheduler()

app = FastAPI(title="Website Defacement Watcher", lifespan=lifespan)

# Mount static files to serve images and UI scripts
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
    # Quick URL validation helper
    url = target.url.strip()
    name = target.name.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
        
    target_id = database.add_target(url, name)
    if not target_id:
        raise HTTPException(status_code=400, detail="Failed to add target website.")
        
    # Re-sync scheduler jobs to schedule the new target
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
    """
    Sets the latest successful screenshot as the new baseline image.
    If no screenshots exist, it schedules an immediate capture run.
    """
    target = database.get_target(target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found.")
        
    latest_log = database.get_latest_log(target_id)
    baseline_path = f"static/screenshots/{target_id}/baseline.png"
    
    if latest_log and latest_log['screenshot_path']:
        current_img_path = latest_log['screenshot_path'].lstrip('/')
        # Copy current to baseline
        try:
            shutil.copy(current_img_path, baseline_path)
            logger.info(f"Updated baseline image for target {target_id} using {current_img_path}")
            
            # Insert a system log
            database.add_log(
                target_id=target_id,
                similarity_score=1.0,
                is_defaced=0,
                confidence=0,
                change_type="Baseline Reset",
                analysis_summary="Baseline reset manually by administrator. Future checks will use this new baseline.",
                screenshot_path=f"/static/screenshots/{target_id}/baseline.png",
                diff_path="",
                status="SUCCESS"
            )
            return {"status": "success", "message": "Baseline updated successfully."}
        except Exception as e:
            logger.error(f"Failed to reset baseline for target {target_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to copy image to baseline.")
    else:
        # No history screenshot available, trigger background check immediately to capture
        logger.info(f"No current screenshot found to use as baseline. Triggering immediate check.")
        background_tasks.add_task(scheduler.run_check_for_target, target_id)
        return {"status": "triggered", "message": "Check triggered immediately to establish baseline."}

@app.delete("/api/targets/{target_id}")
async def delete_monitored_target(target_id: int):
    target = database.get_target(target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found.")
        
    database.delete_target(target_id)
    
    # Delete screenshot assets folder
    target_dir = f"static/screenshots/{target_id}"
    if os.path.exists(target_dir):
        try:
            shutil.rmtree(target_dir)
        except Exception as e:
            logger.error(f"Failed to delete screenshot folder {target_dir}: {e}")
            
    # Sync background scheduler
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
    total_checks = len(database.get_logs(limit=10000)) # get all-time log counts
    
    # Find if there are any active defacements (defacement flagged in the last check of any site)
    active_defacements = 0
    for target in targets:
        latest = database.get_latest_log(target['id'])
        if latest and latest['is_defaced'] == 1:
            active_defacements += 1
            
    # Compute success rate
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

# --- Settings Endpoints ---

@app.get("/api/settings")
async def get_system_settings():
    return database.get_settings()

@app.post("/api/settings")
async def update_system_settings(settings: SettingsUpdate):
    settings_dict = settings.model_dump()
    database.save_settings(settings_dict)
    
    # Re-sync scheduler in case check interval changed
    scheduler.sync_scheduler_jobs()
    return {"status": "success", "message": "Settings updated successfully."}

# Start script
if __name__ == "__main__":
    import uvicorn
    # Make sure database is ready
    database.init_db()
    uvicorn.run(app, host="127.0.0.1", port=8000)
