import asyncio
import logging
import os
import random
from pathlib import Path
from playwright.async_api import async_playwright, Page, BrowserContext, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

# Stealth Browser Configurations & Human Profile Emulation
STEALTH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

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
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    window.chrome = {
        app: { isInstalled: false },
        runtime: {},
        loadTimes: function() {},
        csi: function() {}
    };
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });

    if (window.navigator.permissions) {
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
    }
})();
"""

FREEZE_ANIMATIONS_CSS = """
*, *::before, *::after {
    animation-duration: 0s !important;
    animation-delay: 0s !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0s !important;
    transition-delay: 0s !important;
    scroll-behavior: auto !important;
}
"""

async def handle_popups_and_capture(page: Page, popup_output_path: str = None) -> bool:
    popup_captured = False
    for selector in POPUP_CONTAINER_SELECTORS:
        try:
            locator = page.locator(selector).first
            if await locator.is_visible(timeout=500):
                logger.info(f"Detected popup/modal container with selector '{selector}'.")
                if popup_output_path:
                    os.makedirs(os.path.dirname(os.path.abspath(popup_output_path)), exist_ok=True)
                    await locator.screenshot(path=popup_output_path)
                    logger.info(f"Saved isolated popup screenshot to {popup_output_path}")
                    popup_captured = True
                
                for dismiss_sel in POPUP_DISMISS_SELECTORS:
                    try:
                        btn = locator.locator(dismiss_sel).first
                        if await btn.is_visible(timeout=300):
                            logger.info(f"Dismissing popup using button selector '{dismiss_sel}'...")
                            await btn.click()
                            await page.wait_for_timeout(500)
                            break
                    except Exception:
                        continue
                break
        except Exception:
            continue

    return popup_captured

async def scroll_page_naturally(page: Page):
    try:
        total_height = await page.evaluate("document.body.scrollHeight || document.documentElement.scrollHeight")
        current_scroll = 0

        while current_scroll < total_height:
            scroll_step = random.randint(300, 500)
            current_scroll += scroll_step
            await page.evaluate(f"window.scrollTo(0, {current_scroll})")
            await page.wait_for_timeout(random.randint(150, 300))
            total_height = await page.evaluate("document.body.scrollHeight || document.documentElement.scrollHeight")

        await page.wait_for_timeout(400)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(300)
    except Exception as e:
        logger.warning(f"Error during human scroll simulation: {e}")

async def capture_screenshot(
    url: str,
    output_path: str,
    popup_output_path: str = None,
    timeout_ms: int = 30000,
    browser_engine: str = "firefox"
) -> dict:
    """
    Launches a stealth Playwright browser context, navigates to the URL, stabilizes dynamic content,
    captures/dismisses popups, and saves a full-page screenshot.

    Args:
        url: Target website URL to screenshot.
        output_path: Target path for the full-page screenshot.
        popup_output_path: Optional target path to save isolated popup screenshot if present.
        timeout_ms: Maximum navigation timeout in milliseconds.
        browser_engine: Browser engine to use ('firefox', 'chromium', or 'auto'). Default: 'firefox'.

    Returns:
        dict: Result metadata containing success, popup_captured, error.
    """
    logger.info(f"Starting optimized screenshot capture for: {url} (Engine: {browser_engine})")
    result = {"success": False, "popup_captured": False, "error": None}

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    async with async_playwright() as p:
        browser = None
        engine_order = []
        engine_choice = str(browser_engine).lower().strip()

        if engine_choice == "chromium":
            engine_order = [p.chromium, p.firefox]
        elif engine_choice == "firefox":
            engine_order = [p.firefox, p.chromium]
        else: # 'auto' or default
            engine_order = [p.firefox, p.chromium]

        for browser_type in engine_order:
            try:
                browser = await browser_type.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-infobars",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--ignore-certificate-errors"
                    ] if browser_type == p.chromium else []
                )
                logger.info(f"Launched browser engine: {browser_type.name}")
                break
            except Exception as launch_err:
                logger.warning(f"Engine {browser_type.name} launch skipped: {launch_err}")

        if not browser:
            result["error"] = "Failed to launch any Playwright browser engine."
            logger.error(result["error"])
            return result

        try:
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=STEALTH_USER_AGENT,
                device_scale_factor=1,
                has_touch=False,
                is_mobile=False,
                java_script_enabled=True,
                locale="en-US",
                timezone_id="America/New_York"
            )

            await context.add_init_script(STEALTH_INIT_SCRIPT)
            page = await context.new_page()

            logger.info(f"Navigating to {url}...")
            try:
                await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            except PlaywrightTimeoutError:
                logger.warning(f"Navigation wait_until='networkidle' timed out for {url}. Falling back to 'load'...")
                try:
                    await page.goto(url, wait_until="load", timeout=15000)
                except PlaywrightTimeoutError:
                    logger.warning(f"Navigation wait_until='load' timed out for {url}. Falling back to 'domcontentloaded'...")
                    await page.goto(url, wait_until="domcontentloaded", timeout=10000)

            popup_captured = await handle_popups_and_capture(page, popup_output_path)
            result["popup_captured"] = popup_captured

            try:
                await page.evaluate("document.fonts.ready")
            except Exception as fe:
                logger.debug(f"Fonts ready check skipped/failed: {fe}")

            try:
                await page.add_style_tag(content=FREEZE_ANIMATIONS_CSS)
            except Exception as se:
                logger.debug(f"Style tag injection skipped: {se}")

            await scroll_page_naturally(page)
            await page.wait_for_timeout(1000)

            logger.info(f"Capturing full-page screenshot to {output_path}...")
            await page.screenshot(path=output_path, full_page=True)

            await context.close()
            await browser.close()

            result["success"] = True
            logger.info(f"Screenshot successfully captured for {url}")

        except Exception as e:
            logger.error(f"Error capturing screenshot for {url}: {e}", exc_info=True)
            result["error"] = str(e)
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass

    return result

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_url = "https://example.com"
    test_out = "static/screenshots/test_current.png"
    res = asyncio.run(capture_screenshot(test_url, test_out))
    print(f"Test result: {res}")
