---
id: task_023
category: architecture
char_count: 2224
redaction: org-names-agents-pii-strategy-model-ids-removed
---

# service-eval Prompt: Configurable service-eval data collection via voice transcription

## User Request
Design a configurable system for collecting service-eval data points from voice transcriptions. The [service-eval] instruction appended to transcriptions works for some agents but not all (~30-50% compliance). Make it configurable via a JSON config file so the prompt text and on/off toggle can be changed without code changes. Also update the prompt wording to be transparent (no "silently", no "do not mention") — the user wants to see the agent saving the data point.

## Context
- panel CLI voice transcription appends a [service-eval] instruction to clipboard text
- agent-zeta implemented it in native panel-voice app (commit ae9663f) and bash fallback
- Some agents (agent-eta) execute it and save context-rich service-eval prompt files
- Some agents (agent-sigma, agent-alpha) ignored it — one panel model Code prompt injection detection triggered by "save silently" / "do not mention"
- User decided to KEEP the appendix (partial data is better than none) but make it configurable
- Config should control: (1) enabled/disabled toggle, (2) the full prompt text
- The prompt text should be transparent: "User requested this. User will see you doing it. Create the file."
- Files go to ~/workspace/agent-alpha/service-eval/data/service-eval-inbox/
- agent-zeta owns the panel CLI implementation

## Technical Details
- panel CLI: /Users/igorrazumny/PycharmProjects/cli/scripts/panel
- Native voice app: implemented by agent-zeta, separate binary
- Current appendix location in bash: transcribe_and_paste() function, line ~144
- Config file location TBD: likely ~/.panel/service-eval.json or similar
- service-eval-inbox and service-eval-processed dirs are gitignored in service-eval repo

## Related Decisions
- Merged PRs are the primary data source for code review benchmarking (agent-gamma extracting 36 PRs)
- Voice transcription data points are supplementary — different types (business, architecture, code creation)
- Future: categorize data points by type, separate inbox folders per type
- Pipeline processes inbox files → sends to 7-9 models → meta-eval → results to Cloud SQL → service-eval.product.example.com
