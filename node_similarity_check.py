import sys
import json
import argparse
import config

def check_similarity(
    similarity: float,
    threshold: float = None,
    target_id: int = 1,
    url: str = "",
    baseline_path: str = "",
    current_path: str = "",
    diff_path: str = "",
    popup_path: str = ""
) -> dict:
    """
    Evaluates similarity score against threshold to decide workflow routing.
    
    Returns:
        dict with route: 'INVESTIGATE' (if similarity < threshold) or 'NORMAL'
    """
    if threshold is None:
        threshold = config.SIMILARITY_THRESHOLD

    is_below = similarity < threshold
    route = "INVESTIGATE" if is_below else "NORMAL"

    return {
        "route": route,
        "is_below_threshold": is_below,
        "similarity_score": similarity,
        "threshold": threshold,
        "target_id": target_id,
        "url": url,
        "baseline_path": baseline_path,
        "current_path": current_path,
        "diff_path": diff_path,
        "popup_path": popup_path
    }

def main():
    parser = argparse.ArgumentParser(description="Node 5: Similarity Score Check & Router for n8n")
    parser.add_argument("--similarity", type=float, required=True, help="Similarity score (0.0 - 1.0)")
    parser.add_argument("--threshold", type=float, default=None, help="Threshold value")
    parser.add_argument("--target-id", type=int, default=1, help="Target ID")
    parser.add_argument("--url", default="", help="Target URL")
    parser.add_argument("--baseline", default="", help="Baseline screenshot path")
    parser.add_argument("--current", default="", help="Current screenshot path")
    parser.add_argument("--diff", default="", help="Visual diff screenshot path")
    parser.add_argument("--popup", default="", help="Popup screenshot path")
    args = parser.parse_args()

    res = check_similarity(
        similarity=args.similarity,
        threshold=args.threshold,
        target_id=args.target_id,
        url=args.url,
        baseline_path=args.baseline,
        current_path=args.current,
        diff_path=args.diff,
        popup_path=args.popup
    )
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
