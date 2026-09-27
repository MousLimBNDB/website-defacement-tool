import logging
import database
import ollama_analyzer

logger = logging.getLogger(__name__)

def analyze_defacement(
    baseline_path: str,
    current_path: str,
    diff_path: str,
    popup_path: str = None
) -> dict:
    """
    Unified AI analysis dispatcher for Ollama vision models.
    Checks database settings to determine if LLM visual analysis is enabled (use_llm=true).

    Args:
        baseline_path: Path to clean baseline screenshot.
        current_path: Path to current captured screenshot.
        diff_path: Path to visual diff highlight screenshot.
        popup_path: Optional path to isolated popup screenshot.

    Returns:
        dict: Analysis result containing is_defaced, confidence, change_type, analysis_summary.
    """
    try:
        settings = database.get_settings()
    except Exception:
        settings = {}

    # Check if LLM usage is enabled
    use_llm = str(settings.get("use_llm", "true")).lower() in ("true", "1", "yes")

    if not use_llm:
        logger.info("LLM visual analysis is disabled in settings. Skipping Ollama AI evaluation.")
        return {
            "is_defaced": False,
            "confidence": 0,
            "change_type": "LLM Disabled",
            "analysis_summary": "Visual anomaly detected by image comparator, but LLM analysis is disabled in settings."
        }

    ollama_url = settings.get("ollama_url", "http://localhost:11434")
    ollama_model = settings.get("ollama_model", "llama3.2-vision")

    logger.info(f"Delegating visual defacement analysis to Ollama ({ollama_model} at {ollama_url}).")
    return ollama_analyzer.analyze_defacement(
        baseline_path=baseline_path,
        current_path=current_path,
        diff_path=diff_path,
        popup_path=popup_path,
        ollama_url=ollama_url,
        model=ollama_model
    )
