---
id: task_029
category: code_review
char_count: 1304
redaction: org-names-agents-pii-strategy-model-ids-removed
---

---
type: bug_fix
agent: agent-sigma
repo: service-web
timestamp: 2026-03-28T16:30:00
context: Stale runStatus from previous run showing old results on new steps
---

## User Request

After hard refresh (v2026.03.28.7), step 2 shows "running..." but step 3 already shows PASS. Steps still appear out of order. Backend logs confirm sequential execution (STEP 1 DONE → STEP 2 START), so the issue is in the UI.

## Root Cause

`handleScriptExecute` sets `steps` (which renders UnifiedStepView) but does NOT clear `runStatus`. The previous run's `runStatus` (with 17 completed results) was still in React state. The UI's `getStepResult(i)` matched old results by array index to new steps:
- `results[0]` (old step 1 PASS) → new step 1: shows PASS
- `results[2]` (old step 3 PASS) → new step 3: shows PASS
- Step 2 shows "running..." because it's the current step from the NEW run's polling

## Fix

Added `setRunId(null)` and `setRunStatus(null)` at the start of both `handleScriptExecute` and `handleExecute`, before starting the new run. This clears all previous results.

## Context
- File: dashboard/app.jsx
- `handleScriptExecute` (line 169) — called from ScriptEditorPanel Execute button
- `handleExecute` (line 197) — called from UnifiedStepView Execute button
- Both now reset state before starting
