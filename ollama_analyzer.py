import os
import sys
import json
import base64
import logging
import argparse
import urllib.request
import urllib.error

import config

logger = logging.getLogger(__name__)

def encode_image(image_path: str) -> str:
    """Encodes an image file to a base64 string."""
    if not image_path or not os.path.exists(image_path):
        return ""
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logger.warning(f"Failed to read image {image_path}: {e}")
        return ""

def analyze_defacement(
    baseline_path: str,
    current_path: str,
    diff_path: str = "",
    popup_path: str = "",
    ollama_host: str = None,
    model: str = None,
    target_id: int = 1,
    url: str = ""
) -> dict:
    """
    Sends screenshots (baseline, current, visual diff, and optional popup) to the Multimodal Vision AI
    running on the client VM (e.g., Qwen3:4B / Qwen2.5-VL via Ollama) to diagnose potential defacement.
    
    Returns:
        dict: {
            "is_defaced": bool,
            "confidence": int (0 - 100),
            "change_type": str,
            "analysis_summary": str,
            "popup_analyzed": bool,
            "popup_defaced": bool,
            "target_id": int,
            "url": str
        }
    """
    host = (ollama_host or config.OLLAMA_HOST).rstrip("/")
    model_name = model or config.OLLAMA_MODEL
    api_endpoint = f"{host}/api/generate"

    images_b64 = []
    image_descriptions = []

    # Baseline Image
    b64_base = encode_image(baseline_path)
    if b64_base:
        images_b64.append(b64_base)
        image_descriptions.append("Image 1: Baseline Clean Webpage")

    # Current Snapshot
    b64_curr = encode_image(current_path)
    if b64_curr:
        images_b64.append(b64_curr)
        image_descriptions.append("Image 2: Current Webpage Snapshot")

    # Visual Diff (Red highlight)
    b64_diff = encode_image(diff_path)
    if b64_diff:
        images_b64.append(b64_diff)
        image_descriptions.append("Image 3: Visual Diff (Red areas indicate pixel discrepancies)")

    # Isolated Popup Snapshot (if captured)
    has_popup = bool(popup_path and os.path.exists(popup_path))
    if has_popup:
        b64_popup = encode_image(popup_path)
        if b64_popup:
            images_b64.append(b64_popup)
            image_descriptions.append("Image 4: Isolated Popup / Overlay Dialog captured on this site")

    if not images_b64:
        return {
            "is_defaced": False,
            "confidence": 0,
            "change_type": "ERROR",
            "analysis_summary": "No screenshot images found to send to Ollama AI.",
            "popup_analyzed": False,
            "popup_defaced": False,
            "target_id": target_id,
            "url": url
        }

    prompt = (
        "You are an expert cybersecurity monitoring agent inspecting a website for defacement, unauthorized modification, or malicious popups.\n\n"
        f"You are provided with {len(images_b64)} images:\n" +
        "\n".join(f"- {desc}" for desc in image_descriptions) +
        "\n\nTask instructions:\n"
        "1. Compare the Baseline vs Current snapshot using the Visual Diff highlights.\n"
        "2. If an isolated popup image is provided, evaluate whether it is a legitimate UI element (e.g. standard cookie/GDPR consent, newsletter signup) or an injected malicious phishing banner / fake login / hacker manifesto.\n"
        "3. Categorize the change into one of:\n"
        "   - 'Defacement': Unauthorized modification, graffiti, political messaging, defacement text, black screen, fake injected phishing overlay.\n"
        "   - 'Regular Content Update': Normal news updates, dynamic blog feed, timestamp shifts, changing promotional banners.\n"
        "   - 'Layout Bug': Broken CSS stylesheets, missing images, non-malicious layout shifts.\n"
        "   - 'No Change': Minor pixel noise or rendering anti-aliasing differences.\n\n"
        "Respond ONLY with a single valid JSON object strictly matching this schema, without conversational preamble or markdown code blocks:\n"
        "{\n"
        '  "is_defaced": true or false,\n'
        '  "confidence": integer between 0 and 100,\n'
        '  "change_type": "Defacement" | "Regular Content Update" | "Layout Bug" | "No Change",\n'
        '  "popup_defaced": true or false,\n'
        '  "analysis_summary": "Concise technical explanation of observed changes and verdict"\n'
        "}"
    )

    payload = {
        "model": model_name,
        "prompt": prompt,
        "images": images_b64,
        "stream": False,
        "format": "json"
    }

    try:
        logger.info(f"Connecting to Ollama Multimodal VM ({host}) using model '{model_name}'...")
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            api_endpoint,
            data=req_data,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=config.OLLAMA_TIMEOUT) as response:
            res_raw = response.read().decode("utf-8")
            res_json = json.loads(res_raw)
            response_text = res_json.get("response", "").strip()

            # Clean markdown formatting if present
            if response_text.startswith("```"):
                lines = response_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                response_text = "\n".join(lines).strip()

            parsed = json.loads(response_text)
            logger.info(f"Ollama Vision response: {parsed}")

            return {
                "is_defaced": bool(parsed.get("is_defaced", False)),
                "confidence": int(parsed.get("confidence", 0)),
                "change_type": str(parsed.get("change_type", "Unknown")),
                "popup_analyzed": has_popup,
                "popup_defaced": bool(parsed.get("popup_defaced", False)),
                "analysis_summary": str(parsed.get("analysis_summary", "")),
                "target_id": target_id,
                "url": url
            }

    except urllib.error.URLError as e:
        msg = f"Cannot reach Ollama at '{host}'. Please verify the VM IP/port and ensure Ollama is serving model '{model_name}'. Details: {e}"
        logger.warning(msg)
        return {
            "is_defaced": False,
            "confidence": 0,
            "change_type": "AI_OFFLINE",
            "popup_analyzed": has_popup,
            "popup_defaced": False,
            "analysis_summary": msg,
            "target_id": target_id,
            "url": url
        }
    except Exception as e:
        logger.error(f"Error in Ollama vision evaluation: {e}", exc_info=True)
        return {
            "is_defaced": False,
            "confidence": 0,
            "change_type": "AI_ERROR",
            "popup_analyzed": has_popup,
            "popup_defaced": False,
            "analysis_summary": f"Ollama execution error: {e}",
            "target_id": target_id,
            "url": url
        }

def main():
    parser = argparse.ArgumentParser(description="Node 6: Ollama Multimodal Vision AI Node for n8n")
    parser.add_argument("--baseline", required=True, help="Baseline screenshot path")
    parser.add_argument("--current", required=True, help="Current screenshot path")
    parser.add_argument("--diff", default="", help="Visual diff screenshot path")
    parser.add_argument("--popup", default="", help="Isolated popup screenshot path")
    parser.add_argument("--host", default=None, help="Ollama host URL (e.g. http://<vm-ip>:11434)")
    parser.add_argument("--model", default=None, help="Ollama vision model name (e.g. qwen3:4b)")
    parser.add_argument("--target-id", type=int, default=1, help="Target ID")
    parser.add_argument("--url", default="", help="Target website URL")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    res = analyze_defacement(
        baseline_path=args.baseline,
        current_path=args.current,
        diff_path=args.diff,
        popup_path=args.popup,
        ollama_host=args.host,
        model=args.model,
        target_id=args.target_id,
        url=args.url
    )
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
