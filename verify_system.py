import os
import time
import asyncio
import http.server
import socketserver
import threading
import shutil
import database
import scheduler

PORT = 8899
MOCK_SITE_DIR = "mock_website"
HTML_PATH = f"{MOCK_SITE_DIR}/index.html"

# Simple HTTP Handler to serve our mock site
class MockHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Suppress server logging to stdout

def start_mock_server():
    os.makedirs(MOCK_SITE_DIR, exist_ok=True)
    
    # Write initial clean page content
    write_webpage_content(
        title="Mous Lim's Secure Corporate Portal",
        headline="Welcome to the Corporate Intranet",
        body="This portal holds secure resources for team members. All systems are operating normally. Operational update: Q3 goals are fully on track."
    )
    
    def bind_handler(*args, **kwargs):
        return MockHTTPHandler(*args, directory=MOCK_SITE_DIR, **kwargs)
        
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), bind_handler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    return httpd

def write_webpage_content(title, headline, body, clock_time="10:00:00 AM", is_hacked=False):
    style = """
    body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #f0f2f5; color: #333; margin: 0; padding: 0; display: flex; align-items: center; justify-content: center; height: 100vh; }
    .card { background: white; padding: 3rem; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); text-align: center; max-width: 500px; }
    h1 { color: #1e3a8a; margin-bottom: 1rem; }
    p { line-height: 1.6; color: #4b5563; }
    .clock { font-size: 1.1rem; font-weight: bold; background: #e0e7ff; color: #3730a3; padding: 0.5rem 1rem; border-radius: 8px; margin: 1rem 0; display: inline-block; }
    .footer { margin-top: 2rem; font-size: 0.8rem; color: #9ca3af; }
    """
    if is_hacked:
        style = """
        body { font-family: 'Courier New', monospace; background-color: #000; color: #0f0; margin: 0; padding: 0; display: flex; align-items: center; justify-content: center; height: 100vh; }
        .card { border: 3px solid #f00; background: #111; padding: 3rem; border-radius: 4px; box-shadow: 0 0 30px #f00; text-align: center; max-width: 600px; }
        h1 { color: #ff0000; font-size: 3rem; margin-bottom: 1rem; text-shadow: 0 0 10px #f00; animation: blink 1s infinite; }
        p { line-height: 1.6; color: #ff3333; font-size: 1.2rem; }
        .clock { display: none; }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
        """

    html = f"""<!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <style>{style}</style>
    </head>
    <body>
        <div class="card">
            <h1>{headline}</h1>
            <div class="clock">🕒 Live Clock: {clock_time}</div>
            <p>{body}</p>
            <div class="footer">Secure Portal V2.5.1</div>
        </div>
    </body>
    </html>
    """
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)

async def test_pipeline():
    print("=== STARTING DEFACEMENT Sentinel INTEGRATION TEST ===")
    
    # 1. Initialize SQLite Database
    database.init_db()
    
    # 2. Start mock webserver
    print(f"Starting mock HTTP server on http://localhost:{PORT}...")
    server = start_mock_server()
    
    target_id = None
    try:
        # 3. Register target website with dynamic ignored selector rule
        url = f"http://127.0.0.1:{PORT}/index.html"
        name = "Local Corporate Intranet with Dynamic Clock"
        ignored_selectors = ".clock"
        target_id = database.add_target(url, name, ignored_selectors=ignored_selectors)
        print(f"Target registered in DB: ID = {target_id}, URL = {url}, Ignored = '{ignored_selectors}'")
        
        # 4. First run: Establish Baseline screenshot
        print("\n--- RUN 1: Capturing clean baseline image with clock set to 10:00:00 AM ---")
        write_webpage_content(
            title="Mous Lim's Secure Corporate Portal",
            headline="Welcome to the Corporate Intranet",
            body="This portal holds secure resources for team members. All systems are operating normally.",
            clock_time="10:00:00 AM"
        )
        
        baseline_path = f"static/screenshots/{target_id}/baseline.png"
        if os.path.exists(baseline_path):
            os.remove(baseline_path)
            
        await scheduler.run_check_for_target(target_id)
        latest_log = database.get_latest_log(target_id)
        print(f"Log result: Status={latest_log['status']}, Similarity={latest_log['similarity_score']}, Category={latest_log['change_type']}")
        
        if os.path.exists(baseline_path):
            print("[OK] Baseline image created successfully.")
        else:
            print("[ERROR] Error: Baseline image was not created.")
            return
            
        # 5. Run 2: Dynamic clock changes to 10:15:42 PM (Simulated false positive test)
        print("\n--- RUN 2: Simulating dynamic clock change to 10:15:42 PM (Ignored selector active) ---")
        write_webpage_content(
            title="Mous Lim's Secure Corporate Portal",
            headline="Welcome to the Corporate Intranet",
            body="This portal holds secure resources for team members. All systems are operating normally.",
            clock_time="10:15:42 PM"
        )
        
        await scheduler.run_check_for_target(target_id)
        logs = database.get_logs(target_id, limit=1)
        latest_log = logs[0]
        print(f"Log result: Status={latest_log['status']}, Similarity={latest_log['similarity_score']:.4f}, Category='{latest_log['change_type']}'")
        print(f"Summary: {latest_log['analysis_summary']}")
        
        if latest_log['similarity_score'] >= 0.99:
            print("[SUCCESS] Dynamic clock change ignored successfully! False positive avoided.")
        else:
            print(f"[WARNING] Similarity score ({latest_log['similarity_score']}) was lower than expected.")

        # 6. Run 3: Simulate genuine website defacement
        print("\n--- RUN 3: Simulating Actual Website Defacement ---")
        write_webpage_content(
            title="HACKED BY ANONYMOUS",
            headline="!!! HACKED BY ANONYMOUS !!!",
            body="YOUR SYSTEM HAS BEEN PENETRATED. WE ARE IN CONTROL. ALL DATA HAS BEEN EXFILTRATED. PAY 5 BTC TO WE-OWN-YOU OR YOUR SECRETS GO PUBLIC.",
            is_hacked=True
        )
        print("Mock website defaced. Running check...")
        
        await scheduler.run_check_for_target(target_id)
        logs = database.get_logs(target_id, limit=1)
        latest_log = logs[0]
        
        print("\n--- TEST CONCLUSION ---")
        print(f"Audit log details:")
        print(f"  - Target Site: {latest_log['target_name']}")
        print(f"  - Similarity Score: {latest_log['similarity_score']:.4f}")
        print(f"  - Flagged Defaced: {latest_log['is_defaced'] == 1}")
        print(f"  - Confidence: {latest_log['confidence']}%")
        print(f"  - Classification: {latest_log['change_type']}")
        print(f"  - Diagnostic Summary: {latest_log['analysis_summary']}")
        
        if latest_log['is_defaced'] == 1 or latest_log['similarity_score'] < 0.9:
            print("\n[SUCCESS] Genuine website defacement successfully caught!")
        else:
            print("\n[FAILED] Defacement was not detected.")

    finally:
        print("\nCleaning up server and temporary files...")
        if target_id:
            database.delete_target(target_id)
        server.shutdown()
        server.server_close()
        if os.path.exists(MOCK_SITE_DIR):
            shutil.rmtree(MOCK_SITE_DIR)
        print("Cleanup done.")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
