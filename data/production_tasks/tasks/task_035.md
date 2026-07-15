---
id: task_035
category: code_review
char_count: 927
redaction: org-names-agents-pii-strategy-labels-removed
---

# service-eval Prompt: Remove unique_insight category + fix tooltip styling

## User Request
1. Remove "unique_insight" from DB — we already have Solo, don't need another similar column
2. Fix tooltip: text is all caps and doesn't fit width — should be normal case, multi-line if needed
3. Going forward: every change requires written requirement → user confirmation → implementation → PR review → merge

## Context
- finding_categories table in Cloud SQL has: critical, non_critical, perspective, unique_insight
- unique_insight was added during initial setup (only 8 findings, too small sample, 100% values nonsensical)
- Tooltips use CSS class .tip-box with max-width: 300px but text-transform may be inherited from th
- Column headers use text-transform: uppercase (CSS .data-table th) — tooltips inside th inherit this
- The approved columns are: Model, Type, Sample, All, Critical, Non-Critical, Perspectives, Solo, Time
