import os
import sys
import json
import logging
import argparse
from pathlib import Path
from PIL import Image, ImageChops, ImageEnhance

import config

logger = logging.getLogger(__name__)

def expand_to_canvas(img: Image.Image, target_width: int, target_height: int, bg_color=(255, 255, 255)) -> Image.Image:
    """
    Expands an image onto a new neutral canvas sized (target_width, target_height)
    pasted at coordinate (0, 0).
    Eliminates image distortion and squashing caused by resizing.
    """
    if img.size == (target_width, target_height):
        return img
        
    canvas = Image.new("RGB", (target_width, target_height), bg_color)
    canvas.paste(img, (0, 0))
    return canvas

def compare_screenshots(
    baseline_path: str,
    current_path: str,
    diff_path: str = None,
    threshold: int = None
) -> dict:
    """
    Compares baseline and current screenshots using Canvas Expansion (Letterboxing/Padding).
    
    Args:
        baseline_path: Path to clean baseline screenshot.
        current_path: Path to current capture.
        diff_path: Path to save visual difference highlight image.
        threshold: Pixel difference threshold (0-255). Defaults to config.PIXEL_DIFF_THRESHOLD.
        
    Returns:
        dict: {
            "similarity_score": float (0.0 to 1.0),
            "changed_pixels": int,
            "total_pixels": int,
            "diff_path": str,
            "width": int,
            "height": int,
            "canvas_expanded": bool
        }
    """
    if threshold is None:
        threshold = config.PIXEL_DIFF_THRESHOLD

    if not os.path.exists(baseline_path):
        logger.warning(f"Baseline screenshot not found: {baseline_path}")
        return {"similarity_score": 0.0, "error": f"Baseline not found: {baseline_path}"}

    if not os.path.exists(current_path):
        logger.warning(f"Current screenshot not found: {current_path}")
        return {"similarity_score": 0.0, "error": f"Current not found: {current_path}"}

    try:
        img_base = Image.open(baseline_path).convert("RGB")
        img_curr = Image.open(current_path).convert("RGB")

        # Determine canvas dimensions based on maximum width and height
        max_w = max(img_base.width, img_curr.width)
        max_h = max(img_base.height, img_curr.height)
        canvas_expanded = (img_base.size != img_curr.size)

        if canvas_expanded:
            logger.info(
                f"Applying Canvas Expansion: Base={img_base.size}, Curr={img_curr.size} -> Canvas=({max_w}x{max_h})"
            )

        # Place both images at (0, 0) on separate expanded canvases
        canvas_base = expand_to_canvas(img_base, max_w, max_h)
        canvas_curr = expand_to_canvas(img_curr, max_w, max_h)

        # Pixel-for-pixel difference
        diff = ImageChops.difference(canvas_base, canvas_curr)
        diff_gray = diff.convert("L")

        # Count changed pixels exceeding the noise threshold
        pixels = list(diff_gray.getdata())
        changed_pixels = sum(1 for p in pixels if p > threshold)
        total_pixels = len(pixels)

        diff_ratio = changed_pixels / total_pixels if total_pixels > 0 else 0.0
        similarity_score = max(0.0, min(1.0, 1.0 - diff_ratio))

        logger.info(
            f"Comparison Result: Similarity={similarity_score:.4f} (Changed: {changed_pixels}/{total_pixels})"
        )

        # Save visual diff highlight if diff_path is specified
        saved_diff_path = ""
        if diff_path:
            os.makedirs(os.path.dirname(os.path.abspath(diff_path)), exist_ok=True)
            mask = diff_gray.point(lambda x: 255 if x > threshold else 0)
            red_overlay = Image.new("RGB", (max_w, max_h), (255, 0, 0))
            
            # Dim current canvas slightly to enhance visual contrast of red difference areas
            dimmer = ImageEnhance.Brightness(canvas_curr)
            dimmed_curr = dimmer.enhance(0.75)
            
            diff_visual = Image.composite(red_overlay, dimmed_curr, mask)
            diff_visual.save(diff_path)
            saved_diff_path = diff_path
            logger.info(f"Saved visual diff highlight image to {diff_path}")

        return {
            "similarity_score": round(similarity_score, 4),
            "changed_pixels": changed_pixels,
            "total_pixels": total_pixels,
            "diff_path": saved_diff_path,
            "width": max_w,
            "height": max_h,
            "canvas_expanded": canvas_expanded
        }

    except Exception as e:
        logger.error(f"Image comparison failed: {e}", exc_info=True)
        return {"similarity_score": 0.0, "error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Node 4: Pillow Image Comparator (Canvas Expansion) for n8n")
    parser.add_argument("--baseline", required=True, help="Baseline screenshot file path")
    parser.add_argument("--current", required=True, help="Current screenshot file path")
    parser.add_argument("--diff-output", default=None, help="Output visual diff file path")
    parser.add_argument("--threshold", type=int, default=None, help="Pixel difference threshold")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    res = compare_screenshots(
        baseline_path=args.baseline,
        current_path=args.current,
        diff_path=args.diff_output,
        threshold=args.threshold
    )
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
