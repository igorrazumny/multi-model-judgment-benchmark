"""Three-tier evaluation: standalone → aggregation → debate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from mmjb.client import InferenceClient


STANDALONE_SYSTEM = (
    "You are an expert reviewer. Analyze the task carefully. "
    "List distinct findings as bullet points. Mark each as Material or Minor."
)

AGGREGATION_SYSTEM = (
    "You are an expert aggregator. You receive the original task and several "
    "standalone expert answers. Produce a consolidated assessment: valid findings, "
    "false positives, and misses. Be specific."
)

DEBATE_FOR_AGAINST = (
    "For each candidate finding below, write (1) the strongest argument FOR validity "
    "and (2) the strongest argument AGAINST. Be concise."
)

DEBATE_VERDICT = (
    "Given the arguments, vote VALID or INVALID for each finding id. "
    "Reply as lines: FINDING_ID: VALID|INVALID"
)


@dataclass
class PanelResult:
    model: str
    text: str
    tier: str


@dataclass
class RunBundle:
    task: str
    standalone: list[PanelResult] = field(default_factory=list)
    aggregation: list[PanelResult] = field(default_factory=list)
    debate_args: list[PanelResult] = field(default_factory=list)
    debate_votes: list[PanelResult] = field(default_factory=list)


def load_task_body(path: str) -> str:
    text = open(path, encoding="utf-8").read()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return text.strip()


def run_standalone(
    client: InferenceClient,
    models: list[str],
    task: str,
    call: Callable[..., str] | None = None,
) -> list[PanelResult]:
    call = call or client.chat
    out: list[PanelResult] = []
    for m in models:
        text = call(
            m,
            [
                {"role": "system", "content": STANDALONE_SYSTEM},
                {"role": "user", "content": task},
            ],
        )
        out.append(PanelResult(model=m, text=text, tier="standalone"))
    return out


def run_aggregation(
    client: InferenceClient,
    models: list[str],
    task: str,
    standalone: list[PanelResult],
    call: Callable[..., str] | None = None,
) -> list[PanelResult]:
    call = call or client.chat
    digest = "\n\n".join(
        f"### Expert {i+1} ({r.model})\n{r.text}" for i, r in enumerate(standalone)
    )
    user = f"## Task\n{task}\n\n## Standalone panel answers\n{digest}"
    out: list[PanelResult] = []
    for m in models:
        text = call(
            m,
            [
                {"role": "system", "content": AGGREGATION_SYSTEM},
                {"role": "user", "content": user},
            ],
        )
        out.append(PanelResult(model=m, text=text, tier="aggregation"))
    return out


def run_debate(
    client: InferenceClient,
    models: list[str],
    findings_block: str,
    call: Callable[..., str] | None = None,
) -> tuple[list[PanelResult], list[PanelResult]]:
    """Two-pass debate: for/against, then VALID/INVALID votes."""
    call = call or client.chat
    args: list[PanelResult] = []
    for m in models:
        text = call(
            m,
            [
                {"role": "system", "content": DEBATE_FOR_AGAINST},
                {"role": "user", "content": findings_block},
            ],
        )
        args.append(PanelResult(model=m, text=text, tier="debate_r1"))
    arg_digest = "\n\n".join(f"### {r.model}\n{r.text}" for r in args)
    votes: list[PanelResult] = []
    user2 = f"## Findings\n{findings_block}\n\n## Panel arguments\n{arg_digest}"
    for m in models:
        text = call(
            m,
            [
                {"role": "system", "content": DEBATE_VERDICT},
                {"role": "user", "content": user2},
            ],
        )
        votes.append(PanelResult(model=m, text=text, tier="debate_r2"))
    return args, votes


def default_models() -> list[str]:
    import os

    env = os.environ.get("MMJB_MODELS", "").strip()
    if env:
        return [x.strip() for x in env.split(",") if x.strip()]
    # Placeholders — replace via config or env for a real run
    return [
        "anthropic-opus",
        "openai-gpt",
        "google-gemini",
        "xai-grok",
        "alibaba-qwen",
        "moonshot-kimi",
    ]
