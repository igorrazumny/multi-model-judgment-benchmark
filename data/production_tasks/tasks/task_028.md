---
id: task_028
category: code_review
char_count: 1454
redaction: org-names-agents-pii-strategy-labels-removed
---

# service-eval Prompt: Consensus validation for findings — majority vote before counting

## User Request
Current meta-eval just accepts whatever findings models claim. But models frequently claim false positives. Before counting a finding, it needs majority vote (>50% of models agree it's valid). Also add a "False Positives" column showing what percentage of a model's claimed findings were rejected by consensus.

## Proposed Pipeline Change
Current: models respond → meta-eval extracts findings → attribute to models → count
Proposed: models respond → meta-eval extracts ALL claimed findings → send each finding back to ALL models for validation vote → only findings with >50% agreement are "confirmed" → confirmed findings get attributed → count percentages from confirmed only → also track false positive rate per model

## New Column: False Positives %
Shows what percentage of a model's total claimed findings were rejected by consensus. High false positive rate = model is noisy/hallucinating. This is shown FIRST in the table (before All) as a negative signal users should see immediately.

## Context
- Agents frequently claim false positives in code reviews (user direct experience)
- Solo discoveries especially suspect — if only one model found it, is it real or hallucination?
- Majority vote adds one more API call round but improves data quality
- Changes meaning of all existing percentages — would need to re-evaluate historical data
