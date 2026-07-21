import asyncio
import logging
# pyrefly: ignore [missing-import]
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

async def capture_screenshot(url: str, output_path: str, timeout_ms: int = 30000) -> bool:
    """
    Launches a headless browser, navigates to the given url, and captures a full-page screenshot.
    
    Args:
        url: The website URL to check.
        output_path: Path where the screenshot image should be saved.
        timeout_ms: Maximum time to wait for page load in milliseconds.
        
    Returns:
        True if screenshot was successfully captured, False otherwise.
    """
    logger.info(f"Starting screenshot capture for: {url}")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            # Create a clean browser context with a standard user agent and desktop viewport
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            
            # Go to the url and wait until network is idle (no connections for 500ms)
            logger.info(f"Navigating to {url}...")
            await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            
            # Wait an additional 3 seconds for dynamic content/animations to settle
            await page.wait_for_timeout(3000)
            
            # Capture full page screenshot
            logger.info(f"Saving full-page screenshot to {output_path}...")
            await page.screenshot(path=output_path, full_page=True)
            
            await context.close()
            await browser.close()
            logger.info("Screenshot capture completed successfully.")
            return True
            
    except Exception as e:
        logger.error(f"Error capturing screenshot for {url}: {e}", exc_info=True)
        return False

# Self-test block
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import os
    test_dir = "screenshots"
    os.makedirs(test_dir, exist_ok=True)
    test_path = os.path.join(test_dir, "test_capture.png")
    asyncio.run(capture_screenshot("https://example.com", test_path))
