import os
import logging
from PIL import Image, ImageChops, ImageEnhance

logger = logging.getLogger(__name__)

def compare_screenshots(baseline_path: str, current_path: str, diff_path: str = None, threshold: int = 15) -> float:
    """
    Compares two screenshot images, computes a similarity score, and creates a visual diff image.
    
    Args:
        baseline_path: Path to the clean, baseline screenshot.
        current_path: Path to the new, current screenshot.
        diff_path: Path where the visual diff highlight image should be saved.
        threshold: The pixel value difference threshold (0-255) to consider a pixel "changed".
        
    Returns:
        similarity_score: Float between 0.0 (completely different) and 1.0 (identical).
    """
    logger.info(f"Comparing baseline {baseline_path} and current {current_path}")
    
    if not os.path.exists(baseline_path) or not os.path.exists(current_path):
        logger.warning("One of the image paths for comparison does not exist.")
        return 0.0
        
    try:
        # Open images and convert to RGB
        img_baseline = Image.open(baseline_path).convert('RGB')
        img_current = Image.open(current_path).convert('RGB')
        
        # Resize current to match baseline if dimensions changed
        if img_baseline.size != img_current.size:
            logger.info(f"Resizing current screenshot from {img_current.size} to baseline size {img_baseline.size}")
            img_current = img_current.resize(img_baseline.size, Image.Resampling.LANCZOS)
            
        # Compute absolute difference
        diff = ImageChops.difference(img_baseline, img_current)
        
        # Convert difference to grayscale to evaluate pixel intensity changes
        diff_gray = diff.convert('L')
        
        # Count changed pixels above threshold
        pixels = list(diff_gray.getdata())
        changed_pixels = sum(1 for p in pixels if p > threshold)
        total_pixels = len(pixels)
        
        diff_ratio = changed_pixels / total_pixels
        similarity_score = 1.0 - diff_ratio
        
        logger.info(f"Similarity: {similarity_score:.4f} (Changed pixels: {changed_pixels}/{total_pixels})")
        
        # Generate visual diff highlights if output path is requested
        if diff_path:
            # Create binary mask where difference exceeds threshold
            mask = diff_gray.point(lambda x: 255 if x > threshold else 0)
            
            # Create solid red image for overlay highlights
            red_overlay = Image.new('RGB', img_baseline.size, (255, 0, 0))
            
            # Dim the current screenshot slightly to make the red highlights pop
            dimmer = ImageEnhance.Brightness(img_current)
            dimmed_current = dimmer.enhance(0.75)
            
            # Composite the red overlay onto the dimmed screenshot using the difference mask
            diff_visual = Image.composite(red_overlay, dimmed_current, mask)
            
            # Save visual diff
            os.makedirs(os.path.dirname(os.path.abspath(diff_path)), exist_ok=True)
            diff_visual.save(diff_path)
            logger.info(f"Saved visual diff highlight to {diff_path}")
            
        return similarity_score
        
    except Exception as e:
        logger.error(f"Error comparing screenshots: {e}", exc_info=True)
        return 0.0

# Self-test block
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Create mock images for testing
    os.makedirs("screenshots", exist_ok=True)
    img1 = Image.new("RGB", (300, 300), (255, 255, 255))
    img2 = Image.new("RGB", (300, 300), (255, 255, 255))
    
    # draw a red box in the second image
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img2)
    draw.rectangle([50, 50, 150, 150], fill=(0, 0, 0))
    
    img1.save("screenshots/test_base.png")
    img2.save("screenshots/test_current.png")
    
    score = compare_screenshots("screenshots/test_base.png", "screenshots/test_current.png", "screenshots/test_diff.png")
    print(f"Test similarity score: {score}")
