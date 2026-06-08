"""Baseline save/diff for tracking output drift."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from .models import TestResult


def save_baseline(results: List[TestResult], path: Path) -> None:
    data = {r.test_id: r.output for r in results}
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_baseline(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def cosine_similarity(a: List[float], b: List[float]) -> float:
    import math
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x ** 2 for x in a))
    mag_b = math.sqrt(sum(x ** 2 for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def diff_baseline(
    results: List[TestResult],
    baseline: Dict[str, str],
    similarity_threshold: float = 0.85,
) -> List[Dict]:
    """Compare current outputs to baseline using simple character-level similarity.

    For production use, replace with embedding-based cosine similarity.
    """
    diffs = []
    for r in results:
        if r.test_id not in baseline:
            diffs.append({"test_id": r.test_id, "status": "new", "similarity": None})
            continue
        old = baseline[r.test_id]
        new = r.output
        # Simple Jaccard similarity on word sets as a lightweight proxy
        old_words = set(old.lower().split())
        new_words = set(new.lower().split())
        if not old_words and not new_words:
            sim = 1.0
        elif not old_words or not new_words:
            sim = 0.0
        else:
            sim = len(old_words & new_words) / len(old_words | new_words)

        if sim < similarity_threshold:
            diffs.append({
                "test_id": r.test_id,
                "status": "drifted",
                "similarity": round(sim, 3),
                "old_preview": old[:80],
                "new_preview": new[:80],
            })
    return diffs
