import os
import logging
from PIL import Image, ImageChops, ImageEnhance

logger = logging.getLogger(__name__)

def compare_screenshots(
    baseline_path: str,
    current_path: str,
    diff_path: str = None,
    threshold: int = 15
) -> float:
    """
    Compares baseline and current screenshots using Canvas Expansion (Letterboxing / Padding).
    Instead of squashing or resizing images with .resize(), both images are pasted onto a canvas
    sized to max(width1, width2) and max(height1, height2) at position (0, 0).

    Args:
        baseline_path: Path to baseline clean screenshot.
        current_path: Path to current captured screenshot.
        diff_path: Optional path to save visual diff highlight image.
        threshold: Pixel intensity difference threshold (0-255) for flagging changes.

    Returns:
        float: Similarity score between 0.0 (completely different) and 1.0 (identical).
    """
    logger.info(f"Comparing baseline '{baseline_path}' and current '{current_path}' using Canvas Expansion.")

    if not os.path.exists(baseline_path) or not os.path.exists(current_path):
        logger.warning("One or both screenshot files do not exist for comparison.")
        return 0.0

    try:
        img_baseline = Image.open(baseline_path).convert('RGB')
        img_current = Image.open(current_path).convert('RGB')

        # 1. Calculate maximum canvas dimensions
        max_width = max(img_baseline.width, img_current.width)
        max_height = max(img_baseline.height, img_current.height)

        # 2. Create uniform white canvas for both images (0, 0 alignment)
        canvas_baseline = Image.new('RGB', (max_width, max_height), (255, 255, 255))
        canvas_current = Image.new('RGB', (max_width, max_height), (255, 255, 255))

        canvas_baseline.paste(img_baseline, (0, 0))
        canvas_current.paste(img_current, (0, 0))

        # 3. Calculate absolute difference
        diff = ImageChops.difference(canvas_baseline, canvas_current)
        diff_gray = diff.convert('L')

        # 4. Count changed pixels above intensity threshold
        pixels = diff_gray.tobytes()
        changed_pixels = sum(1 for p in pixels if p > threshold)
        total_pixels = len(pixels)

        diff_ratio = changed_pixels / total_pixels if total_pixels > 0 else 0.0
        similarity_score = max(0.0, 1.0 - diff_ratio)

        logger.info(
            f"Canvas Expansion Comparison complete: Similarity = {similarity_score:.4f} "
            f"({changed_pixels}/{total_pixels} pixels changed, Canvas Size: {max_width}x{max_height})"
        )

        # 5. Create visual diff highlight image if requested
        if diff_path:
            # Mask pixels where difference exceeds threshold
            mask = diff_gray.point(lambda x: 255 if x > threshold else 0)

            # Red overlay for changed regions
            red_overlay = Image.new('RGB', (max_width, max_height), (255, 0, 0))

            # Dim current canvas slightly so red highlights pop
            dimmer = ImageEnhance.Brightness(canvas_current)
            dimmed_current = dimmer.enhance(0.75)

            # Composite red overlay onto dimmed current image
            diff_visual = Image.composite(red_overlay, dimmed_current, mask)

            os.makedirs(os.path.dirname(os.path.abspath(diff_path)), exist_ok=True)
            diff_visual.save(diff_path)
            logger.info(f"Saved visual diff highlight image to '{diff_path}'.")

        return similarity_score

    except Exception as e:
        logger.error(f"Error comparing screenshots with canvas expansion: {e}", exc_info=True)
        return 0.0

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    os.makedirs("static/screenshots", exist_ok=True)
    img1 = Image.new("RGB", (300, 300), (255, 255, 255))
    img2 = Image.new("RGB", (300, 450), (255, 255, 255))

    from PIL import ImageDraw
    draw = ImageDraw.Draw(img2)
    draw.rectangle([50, 50, 150, 150], fill=(0, 0, 0))

    img1.save("static/screenshots/test_base.png")
    img2.save("static/screenshots/test_current.png")

    score = compare_screenshots(
        "static/screenshots/test_base.png",
        "static/screenshots/test_current.png",
        "static/screenshots/test_diff.png"
    )
    print(f"Canvas Expansion test similarity score: {score}")
