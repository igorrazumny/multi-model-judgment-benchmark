# Production tasks — redacted prompts only

## Why prompts only

Production evaluation used **real proprietary work** (internal code reviews,
architecture decisions, product-adjacent analysis). Both the raw tasks and the
**full multi-model responses** on those tasks contain proprietary information.

We therefore:

- **Share only redacted prompts** — so readers can see the *kind* of tasks used  
- **Do not share full production model responses** — they would re-expose proprietary content  

For a complete response dump on a **public** benchmark, see
`../gpqa_diamond_responses/` (GPQA Diamond).

## Processing

Prompts were processed so that:

- Organization brands and product names are generalized  
- Internal agent codenames are replaced with `agent-alpha` / …  
- Internal repository names map to `service-*`  
- Emails, API keys, and cloud project IDs are removed  
- Strategy / roadmap phrasing is generalized  
- **Specific model / vendor names are removed** — code-under-review is labeled
  **LLM-generated** (not “Claude Opus …” / “GPT …”); panel reviewers are
  generic “panel models,” not named products  

**Illustrative only** — not bit-identical to the private evaluation set.

## Layout

| File | Role |
|------|------|
| `manifest.json` | Task list, categories, redaction policy |
| `tasks/task_XXX.md` | One **prompt** per file (no model responses) |
| `OWNER_RECONCILIATION.json` | Owner-only private ID map (optional; ignore for reuse) |

## Categories

- `code_review` — diffs / implementation review  
- `architecture` — design decisions  
- `general_analysis` — analysis / process / strategy-shaped prompts (generalized)  

## License / use

Research use. Do not treat redacted text as factual claims about any real organization.
