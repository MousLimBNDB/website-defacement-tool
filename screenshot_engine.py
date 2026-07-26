import asyncio
import logging
# pyrefly: ignore [missing-import]
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

async def capture_screenshot(
    url: str, 
    output_path: str, 
    timeout_ms: int = 30000, 
    ignored_selectors: str = "", 
    target_selectors: str = ""
) -> bool:
    """
    Launches a headless browser, navigates to the given url, masks/hides ignored dynamic elements,
    and captures a full-page or section-focused screenshot.
    
    Args:
        url: The website URL to check.
        output_path: Path where the screenshot image should be saved.
        timeout_ms: Maximum time to wait for page load in milliseconds.
        ignored_selectors: Comma-separated CSS selectors of dynamic elements to mask/hide (e.g. '.clock, #timer').
        target_selectors: Specific CSS selector to fragment/crop target section (e.g. '#main-content').
        
    Returns:
        True if screenshot was successfully captured, False otherwise.
    """
    logger.info(f"Starting screenshot capture for: {url} (Ignored: '{ignored_selectors}', Target: '{target_selectors}')")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            # Create a clean browser context with a standard user agent and desktop viewport
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            
            # Go to the url and wait until domcontentloaded
            logger.info(f"Navigating to {url}...")
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            
            # Wait an additional 1.5 seconds for dynamic content/animations to settle
            await page.wait_for_timeout(1500)
            
            # 1. Apply Dynamic Element Hiding / Masking for Ignored Selectors
            if ignored_selectors and ignored_selectors.strip():
                selectors_list = [s.strip() for s in ignored_selectors.split(',') if s.strip()]
                if selectors_list:
                    logger.info(f"Hiding dynamic elements for selectors: {selectors_list}")
                    await page.evaluate("""(selectors) => {
                        selectors.forEach(sel => {
                            try {
                                const elements = document.querySelectorAll(sel);
                                elements.forEach(el => {
                                    // Mask dynamic element by hiding visibility or rendering a neutral static placeholder
                                    el.style.setProperty('visibility', 'hidden', 'important');
                                    el.setAttribute('data-defacement-ignored', 'true');
                                });
                            } catch (err) {
                                console.error('Invalid selector:', sel, err);
                            }
                        });
                    }""", selectors_list)

            # 2. Capture screenshot (Target locator section or Full Page)
            captured_section = False
            if target_selectors and target_selectors.strip():
                target_sel = target_selectors.strip()
                try:
                    locator = page.locator(target_sel).first
                    if await locator.count() > 0:
                        logger.info(f"Saving fragment section screenshot ({target_sel}) to {output_path}...")
                        await locator.screenshot(path=output_path)
                        captured_section = True
                except Exception as ex:
                    logger.warning(f"Could not crop fragment for selector '{target_sel}': {ex}. Falling back to full page.")

            if not captured_section:
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
