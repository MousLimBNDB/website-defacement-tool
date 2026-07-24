import os
import logging
import json
import base64
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

def analyze_defacement(baseline_path: str, current_path: str, diff_path: str, ollama_url: str = "http://localhost:11434", model: str = "llama3.2-vision") -> dict:
    """
    Sends baseline, current, and diff-highlighted screenshots to a local Ollama vision model
    (e.g., llama3.2-vision, llava, qwen2-vl) to evaluate whether a website has been defaced.
    
    Returns a dictionary with:
      - is_defaced: bool
      - confidence: int (0 to 100)
      - change_type: str
      - analysis_summary: str
    """
    if not ollama_url:
        ollama_url = "http://localhost:11434"
    if not model:
        model = "llama3.2-vision"

    # Normalize host URL
    ollama_url = ollama_url.rstrip("/")
    api_endpoint = f"{ollama_url}/api/generate"

    # Base64 encode available screenshots
    images_b64 = []
    image_names = []
    
    for name, path in [("Baseline", baseline_path), 
                       ("Current", current_path), 
                       ("Visual Diff", diff_path)]:
        if os.path.exists(path):
            try:
                with open(path, "rb") as img_file:
                    b64_str = base64.b64encode(img_file.read()).decode("utf-8")
                    images_b64.append(b64_str)
                    image_names.append(name)
            except Exception as e:
                logger.warning(f"Failed to read image {path}: {e}")

    if not images_b64:
        return {
            "is_defaced": False,
            "confidence": 0,
            "change_type": "Error",
            "analysis_summary": "No screenshot images found to send to Ollama AI."
        }

    prompt = (
        "You are a cybersecurity expert monitoring websites for defacement, hacking, and malicious modification.\n"
        f"Analyze these {len(images_b64)} screenshots ({', '.join(image_names)}):\n"
        "1. Baseline (clean site)\n"
        "2. Current snapshot\n"
        "3. Highlighted differences (red pixels show visual changes)\n\n"
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
        
        # Timeout after 15 seconds for local Vision model inference
        with urllib.request.urlopen(req, timeout=15) as response:
            res_raw = response.read().decode("utf-8")
            res_json = json.loads(res_raw)
            response_text = res_json.get("response", "").strip()

            # Clean markdown codeblocks if Ollama wrapped output in ```json ... ```
            if response_text.startswith("```"):
                lines = response_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                response_text = "\n".join(lines).strip()

            result = json.loads(response_text)
            logger.info(f"Ollama AI Analysis complete. Result: {result}")

            return {
                "is_defaced": bool(result.get("is_defaced", False)),
                "confidence": int(result.get("confidence", 0)),
                "change_type": str(result.get("change_type", "Unknown")),
                "analysis_summary": str(result.get("analysis_summary", "Ollama analysis finished."))
            }

    except urllib.error.URLError as e:
        error_msg = (
            f"Could not connect to Ollama at '{ollama_url}'. "
            f"Please ensure Ollama is running (`ollama serve`) and the model '{model}' is pulled (`ollama pull {model}`). Details: {e}"
        )
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
