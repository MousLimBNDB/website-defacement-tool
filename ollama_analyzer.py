import os
import logging
import json
import base64
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

def analyze_defacement(
    baseline_path: str,
    current_path: str,
    diff_path: str,
    popup_path: str = None,
    ollama_url: str = "http://localhost:11434",
    model: str = "llama3.2-vision"
) -> dict:
    """
    Sends baseline, current, diff-highlighted, and optional popup screenshots to a local Ollama vision model
    (e.g., llama3.2-vision, llava, qwen2-vl) to evaluate whether a website has been defaced.

    Args:
        baseline_path: Path to baseline screenshot.
        current_path: Path to current screenshot.
        diff_path: Path to visual diff highlight screenshot.
        popup_path: Optional path to isolated popup screenshot.
        ollama_url: Base URL of local Ollama server.
        model: Vision model tag name.

    Returns:
        dict: Evaluation dictionary with keys: is_defaced, confidence, change_type, analysis_summary.
    """
    if not ollama_url:
        ollama_url = "http://localhost:11434"
    if not model:
        model = "llama3.2-vision"

    ollama_url = ollama_url.rstrip("/")
    api_endpoint = f"{ollama_url}/api/generate"

    images_b64 = []
    image_names = []

    candidates = [
        ("Baseline", baseline_path),
        ("Current", current_path),
        ("Visual Diff", diff_path)
    ]
    if popup_path and os.path.exists(popup_path):
        candidates.append(("Isolated Popup", popup_path))

    for name, path in candidates:
        if path and os.path.exists(path):
            try:
                with open(path, "rb") as img_file:
                    b64_str = base64.b64encode(img_file.read()).decode("utf-8")
                    images_b64.append(b64_str)
                    image_names.append(name)
            except Exception as e:
                logger.warning(f"Failed to encode image {path}: {e}")

    if not images_b64:
        return {
            "is_defaced": False,
            "confidence": 0,
            "change_type": "Error",
            "analysis_summary": "No valid screenshot images found for Ollama AI evaluation."
        }

    prompt = (
        "You are a cybersecurity expert monitoring websites for defacement, unauthorized modification, and hacking.\n"
        f"Analyze these {len(images_b64)} screenshots ({', '.join(image_names)}):\n"
        "1. Baseline (clean site)\n"
        "2. Current snapshot\n"
        "3. Highlighted differences (red pixels show visual changes)\n"
        + ("4. Isolated Popup modal\n" if "Isolated Popup" in image_names else "") + "\n"
        "Distinguish between:\n"
        "- Normal content updates (news articles, dynamic ads, date shifts).\n"
        "- Visual layout bugs (broken CSS, missing images - non-malicious).\n"
        "- Malicious defacement (hacking manifestos, political slogans, offensive slurs, malicious banners, phishing text, blacked-out screens).\n\n"
        "Respond ONLY with a single valid JSON object strictly matching this schema, without markdown blocks:\n"
        "{\n"
        '  "is_defaced": true or false,\n'
        '  "confidence": integer between 0 and 100,\n'
        '  "change_type": "Defacement" or "Regular Content Update" or "Layout Bug" or "No Change",\n'
        '  "analysis_summary": "Concise explanation of changes and diagnostic decision"\n'
        "}"
    )

    payload = {
        "model": model,
        "prompt": prompt,
        "images": images_b64,
        "stream": False,
        "format": "json"
    }

    try:
        logger.info(f"Sending screenshots to local Ollama AI ({model} at {ollama_url})...")
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            api_endpoint,
            data=req_data,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=20) as response:
            res_raw = response.read().decode("utf-8")
            res_json = json.loads(res_raw)
            response_text = res_json.get("response", "").strip()

            if response_text.startswith("```"):
                lines = response_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                response_text = "\n".join(lines).strip()

            result = json.loads(response_text)
            logger.info(f"Ollama AI analysis complete. Result: {result}")

            return {
                "is_defaced": bool(result.get("is_defaced", False)),
                "confidence": int(result.get("confidence", 0)),
                "change_type": str(result.get("change_type", "Unknown")),
                "analysis_summary": str(result.get("analysis_summary", "Ollama analysis finished."))
            }

    except urllib.error.URLError as e:
        error_msg = f"Could not connect to Ollama at '{ollama_url}': {e}"
        logger.error(error_msg)
        return {
            "is_defaced": False,
            "confidence": 0,
            "change_type": "Ollama Connection Error",
            "analysis_summary": error_msg
        }
    except Exception as e:
        logger.error(f"Error calling Ollama API: {e}", exc_info=True)
        return {
            "is_defaced": False,
            "confidence": 0,
            "change_type": "AI Error",
            "analysis_summary": f"Failed to perform Ollama AI analysis: {str(e)}"
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = analyze_defacement("static/screenshots/test_base.png", "static/screenshots/test_current.png", "static/screenshots/test_diff.png")
    print(json.dumps(res, indent=2))
