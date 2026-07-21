import os
import logging
import json
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Define the structured response schema using Pydantic
class DefacementAnalysis(BaseModel):
    is_defaced: bool = Field(description="True if the website exhibits signs of malicious defacement, hacking, hijacking, phishing insertions, or extreme vandalism. False otherwise.")
    confidence: int = Field(description="Confidence rating from 0 to 100 on the detection result.")
    change_type: str = Field(description="Categorization of the changes: 'No Change', 'Regular Content Update' (news, articles, dynamic ads), 'Layout Bug' (broken CSS/layout but non-malicious), or 'Defacement' (malicious hijacking, hacking messages).")
    analysis_summary: str = Field(description="A concise summary detailing what changed and explaining the diagnostic decision.")

def analyze_defacement(baseline_path: str, current_path: str, diff_path: str) -> dict:
    """
    Sends the baseline, current, and diff-highlighted screenshots to Gemini to analyze
    whether defacement occurred.
    
    Returns a dictionary matching the DefacementAnalysis structure.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or "AQ.Ab8RN6IZcGjUJHLZvKxWo1BFnOg2cLX_b3Bm7M7AEZ--4Wl77Q"
    if not api_key:
        logger.warning("GEMINI_API_KEY environment variable is not set. Visual AI analysis will be skipped.")
        return {
            "is_defaced": False,
            "confidence": 0,
            "change_type": "No API Key Provided",
            "analysis_summary": "Gemini API key is not configured. Please set the GEMINI_API_KEY environment variable to enable AI defacement analysis."
        }
        
    try:
        # Initialize the client with the resolved API key
        client = genai.Client(api_key=api_key)
        
        # Read the image files as bytes
        contents = []
        
        for name, path in [("Baseline Screenshot", baseline_path), 
                           ("Current Screenshot", current_path), 
                           ("Highlighted Differences (Red pixels show changes)", diff_path)]:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    img_bytes = f.read()
                contents.append(f"--- Image: {name} ---")
                contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
            else:
                logger.warning(f"Image not found for analysis: {path}")

        if not contents:
            return {
                "is_defaced": False,
                "confidence": 0,
                "change_type": "Error",
                "analysis_summary": "No screenshot images found to send to the AI."
            }

        # Prompt instruction
        prompt = (
            "You are a cybersecurity expert monitoring websites for defacement, hijacking, and malicious modification.\n"
            "Analyze these three screenshots: the baseline (known clean site), the current snapshot, and the highlighted differences "
            "(where red markings represent changed visual pixels).\n\n"
            "Distinguish between:\n"
            "1. Normal changes (e.g. news headlines updating, advertisements changing, dynamic carousel shifts, dates updating).\n"
            "2. Visual layout errors (e.g. CSS files failing to load, images broken - non-malicious).\n"
            "3. Malicious defacement (e.g. hacking manifestos, replacement with political messages, offensive slurs, malicious banners, phishing text, completely blacked-out screens with hacker names).\n\n"
            "Return a structured evaluation detailing if this is a defacement attack."
        )
        contents.append(prompt)

        logger.info("Sending screenshots to Gemini for multimodal analysis...")
        
        # Use gemini-2.5-flash as the standard fast multimodal model
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=DefacementAnalysis,
                temperature=0.1
            )
        )
        
        # Parse the structured JSON response
        result = json.loads(response.text)
        logger.info(f"Gemini Analysis complete. Result: {result}")
        return result

    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}", exc_info=True)
        return {
            "is_defaced": False,
            "confidence": 0,
            "change_type": "API Error",
            "analysis_summary": f"Failed to perform AI analysis due to API error: {str(e)}"
        }

# Self-test block
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # This will use dummy files or fail gracefully if no API key is present
    res = analyze_defacement("screenshots/test_base.png", "screenshots/test_current.png", "screenshots/test_diff.png")
    print(json.dumps(res, indent=2))
