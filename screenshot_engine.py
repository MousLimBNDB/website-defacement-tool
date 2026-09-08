import os
import sys
import json
import asyncio
import logging
import argparse
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page, BrowserContext

import config
import database

logger = logging.getLogger(__name__)

# Realistic Desktop User Agent
STEALTH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Common Consent & Popup selectors (inspired by autoconsent & Consent-O-Matic)
POPUP_CONTAINER_SELECTORS = [
    "#onetrust-banner-sdk",
    "#onetrust-consent-sdk",
    "#CybotCookiebotDialog",
    "#didomi-host",
    "#didomi-notice",
    "#trustarc-banner-container",
    ".fc-consent-root",
    ".fc-dialog-container",
    ".qc-cmp2-container",
    "div[id*='cookie-banner' i]",
    "div[id*='cookie-consent' i]",
    "div[class*='cookie-consent' i]",
    "div[class*='cookie-banner' i]",
    "div[class*='consent-banner' i]",
    "[aria-modal='true']",
    ".modal.show",
    "div[role='dialog']"
]

POPUP_DISMISS_SELECTORS = [
    "#onetrust-accept-btn-handler",
    "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
    "#didomi-notice-agree-button",
    ".fc-cta-consent",
    "button[mode='primary']",
    "button:has-text('Accept all')",
    "button:has-text('Accept All')",
    "button:has-text('Accept')",
    "button:has-text('Agree')",
    "button:has-text('Allow all')",
    "button:has-text('Allow All')",
    "button:has-text('I agree')",
    "button:has-text('I Agree')",
    "button:has-text('Accepter')",
    "button:has-text('J\\'accepte')",
    "button:has-text('Tout accepter')",
    "button:has-text('Got it')",
    "button:has-text('OK')",
    "button[aria-label='Close']",
    "button[aria-label='Fermer']",
    ".modal-close",
    ".close-button"
]

STEALTH_INIT_SCRIPT = """
(() => {
    // 1. Mask navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });

    // 2. Mock Chrome runtime object
    window.chrome = {
        app: { isInstalled: false, InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' }, RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' } },
        runtime: { OnInstalledReason: { CHROME_UPDATE: 'chrome_update', INSTALL: 'install', SHARED_MODULE_UPDATE: 'shared_module_update', UPDATE: 'update' } },
        loadTimes: function() {},
        csi: function() {}
    };

    // 3. Emulate realistic languages and plugins
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en', 'fr']
    });

    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
    });

    // 4. Emulate notification permission
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
})();
"""

FREEZE_ANIMATIONS_CSS = """
*, *::before, *::after {
    animation: none !important;
    -webkit-animation: none !important;
    transition: none !important;
    -webkit-transition: none !important;
    scroll-behavior: auto !important;
}
"""

async def apply_stealth_and_stabilization(page: Page):
    """
    Injects anti-bot stealth scripts, freezes CSS transitions and animations,
    and awaits font loading to prevent layout shifts.
    """
    # Freeze CSS animations and transitions
    try:
        await page.add_style_tag(content=FREEZE_ANIMATIONS_CSS)
    except Exception as e:
        logger.debug(f"Could not inject animation freeze CSS: {e}")

    # Await web fonts loading
    try:
        await page.evaluate("() => document.fonts ? document.fonts.ready : Promise.resolve()")
    except Exception as e:
        logger.debug(f"Font wait error: {e}")

async def handle_infinite_scroll_and_lazy_load(page: Page, max_scroll_steps: int = 4):
    """
    Performs human-like smooth scrolling to trigger viewport-based lazy-loaded images,
    banners, and dynamic hydration scripts, then scrolls back to top.
    """
    try:
        viewport_height = await page.evaluate("() => window.innerHeight || 800")
        total_height = await page.evaluate("() => document.body.scrollHeight || 1000")
        
        # Incremental scroll down
        steps = min(max_scroll_steps, max(1, total_height // viewport_height))
        for step in range(1, steps + 1):
            scroll_y = step * 600
            await page.evaluate(f"window.scrollTo({{ top: {scroll_y}, behavior: 'smooth' }})")
            # Human pause
            await page.wait_for_timeout(350)
            
        # Simulated mouse movement across page
        await page.mouse.move(300, 400)
        await page.wait_for_timeout(200)
        await page.mouse.move(600, 300)

        # Scroll back to the top for the main capture
        await page.evaluate("window.scrollTo({ top: 0, behavior: 'instant' })")
        await page.wait_for_timeout(400)
    except Exception as e:
        logger.debug(f"Lazy-load scroll encountered minor error: {e}")

async def detect_and_isolate_popups(page: Page, target_id: int, timestamp: str, screenshots_dir: Path) -> str:
    """
    Detects overlay dialogs / cookie banners / consent modals.
    If detected:
      1. Captures the popup element separately into screenshots/{target_id}/popup_{timestamp}.png
      2. Records popup metadata in database for isolated defacement monitoring.
      3. Dismisses / accepts the popup to unblock the main webpage.
    Returns:
      Path to captured popup screenshot, or empty string if no popup found.
    """
    popup_screenshot_path = ""
    target_folder = screenshots_dir / str(target_id)
    target_folder.mkdir(parents=True, exist_ok=True)

    for selector in POPUP_CONTAINER_SELECTORS:
        try:
            locator = page.locator(selector).first
            if await locator.count() > 0 and await locator.is_visible():
                box = await locator.bounding_box()
                if box and box["width"] > 100 and box["height"] > 50:
                    logger.info(f"[Target {target_id}] Popup/Consent dialog detected matching '{selector}'")
                    popup_file = target_folder / f"popup_{timestamp}.png"
                    try:
                        await locator.screenshot(path=str(popup_file))
                        popup_screenshot_path = str(popup_file)
                        logger.info(f"[Target {target_id}] Saved isolated popup screenshot to {popup_file}")
                        # Record in popup tracking table
                        database.add_popup_log(
                            target_id=target_id,
                            url=page.url,
                            popup_screenshot_path=popup_screenshot_path,
                            is_defaced=False,
                            analysis_summary=f"Detected popup matching '{selector}'"
                        )
                    except Exception as snap_err:
                        logger.warning(f"Could not screenshot popup locator: {snap_err}")
                    break
        except Exception:
            continue

    # Attempt to dismiss or accept the popup to reveal clean page
    for dismiss_sel in POPUP_DISMISS_SELECTORS:
        try:
            btn = page.locator(dismiss_sel).first
            if await btn.count() > 0 and await btn.is_visible():
                logger.info(f"[Target {target_id}] Dismissing popup via selector: '{dismiss_sel}'")
                await btn.click(timeout=1500)
                await page.wait_for_timeout(400)
                break
        except Exception:
            continue

    return popup_screenshot_path

async def capture_website(
    url: str,
    target_id: int,
    output_path: str = None,
    ignored_selectors: str = "",
    target_selectors: str = "",
    timeout_ms: int = 35000
) -> dict:
    """
    Captures a high-fidelity screenshot of the target website with anti-bot evasion,
    stealth fingerprinting, hydration settling, popup detection, and isolated popup snapshot.
    
    Returns:
        dict: {
            "success": bool,
            "target_id": int,
            "url": str,
            "current_path": str,
            "baseline_path": str,
            "is_baseline_created": bool,
            "popup_path": str,
            "error": str
        }
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshots_dir = Path(config.SCREENSHOTS_DIR)
    target_folder = screenshots_dir / str(target_id)
    target_folder.mkdir(parents=True, exist_ok=True)

    baseline_file = target_folder / "baseline.png"
    if not output_path:
        current_file = target_folder / f"current_{timestamp}.png"
    else:
        current_file = Path(output_path)
        current_file.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "success": False,
        "target_id": target_id,
        "url": url,
        "timestamp": timestamp,
        "current_path": str(current_file),
        "baseline_path": str(baseline_file),
        "is_baseline_created": False,
        "popup_path": "",
        "error": ""
    }

    logger.info(f"[Target {target_id}] Starting capture for {url}")

    try:
        async with async_playwright() as p:
            # Stealth Chrome Launch Flags
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-infobars",
                    "--window-size=1920,1080"
                ]
            )

            # Realistic browser context
            context: BrowserContext = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=STEALTH_USER_AGENT,
                locale="en-US",
                timezone_id="America/New_York",
                device_scale_factor=1,
                has_touch=False,
                is_mobile=False,
                java_script_enabled=True
            )

            # Inject stealth initialization script before any page scripts run
            await context.add_init_script(STEALTH_INIT_SCRIPT)

            page: Page = await context.new_page()

            # Set custom navigation timeout
            page.set_default_navigation_timeout(timeout_ms)

            # Step 1: Navigate with networkidle fallback
            try:
                logger.info(f"[Target {target_id}] Navigating to {url} (wait_until=networkidle)...")
                await page.goto(url, wait_until="networkidle", timeout=min(timeout_ms, 15000))
            except Exception as net_err:
                logger.warning(f"[Target {target_id}] networkidle timed out ({net_err}). Falling back to 'load' / DOM settle...")
                try:
                    await page.goto(url, wait_until="load", timeout=timeout_ms)
                except Exception:
                    # If already navigated, continue
                    pass

            # Step 2: Human reading pause & JS hydration delay (React/Vue/Next.js skeleton)
            await page.wait_for_timeout(800)

            # Step 3: Anti-bot interaction simulation & Lazy-load image trigger
            await handle_infinite_scroll_and_lazy_load(page)

            # Step 4: Detect, snapshot, and dismiss popups/cookie consent banners
            popup_path = await detect_and_isolate_popups(page, target_id, timestamp, screenshots_dir)
            result["popup_path"] = popup_path

            # Step 5: Stabilize rendering (Freeze animations & await web fonts)
            await apply_stealth_and_stabilization(page)

            # Step 6: Mask dynamically ignored selectors if specified
            if ignored_selectors and ignored_selectors.strip():
                selectors_list = [s.strip() for s in ignored_selectors.split(",") if s.strip()]
                if selectors_list:
                    await page.evaluate("""(selectors) => {
                        selectors.forEach(sel => {
                            try {
                                const elements = document.querySelectorAll(sel);
                                elements.forEach(el => {
                                    el.style.setProperty('visibility', 'hidden', 'important');
                                });
                            } catch (e) {}
                        });
                    }""", selectors_list)

            # Step 7: Capture Screenshot (Target selector fragment or full page)
            if target_selectors and target_selectors.strip():
                locator = page.locator(target_selectors.strip()).first
                if await locator.count() > 0:
                    logger.info(f"[Target {target_id}] Capturing targeted selector: {target_selectors}")
                    await locator.screenshot(path=str(current_file))
                else:
                    logger.info(f"[Target {target_id}] Target selector not found, capturing full page.")
                    await page.screenshot(path=str(current_file), full_page=True)
            else:
                logger.info(f"[Target {target_id}] Capturing full-page snapshot to {current_file}")
                await page.screenshot(path=str(current_file), full_page=True)

            # Check if baseline exists; if not, initialize current as baseline
            if not baseline_file.exists():
                import shutil
                shutil.copy(str(current_file), str(baseline_file))
                result["is_baseline_created"] = True
                logger.info(f"[Target {target_id}] Baseline image created: {baseline_file}")

            await context.close()
            await browser.close()
            result["success"] = True

    except Exception as e:
        logger.error(f"[Target {target_id}] Screenshot capture failed: {e}", exc_info=True)
        result["error"] = str(e)

    return result

def main():
    parser = argparse.ArgumentParser(description="Node 3: Playwright Screenshot Engine for n8n")
    parser.add_argument("--url", required=True, help="Target website URL")
    parser.add_argument("--target-id", type=int, default=1, help="Target ID")
    parser.add_argument("--output", default=None, help="Output current screenshot file path")
    parser.add_argument("--ignored-selectors", default="", help="Comma-separated CSS selectors to mask")
    parser.add_argument("--target-selectors", default="", help="Specific CSS selector to crop")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    res = asyncio.run(capture_website(
        url=args.url,
        target_id=args.target_id,
        output_path=args.output,
        ignored_selectors=args.ignored_selectors,
        target_selectors=args.target_selectors
    ))
    # Emit JSON result for n8n pipeline
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
