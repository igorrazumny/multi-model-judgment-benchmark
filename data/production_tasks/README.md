# Production tasks (redacted)

These are **production-style evaluation prompts** used in multi-model judgment
quality experiments (code review, architecture, general analysis).

## Processing

Tasks were processed so that:

- Organization brands and product names are generalized  
- Internal agent codenames are replaced with `agent-alpha` / …  
- Internal repository names map to `service-*`  
- Emails, API keys, and cloud project IDs are removed  
- Strategy / roadmap phrasing is generalized  

The goal is that nothing here is easily associateable with a specific company
or private product roadmap, while remaining useful as realistic tasks.

**This corpus is not bit-identical to the private evaluation set.**

## Layout

| File | Role |
|------|------|
| `manifest.json` | Task list, categories, redaction policy |
| `tasks/task_XXX.md` | One task prompt per file |
| `OWNER_RECONCILIATION.json` | Owner-only private ID map (optional; ignore for reuse) |

## Categories

- `code_review` — diffs / implementation review  
- `architecture` — design decisions  
- `general_analysis` — analysis / process / strategy-shaped prompts (generalized)  

## License / use

Research and evaluation use. Do not treat redacted text as ground-truth labels
about any real organization.
