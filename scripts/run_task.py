#!/usr/bin/env python3
"""Run the reference multi-model protocol on one task file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

try:
    from dotenv import load_dotenv
except ImportError:  # optional
    def load_dotenv(*_a, **_k):  # type: ignore
        return False

from mmjb.pipeline import (
    default_models,
    load_task_body,
    run_aggregation,
    run_debate,
    run_standalone,
)


def main() -> int:
    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("task", type=Path, help="Path to task_XXX.md")
    ap.add_argument(
        "--tier",
        choices=("standalone", "aggregation", "debate", "all"),
        default="all",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print plan only; no API")
    ap.add_argument("--out", type=Path, default=None, help="Write JSON bundle here")
    args = ap.parse_args()

    task = load_task_body(str(args.task))
    models = default_models()
    print(f"task_chars={len(task)} models={models}")

    if args.dry_run:
        print("dry-run: would run tiers:", args.tier)
        print(task[:400], "..." if len(task) > 400 else "")
        return 0

    from mmjb.client import InferenceClient

    client = InferenceClient()
    bundle: dict = {"task_file": str(args.task), "models": models}

    if args.tier in ("standalone", "all"):
        standalone = run_standalone(client, models, task)
        bundle["standalone"] = [{"model": r.model, "text": r.text} for r in standalone]
        print(f"standalone done ({len(standalone)} models)")
    else:
        standalone = []

    if args.tier in ("aggregation", "all"):
        if not standalone:
            raise SystemExit("aggregation needs standalone first (use --tier all)")
        agg = run_aggregation(client, models, task, standalone)
        bundle["aggregation"] = [{"model": r.model, "text": r.text} for r in agg]
        print(f"aggregation done ({len(agg)} models)")

    if args.tier in ("debate", "all"):
        # Minimal finding list: ask first model to list IDs (production uses extractor)
        findings_block = (
            "F1: Primary defect or issue identified in standalone answers\n"
            "F2: Secondary issue or risk\n"
            "F3: Missing alternative or incomplete analysis\n"
            "(Replace with extracted findings in a full pipeline.)"
        )
        args_r, votes = run_debate(client, models, findings_block)
        bundle["debate_r1"] = [{"model": r.model, "text": r.text} for r in args_r]
        bundle["debate_r2"] = [{"model": r.model, "text": r.text} for r in votes]
        print(f"debate done ({len(votes)} models)")

    out = args.out or (ROOT / "outputs" / f"{args.task.stem}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, indent=2) + "\n")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
