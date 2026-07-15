"""Leave-one-out consensus alignment scoring (production-style construct).

This is a *reference sketch* of the paper's production scoring idea:
coverage of a consensus finding set, not independent ground truth.
GPQA should use known-answer accuracy instead.
"""

from __future__ import annotations

import re
from collections import defaultdict


def parse_vote_lines(text: str) -> dict[str, str]:
    votes: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"\s*([A-Za-z0-9_.-]+)\s*:\s*(VALID|INVALID)\b", line, re.I)
        if m:
            votes[m.group(1)] = m.group(2).upper()
    return votes


def majority_valid(
    panel_votes: list[dict[str, str]],
    threshold: int,
) -> set[str]:
    """Findings with at least `threshold` VALID votes."""
    counts: dict[str, int] = defaultdict(int)
    for votes in panel_votes:
        for fid, v in votes.items():
            if v == "VALID":
                counts[fid] += 1
    return {fid for fid, c in counts.items() if c >= threshold}


def leave_one_out_coverage(
    model_findings: dict[str, set[str]],
    consensus: set[str],
) -> dict[str, float]:
    """Share of consensus findings present in each model's set (simple coverage)."""
    if not consensus:
        return {m: 0.0 for m in model_findings}
    out = {}
    for m, s in model_findings.items():
        # Leave-one-out would rebuild consensus without m; for the sketch we
        # report simple coverage of the full consensus set.
        out[m] = len(s & consensus) / len(consensus)
    return out
