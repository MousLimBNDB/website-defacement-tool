import os
import sys
import shutil
import time
import asyncio
import http.server
import socketserver
import threading
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageEnhance

import database
import image_comparator
from screenshot_engine import capture_screenshot

PORT = 8899
MOCK_DIR = "mock_demo_site"

class MockHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

def start_mock_server():
    os.makedirs(MOCK_DIR, exist_ok=True)
    
    # 1. Clean Corporate Portal
    clean_html = """<!DOCTYPE html>
<html>
<head>
    <title>Corporate Portal - Security System</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 40px; }
        .card { background: #1e293b; border-radius: 12px; padding: 30px; border: 1px solid #334155; max-width: 800px; margin: 0 auto; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
        h1 { color: #38bdf8; font-size: 28px; margin-bottom: 10px; }
        .subtitle { color: #94a3b8; font-size: 16px; margin-bottom: 25px; }
        .clock-box { background: #0f172a; border: 1px solid #38bdf8; color: #38bdf8; padding: 10px 20px; border-radius: 8px; display: inline-block; font-weight: bold; margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }
        .box { background: #334155; padding: 20px; border-radius: 8px; }
        .box h3 { color: #f1f5f9; margin-top: 0; }
        .badge { background: #22c55e; color: #022c22; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🛡️ Corporate Operations Hub</h1>
        <div class="subtitle">Official Internal Enterprise Management Portal</div>
        <div class="clock-box clock">🕒 System Live Time: 10:45:12 AM</div>
        <div class="grid">
            <div class="box">
                <h3>System Status</h3>
                <p>All core infrastructure services operating within normal parameters.</p>
                <span class="badge">OPERATIONAL</span>
            </div>
            <div class="box">
                <h3>Active Deployment</h3>
                <p>Version 4.2.1 production build active across primary regions.</p>
                <span class="badge">VERIFIED</span>
            </div>
        </div>
    </div>
</body>
</html>"""
    with open(f"{MOCK_DIR}/intranet.html", "w", encoding="utf-8") as f:
        f.write(clean_html)
        
    # 2. Defaced Corporate Portal
    defaced_html = """<!DOCTYPE html>
<html>
<head>
    <title>HACKED BY ANONYMOUS SQUAD</title>
    <style>
        body { font-family: 'Courier New', monospace; background-color: #000; color: #0f0; margin: 0; padding: 40px; text-align: center; }
        .card { background: #050505; border: 3px solid #ff0000; border-radius: 8px; padding: 40px; max-width: 800px; margin: 0 auto; box-shadow: 0 0 40px #ff0000; }
        h1 { color: #ff0000; font-size: 42px; margin-bottom: 10px; text-shadow: 0 0 10px #ff0000; }
        .hacker-msg { color: #ffffff; font-size: 20px; margin: 20px 0; border: 1px dashed #ff0000; padding: 15px; }
        .skull { font-size: 70px; margin: 20px; }
        .footer-hack { color: #888; font-size: 14px; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="card">
        <div class="skull">☠️</div>
        <h1>!!! SYSTEM DEFACED BY X-CYBER !!!</h1>
        <div class="hacker-msg">
            YOUR SECURITY IS A JOKE. ALL INTERNAL DATABASES HAVE BEEN ENCRYPTED AND EXFILTRATED.
        </div>
        <p style="color: #ff5555; font-size: 18px;">PAY 10 BTC TO RESTORE ACCESS OR SENSITIVE DATA WILL BE LEAKED TO PUBLIC DOMAIN.</p>
        <div class="footer-hack">Greetz: 0day-sec | root-access | cyber-ghosts</div>
    </div>
</body>
</html>"""
    with open(f"{MOCK_DIR}/intranet_defaced.html", "w", encoding="utf-8") as f:
        f.write(defaced_html)

    # 3. Copy eliteMotors.html from mockSite if available
    if os.path.exists("mockSite/eliteMotors.html"):
        shutil.copy("mockSite/eliteMotors.html", f"{MOCK_DIR}/eliteMotors.html")

    def bind_handler(*args, **kwargs):
        return MockHTTPHandler(*args, directory=MOCK_DIR, **kwargs)
        
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), bind_handler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    return httpd

async def generate_demo_dataset():
    print("Initializing demo environment...")
    database.init_db()
    
    httpd = start_mock_server()
    print(f"Mock server running on http://127.0.0.1:{PORT}")

    # Register Target 1: Corporate Intranet
    t1_id = database.add_target(
        url=f"http://127.0.0.1:{PORT}/intranet.html",
        name="Corporate Intranet Operations",
        ignored_selectors=".clock",
        target_selectors=""
    )
    
    # Register Target 2: E-Commerce Store
    t2_id = database.add_target(
        url=f"http://127.0.0.1:{PORT}/eliteMotors.html",
        name="Elite Motors Showcase",
        ignored_selectors=".timestamp, #visitorCount",
        target_selectors=""
    )

    # Register Target 3: Public Banking Portal
    t3_id = database.add_target(
        url="https://example.com",
        name="Public Gateway Portal",
        ignored_selectors="",
        target_selectors=""
    )

    dir_t1 = f"static/screenshots/{t1_id}"
    dir_t2 = f"static/screenshots/{t2_id}"
    dir_t3 = f"static/screenshots/{t3_id}"
    
    os.makedirs(dir_t1, exist_ok=True)
    os.makedirs(dir_t2, exist_ok=True)
    os.makedirs(dir_t3, exist_ok=True)

    # Capture Baseline 1
    url1 = f"http://127.0.0.1:{PORT}/intranet.html"
    base1_path = f"{dir_t1}/baseline.png"
    await capture_screenshot(url1, base1_path, ignored_selectors=".clock")
    
    database.add_log(
        target_id=t1_id,
        similarity_score=1.0,
        is_defaced=0,
        confidence=0,
        change_type="Baseline Created",
        analysis_summary="Clean baseline visual snapshot captured and stored.",
        screenshot_path=f"/{base1_path}",
        diff_path="",
        status="SUCCESS"
    )

    # Capture Current 1 (Defaced version)
    url1_defaced = f"http://127.0.0.1:{PORT}/intranet_defaced.html"
    curr1_path = f"{dir_t1}/current_defaced.png"
    diff1_path = f"{dir_t1}/diff_defaced.png"
    await capture_screenshot(url1_defaced, curr1_path)

    sim1 = image_comparator.compare_screenshots(base1_path, curr1_path, diff1_path)

    database.add_log(
        target_id=t1_id,
        similarity_score=sim1,
        is_defaced=1,
        confidence=98,
        change_type="Website Defacement",
        analysis_summary=f"CRITICAL: Visual similarity score dropped to {sim1:.2f}. System header replaced with 'SYSTEM DEFACEMENT BY X-CYBER' skull graphic and ransom demands. Multimodal Vision AI confirms unauthorized malicious visual modification.",
        screenshot_path=f"/{curr1_path}",
        diff_path=f"/{diff1_path}",
        status="SUCCESS"
    )

    # Baseline & Log for Target 2
    url2 = f"http://127.0.0.1:{PORT}/eliteMotors.html"
    base2_path = f"{dir_t2}/baseline.png"
    curr2_path = f"{dir_t2}/current_normal.png"
    diff2_path = f"{dir_t2}/diff_normal.png"
    await capture_screenshot(url2, base2_path)
    await capture_screenshot(url2, curr2_path)
    sim2 = image_comparator.compare_screenshots(base2_path, curr2_path, diff2_path)

    database.add_log(
        target_id=t2_id,
        similarity_score=1.0,
        is_defaced=0,
        confidence=0,
        change_type="Baseline Created",
        analysis_summary="Initial high-resolution baseline screenshot established.",
        screenshot_path=f"/{base2_path}",
        diff_path="",
        status="SUCCESS"
    )

    database.add_log(
        target_id=t2_id,
        similarity_score=sim2,
        is_defaced=0,
        confidence=0,
        change_type="No Change",
        analysis_summary="Periodic monitoring check passed. Site structure intact.",
        screenshot_path=f"/{curr2_path}",
        diff_path="",
        status="SUCCESS"
    )

    print("Demo dataset established successfully!")

if __name__ == "__main__":
    asyncio.run(generate_demo_dataset())
