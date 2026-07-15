---
id: task_047
category: code_review
char_count: 1865
redaction: org-names-agents-pii-strategy-model-ids-removed
---

# service-eval Prompt: Force Fresh File Read in one panel model Code

## User Request
"But then if it's cached, then maybe I can say, okay, read without caching or something like that. Or read the full file kind of like, what would trigger you to read the full file? And not cached but like the real one."

## Context
An agent (agent-eta) was asked to check its inbox (CC = Check Chat + Inbox). The inbox file (`~/workspace/agent-eta/INBOX.md`) contained 3 messages confirmed written by assign.sh. But when the agent read it via CC, it reported "Inbox: Empty." On a subsequent check, it found the messages.

The issue: one panel model Code's Read tool may return stale results if the file was previously read in the same conversation and was empty at that time. The model might recall the previous empty result instead of actually invoking the Read tool again.

## Current CC Rule (GROUND_RULES rule #16)
```
16. **User Shortcut — CC:** When the user types **CC**, it means **Check Chat + Inbox**. Read `~/workspace/.chat.md` AND `~/workspace/{agent}/INBOX.md`, summarize what's new, and act on anything relevant.
```

## Current INBOX workflow
- Messages written via `process-hooks/core/scripts/assign.sh`
- Pre-commit hook displays inbox contents (fresh shell `cat` every time — reliable)
- CC shortcut triggers one panel model Code Read tool (may use cached/recalled result — unreliable)

## Question for service-eval
How should the CC instruction be modified to ensure one panel model Code always performs a fresh file read of the inbox, not relying on previously cached or recalled content? Options considered:
1. Add "MUST use Read tool, do not rely on memory" to the CC rule
2. Use Bash `cat` instead of Read tool for inbox checks
3. Add explicit instruction like "the file may have changed since last read, always re-read"
4. Other approaches to force fresh reads in one panel model Code conversations
