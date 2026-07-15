---
id: task_036
category: code_review
char_count: 9140
redaction: org-names-agents-pii-strategy-labels-removed
---

# Pre-push brainstorm — lock / product-code
Date: 2026-03-28T18:34:45Z
Branch: lock/2026-03-28-req-enforcement
Files: 5 | Diff lines: 276

panel: Qwen3.5 Plus (6.11s), GPT-5.4 (6.45s), Claude Opus 4.6 (23.5s), Grok 4.2 (25.69s), Gemini 3.1 Pro (26.01s)

=== Qwen3.5 Plus (6.11s) ===
[INFO] The diff successfully enforces Ground Rule #3 (Req trailer) and #9 (no auto-bypass of review).
[INFO] Commit logic in `cvc/tools.py` correctly rejects commits missing the `req` parameter before staging.
[INFO] Push logic in `cvc/tools.py` properly escalates to the user after 2 blocked attempts instead of auto-bypassing with `--no-verify`.
[INFO] All existing tests are updated to include the new required `req` parameter, ensuring the test suite remains green.

=== GPT-5.4 (6.45s) ===
[CRITICAL] `cvc/tools.py:_git_push` treats `"API error"` as a review-blocking attempt and increments `_push_attempts` before knowing whether the failure was an actual review finding. A transient panel outage can now consume the 2-attempt budget and force user escalation on the third try, which contradicts the ground rule “If panel is down, wait — no unreviewed code gets pushed.” API outages/timeouts should not count toward the blocked-review limit.

[CRITICAL] The new `req` enforcement only checks non-empty/whitespace in `cvc/tools.py:_git_commit`, but the ground rules require `Req: REQ-XXX` specifically. This allows invalid values like `req="foo"` or `req="123"` to be committed, so the tool-level “structural enforcement” claim is incomplete and agents can still produce non-compliant commits unless a downstream hook catches it.

[CRITICAL] Missing regression tests for the new req behavior in `tests/test_tools.py`: there is no test that `git_commit` refuses missing/blank `req`, and no test that the actual commit message contains the `Req:` trailer. Since this branch’s primary functionality is req enforcement, those tests are required before push.

[WARNING] `cvc/git_ops.py:_format_message` strips existing trailers using case-sensitive `startswith("Req:")` / `Test-Plan:` / etc. A message containing lowercase or whitespace-indented variants (e.g. `req:` or ` Req:`) will survive and produce duplicate/conflicting trailers in the final commit message.

=== Claude Opus 4.6 (23.5s) ===
## Code Review Results

[INFO] `_format_message` adds `Req:` trailer conditionally (`if req:`), but `_git_commit` in `tools.py` already validates that `req` is non-empty before reaching `commit()`. This means the `if req:` guard in `_format_message` is technically dead code in the current call path — the only caller that passes `req=""` would be a direct `CommitManager.commit()` call bypassing the tool layer. Not a bug, but worth noting the implicit coupling. The defensive check in `_format_message` is reasonable for a public method.

[WARNING] `_git_commit` signature has `req: str = ""` (optional default), but the tool definition in `prompts.py` marks `req` as `"required"`. This means the structural enforcement relies on the OpenAI tool schema rejecting calls without `req` AND the runtime validation (`if not req or not req.strip()`). If the LLM somehow sends `req` as an empty string `""`, the runtime catches it — good. However, if `_git_commit` is called programmatically (not through the LLM tool dispatch), the default `""` would silently bypass enforcement until the strip check catches it. The dual enforcement is adequate but the mismatch between the Python signature default and the intended semantics is slightly misleading. Consider removing the default: `req: str` (no default) to make programmatic misuse a TypeError.

[INFO] `_push_attempts` is a class-level annotation (`_push_attempts: int = 0`) that gets set as an instance attribute on first increment. This works fine in Python but is unconventional — consider initializing it in `__init__` alongside other instance state for clarity.

[INFO] The push counter reset (`self._push_attempts = 0`) when escalating is correct — it allows the agent to retry after receiving user guidance. Good design choice.

[INFO] ROADMAP.md section 3.12 is documentation only — no code impact. Content is well-structured.

[INFO] All existing tests updated with `req` parameter. The escalation test (`test_git_push_escalates_after_2_blocks`) correctly verifies the new behavior replaces auto-bypass. Test coverage looks complete for the changes made.

**No test for `req` validation** — there is no test verifying that `_git_commit` refuses a commit when `req=""` or `req="  "` (whitespace-only). This is the core enforcement mechanism of the branch.

[CRITICAL] Missing test for the primary feature: `req` parameter validation. The commit message says "req=' ' no longer bypasses validation (strip check)" but there is no test asserting that `_git_commit(req="")` or `_git_commit(req="   ")` returns the refusal message. Add a test like:
```python
def test_git_commit_refuses_without_req(git_executor):
    result = git_executor.execute("git_commit", {
        "message": "test", "test_plan": "n/a", "files": ["init.py"],
    })
    assert "Commit refused" in result

def test_git_commit_refuses_whitespace_req(git_executor):
    result = git_executor.execute("git_commit", {
        "message": "test", "test_plan": "n/a", "files": ["init.py"], "req": "   ",
    })
    assert "Commit refused" in result
```

**Summary:** One critical finding — the headline feature (req validation) lacks test coverage. Everything else is clean. Fix the missing test, push again.

=== Grok 4.2 (25.69s) ===
**Review Findings**

[CRITICAL] Broken escalation workflow for persistent review blocks. `tools.py:434` resets `_push_attempts` to 0 and returns "Ask the user to approve --no-verify", but `git_push` has no parameter/flag to perform `--no-verify`, `BLOCKED_COMMANDS` explicitly blocks `git push` via `run_command`, and counter reset causes subsequent calls to perform normal push again. This violates ground rule 9 and leaves the agent permanently stuck on unresolvable BLOCK findings. Push must not proceed.

[CRITICAL] Behavioral change to `git_commit`/`git_push` and system prompt without corresponding `docs/REQUIREMENTS.md` update or `Req:` reference. Ground rules §17 and commit trailer rules require every product behavior change (including tool enforcement and workflow) to update requirements + test cases in the same commit. Commits declare "Req-Impact: none" and no requirement was created/updated. This is exactly what the new enforcement is meant to prevent.

[WARNING] `_push_attempts: int = 0` is a class attribute declared mid-class (after `_review_staged_diff`) and mutated via `self._push_attempts`. Multiple `ToolExecutor` instances (or test vs production) will share/mutate the same counter, leading to incorrect escalation behavior.

[INFO] The structural `req` enforcement in `tools.py:290`, `git_ops.py`, updated tool schema, and whitespace check (`not req or not req.strip()`) correctly implements the deterministic layer-1 compliance described in the new ROADMAP 3.12 section. Prompt updates removing auto-bypass and "agent-alpha" references also align with current ground rules.

[INFO] Test updates are comprehensive (removed auto-bypass test, added escalation test, all `git_commit` calls now pass `req`). No obvious regressions in the 301 passing tests.

**Summary:** Push is blocked by the two [CRITICAL] findings. The intent of the change is correct and mostly well-executed, but the bypass path is non-functional and the requirements traceability is missing. Fix the bypass mechanism (add optional `no_verify` param to `git_push` that is only allowed after explicit user confirmation) and address the requirements update before repushing.

=== Gemini 3.1 Pro (26.01s) ===
[CRITICAL] The `git_push` tool instructs the agent to ask the user for `--no-verify` approval, but the tool lacks a parameter to actually execute it. Furthermore, `run_command` explicitly blocks `git push` in `BLOCKED_COMMANDS`. If the user approves the bypass, the agent has no technical means to perform it and will be stuck in a loop. You must add a `no_verify: bool = False` parameter to the `git_push` tool definition in `cvc/prompts.py` and implement it in `cvc/tools.py`.

[INFO] The structural enforcement of the `Req: REQ-XXX` trailer and the removal of the silent auto-bypass are excellent changes. They perfectly align the agent's capabilities with Ground Rules #3 (mandatory traceability) and #9 (user approval required for review bypass).

=== AGGREGATED ===
While one expert praises the new enforcement, others highlight a critical infinite loop: the agent is instructed to ask for `--no-verify` approval but lacks the tool parameter to actually execute it. Reviewers also uniquely note that API timeouts incorrectly consume the push budget, the `req` validation accepts invalid formats like "foo", and the commit hypocritically omits a `REQUIREMENTS.md` update for its own behavioral changes. **Recommendation:** Block the push to add a `no_verify` parameter to `git_push`, exclude API errors from the attempt counter, and add the missing validation tests and requirement documentation.
