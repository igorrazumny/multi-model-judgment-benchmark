# Multi-Model Judgment Benchmark (reference implementation)

Reference implementation of **multi-model aggregation and adversarial debate** for judgment quality evaluation, as described in:

> *The Cortical Architecture for Judgment Quality: Multi-Agent Consensus and Deliberation*  
> Igor Razumny, 2026

This is a **working reference**, not the full production service. It implements the evaluation protocol (standalone → aggregation → debate) against a configurable multi-model API.

## What is included

| Path | Contents |
|------|----------|
| `src/mmjb/` | Pipeline: call models, aggregate, debate rounds, leave-one-out consensus scoring sketch |
| `data/production_tasks/` | **Redacted** production-style tasks used for evaluation |
| `data/gpqa_diamond_responses/` | **Full model responses** on GPQA Diamond (198 paper items) |
| `data/gpqa/README.md` | GPQA official links + pointer to response dump |
| `config/models.example.yaml` | Example expert panel |
| `scripts/run_task.py` | Run the three-tier protocol on one task file |

## Data availability

### Production tasks — prompts only (proprietary)

The original production tasks and **all model responses on those tasks** contain
**proprietary information**. We **do not share full production model responses**.

What we *do* share is a set of **redacted prompts** so readers can see what
*kinds* of tasks were used (code review, architecture, general analysis):

```text
data/production_tasks/tasks/task_XXX.md
data/production_tasks/manifest.json
```

Prompts were processed to remove organization identifiers, PII, product/strategy
labels, agent codenames, cloud project IDs, and secrets. They are illustrative,
not bit-identical to the private corpus.

### GPQA Diamond — full model responses (public track)

Graduate-level multiple-choice questions with known answers (non-proprietary):

- Paper: [Rein et al., GPQA](https://arxiv.org/abs/2311.12022)
- Dataset: [github.com/idavidrein/gpqa](https://github.com/idavidrein/gpqa)
- **Full multi-model responses (198 paper items):** [`data/gpqa_diamond_responses/`](data/gpqa_diamond_responses/)

Standalone, aggregation, and debate outputs for expert and light tracks where recorded.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set INFERENCE_API_URL + INFERENCE_API_KEY

# Dry-run structure (no API calls)
python scripts/run_task.py data/production_tasks/tasks/task_001.md --dry-run

# Live run (requires API)
python scripts/run_task.py data/production_tasks/tasks/task_001.md --tier standalone
```

Environment:

| Variable | Meaning |
|----------|---------|
| `INFERENCE_API_URL` | Base URL for chat/completions-compatible multi-model gateway |
| `INFERENCE_API_KEY` | Bearer token |
| `MMJB_MODELS` | Optional comma-separated model ids (default: config file) |

## Protocol (matches paper)

1. **Standalone** — each expert answers the task alone.  
2. **Aggregation** — each expert receives the panel’s standalone answers and revises.  
3. **Debate** — structured for/against rounds on extracted findings; final votes.  
4. **Scoring (production-style)** — leave-one-out consensus alignment of findings (not independent ground truth). GPQA uses known answers.

## License

MIT (code). Task texts: research use; redistributed only in redacted form as provided.

## Citation

```bibtex
@misc{razumny2026cortical,
  title  = {The Cortical Architecture for Judgment Quality:
            Multi-Agent Consensus and Deliberation},
  author = {Razumny, Igor},
  year   = {2026},
  note   = {Reference implementation and redacted tasks:
            https://github.com/igorrazumny/multi-model-judgment-benchmark}
}
```
