---
id: task_019
category: architecture
char_count: 1212
redaction: org-names-agents-pii-strategy-labels-removed
---

# service-eval: Session Continuity — Handover Reliability

## User Concern
"I already had situation when we restart and then the new reincarnation is saying like, no, there's no history. I have no idea what you're talking about."

## Context
The user has experienced sessions where the handover/memory written by the previous session was not found or not read by the next session. This breaks continuity and forces the user to re-explain everything.

## Current Memory Architecture
- Memory files: `~/.claude/projects/-Users-igorrazumny/memory/`
- MEMORY.md is the index — loaded into every conversation automatically (first 200 lines)
- Individual memory files are referenced from MEMORY.md
- Handover file: `handover_oracle_session_2026-03-28.md` (just written)
- MEMORY.md updated with pointer to handover

## The Risk
If MEMORY.md exceeds 200 lines, the pointer to the handover might be truncated. If the new session doesn't read the handover file, all context is lost.

## Verification Needed
1. Is the handover pointer within the first 200 lines of MEMORY.md?
2. Will the next session actually load and read the handover?
3. Is there a more reliable mechanism than hoping the model reads referenced files?
