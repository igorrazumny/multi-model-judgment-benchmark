# Evaluation protocol (reference)

Aligned with the paper’s methodology at a conceptual level.

## Tiers

| Tier | Inputs | Output |
|------|--------|--------|
| Standalone | Task only | Per-model findings / answer |
| Aggregation | Task + panel standalone answers | Per-model consolidated assessment |
| Debate | Candidate findings + for/against + votes | Confirmed findings by threshold |

## Production scoring (construct)

Open-ended production tasks have no single ground truth. The production
benchmark uses **leave-one-out consensus alignment** of findings. That metric
includes a convergence component and is **not** independent ground-truth
accuracy. Report it as such.

## GPQA scoring

Use the official GPQA Diamond correct answers. Do not mix expert-only
aggregation with mixed expert+light debate context without labeling both.

## Redacted tasks

See `data/production_tasks/README.md`. Tasks are generalized to remove
sensitive organization and strategy content.
