import os
import sys
import json
import argparse
from pathlib import Path
import config

def get_targets(target_id: int = None, active_only: bool = True):
    """
    Reads target websites from targets.json.
    
    Args:
        target_id: Optional ID to fetch a single target.
        active_only: If True, filters only targets where is_active is True.
        
    Returns:
        List of target dictionaries.
    """
    targets_path = Path(config.TARGETS_FILE)
    if not targets_path.exists():
        return []

    with open(targets_path, "r", encoding="utf-8") as f:
        raw_targets = json.load(f)

    normalized_targets = []
    for t in raw_targets:
        if not isinstance(t, dict):
            continue
        target_obj = {
            "id": int(t.get("id", 1)),
            "name": str(t.get("name", "")),
            "url": str(t.get("url", "")),
            "is_active": bool(t.get("is_active", True)),
            "ignored_selectors": str(t.get("ignored_selectors") or ""),
            "target_selectors": str(t.get("target_selectors") or ""),
            "check_interval_mins": int(t.get("check_interval_mins", 5))
        }
        normalized_targets.append(target_obj)

    targets = normalized_targets

    if active_only:
        targets = [t for t in targets if t.get("is_active", True)]

    if target_id is not None:
        targets = [t for t in targets if t.get("id") == target_id]

    return targets

def main():
    parser = argparse.ArgumentParser(description="Node 1: Target URLs Provider for n8n workflow")
    parser.add_argument("--id", type=int, default=None, help="Fetch specific target ID")
    parser.add_argument("--all", action="store_true", help="Fetch all targets including inactive")
    args = parser.parse_args()

    targets = get_targets(target_id=args.id, active_only=not args.all)
    # Output JSON array for n8n
    print(json.dumps(targets, indent=2))

if __name__ == "__main__":
    main()
