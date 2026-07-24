import logging
import database
import ollama_analyzer


logger = logging.getLogger(__name__)

def analyze_defacement(baseline_path: str, current_path: str, diff_path: str) -> dict:
    """
    Unified AI analysis dispatcher. Checks database settings for configured provider
    ('ollama' or 'gemini') and delegates screenshot evaluation.
    """
    try:
        settings = database.get_settings()
    except Exception:
        settings = {}

    # Directly use Ollama (ignore provider setting)
    ollama_url = settings.get("ollama_url", "http://localhost:11434")
    ollama_model = settings.get("ollama_model", "llama3.2-vision")
    logger.info(f"Using Ollama AI provider ({ollama_model} at {ollama_url}) for visual defacement analysis.")
    return ollama_analyzer.analyze_defacement(
        baseline_path=baseline_path,
        current_path=current_path,
        diff_path=diff_path,
        ollama_url=ollama_url,
        model=ollama_model,
    )
