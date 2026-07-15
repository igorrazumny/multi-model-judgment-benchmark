---
id: task_024
category: code_review
char_count: 14550
redaction: org-names-agents-pii-strategy-model-ids-removed
---

# Pre-push brainstorm — agent-sigma / service-web
Date: 2026-03-29T08:17:45Z
Branch: agent-sigma/2026-03-29-save-fix
Files: 1 | Diff lines: 28

panel: reviewer-model (5.55s), reviewer-model (14.26s), reviewer-model (20.18s), llm (23.19s), reviewer-model (66.39s), reviewer-model (70.24s)

=== reviewer-model (5.55s) ===
[CRITICAL] dashboard/app.jsx:1109-1118 catches **all** `createWritable()` failures and treats them as a stale handle. That changes required behavior for ordinary write errors (permission denied, OS/file lock, quota, disk full, transient I/O failure): instead of surfacing “Save failed”, the app now clears the existing handle and prompts Save As, which can mislead the user and break REQ-418’s “Save writes back to the exact same file silently.” Only stale-handle / permission-revoked cases should fall through; other errors must still be reported.

[CRITICAL] Missing automated test coverage for this code-path change. Ground rules explicitly say manual-only testing is not acceptable for feasible code changes, and REQ-418 is marked testable/E2E. This diff changes save error-handling logic and needs at least a unit/integration test covering: valid handle saves silently, stale handle falls through to `showSaveFilePicker`, and non-stale write errors do not trigger Save As.

=== reviewer-model (14.26s) ===
**Review of db1a36c**

**[CRITICAL]** `dashboard/app.jsx:1130` Broad `catch {}` swallows all errors, not just stale handles.  
`createWritable()`/`write()` can fail for legitimate reasons (disk full, permission revoked for other reasons, quota exceeded, etc.). These are now silently treated as "stale" and turned into a Save As flow. This violates the outer error handling that was previously showing `setError()` and can cause data loss or user confusion.

**[CRITICAL]** Missing requirement and test case updates.  
REQ-418 does not mention stale handle behavior. Per ground rules §17, any behavioral change (even a bug fix that alters observable outcome from "silent failure" to "show picker") must update `docs/REQUIREMENTS.md` *and* the corresponding test case in the same commit. This commit does neither.

**[WARNING]** `setFileHandle(null)` is called from within the async `handleSave` handler without checking error type. Combined with the broad catch, this can clear a valid handle on transient errors.

**[INFO]** Consider specific error checking per the File System Access API spec:

```js
} catch (err) {
  if (err.name === 'NotAllowedError' || err.name === 'InvalidStateError') {
    setFileHandle(null);
  } else {
    throw err; // let outer catch show the real error
  }
}
```

**[INFO]** The `return;` after successful write is correct and necessary.

The functional intent of the fix is sound (stale handles after reload are a real and well-known limitation of the File System Access API), but the implementation is too aggressive in its error handling and violates the mandatory requirements/test-case update rule.

**Push blocked.** Fix the broad catch and update the requirement + test case before pushing again.

=== reviewer-model (20.18s) ===
[BLOCK] Missing automated tests for P0 file save functionality — Test-Plan states "manual" but no user confirmation for Test-Skip shown. Per Ground Rule #3, Test-Skip requires explicit human confirmation for code files. File save is testable via E2E (mock File System Access API or puppeteer). This is a P0 requirement (REQ-418) with data loss implications if save fails silently. Automated regression tests are feasible and expected.

[WARNING] Bare `catch {}` swallows all errors, not just stale handle errors — If `createWritable()` throws for other reasons (quota exceeded, permission denied, file locked), the code will incorrectly fall through to Save As, potentially confusing users. Should catch specific error types or check `error.name` (e.g., `NotFoundError` indicates stale handle per File System Access API spec).

[INFO] Consider adding user feedback when handle goes stale — Currently `setFileHandle(null)` happens silently, then Save As picker opens. User may not understand why they're being asked for a new location. A brief toast/notification explaining "File handle expired, please choose save location" would improve UX.

[INFO] Commit trailers present and valid — Test-Plan, Agent (agent-sigma), and Req (REQ-418) all included. Requirement alignment looks correct: the stale handle fix is an implementation detail necessary for REQ-418's "Save writes back to the exact same file" behavior to work reliably across page reloads.

[INFO] Blast radius acceptable — 1 file, 28 lines changed. File size (1409 lines) under 1500 limit. No dependency changes, no secrets, no config modifications.

=== llm (23.19s) ===
## Review: Stale file handle fallthrough to Save As

### Diff Analysis

The change is minimal and well-scoped: wraps the existing `fileHandle.createWritable()` call in a try/catch, clears the handle on failure, and restructures the control flow so it falls through to the Save As picker. This directly implements the bug fix described in the commit message.

### Requirement Alignment (REQ-418)

REQ-418 specifies: "Save writes back to the exact same file (same path, same name). When no file imported, button shows 'Save As' and opens save picker. Fallback to browser download if API unavailable."

The diff correctly handles a gap in the original implementation: stale handles after page reload. The `return` after successful save, the `setFileHandle(null)` on catch, and the restructured `if` to fall through to `showSaveFilePicker` all align with the requirement. No unrequested behavior is added.

### Findings

[WARNING] `dashboard/app.jsx:1114` — The bare `catch` catches **all** errors from `createWritable()`, `write()`, and `close()`, not just stale-handle errors (e.g., `DOMException` with `NotAllowedError` name). If `createWritable()` succeeds but `write()` fails mid-stream (disk full, permissions revoked), the writable stream is left open/leaked, and the user is silently redirected to Save As — potentially saving to a different file without understanding why the original save failed. Consider: (1) catching only on `createWritable()` rather than wrapping all three calls, or (2) checking `e.name === 'NotAllowedError'` to distinguish stale handles from write failures. That said, this is an improvement over the previous behavior (silent failure with no fallback), so it doesn't warrant blocking.

[INFO] The button label still shows "Save" when `fileHandle` is set, but after a stale-handle catch, the user sees a Save As picker without the label updating first. This is a minor UX inconsistency — `setFileHandle(null)` triggers a re-render, but the picker opens before the re-render completes. Not a bug, just worth noting.

[CRITICAL] `Test-Plan: manual` — Ground Rule #2 states Test-Skip requires explicit human confirmation for code files, and Test-Skip is a last resort. The commit has `Test-Plan: manual` rather than `Test-Skip`, which technically satisfies the trailer requirement, but there are no automated tests for this save behavior. The File System Access API is browser-only and hard to mock, but the control flow restructuring (stale handle → clear → fall through) is testable with a mock `fileHandle` that throws on `createWritable()`. Given this is a P0 feature (REQ-418) with a behavioral change, a unit test verifying the fallthrough logic should exist.

### Summary

The code change itself is correct and well-scoped. The one blocking issue is the missing test coverage for a P0 behavioral change — the stale-handle-to-Save-As fallthrough is straightforward to test with a mock file handle. Add a test that verifies: (1) when `fileHandle.createWritable()` throws, `setFileHandle` is called with `null`, and (2) the code proceeds to the `showSaveFilePicker` branch.

=== reviewer-model (66.39s) ===
 [CRITICAL] Unconditional error catch violates REQ-418 scope: The bare `catch` block catches **all** errors (permissions denied, disk full, file locked), not just stale handles. This triggers Save As flow for errors that should surface to the user as failures, violating REQ-418's "Save writes back to the exact same file silently" behavior. The requirement distinguishes Save (silent) from Save As (picker); conflating them on arbitrary errors is unrequested behavior change (Ground Rules: "building things nobody asked for").

[CRITICAL] Destructive state mutation on transient errors: `setFileHandle(null)` clears the persistent handle on **any** write failure, including potentially transient ones (network timeout, temporary file lock). This forces users to re-select files they already imported, losing the "persistent file handle" UX guarantee of REQ-418. State should only be cleared upon confirmed stale handle or explicit user action.

[WARNING] Test-Plan: manual lacks justification for P0 feature: While File System Access API testing requires browser infrastructure, the diff introduces new control flow logic (try/catch fallthrough) that is testable via mocked handles. Ground Rules require Test-Skip rationale for unfeasible tests; manual-only testing for P0 requires explicit confirmation of infrastructure limitations.

[WARNING] Silent error swallowing prevents debugging: The inner catch block discards the error object without logging (`catch { ... }`), making it impossible to diagnose why saves failed in production logs. At minimum, log `console.warn('[Save] Handle stale or error:', e)` before falling through.

[INFO] Consider discriminating stale handle errors: The File System Access API typically throws `NotFoundError` or `InvalidStateError` for stale handles after reload. Checking `e.name === 'NotFoundError'` before falling through would allow legitimate write errors to surface correctly while handling the specific stale case.

=== reviewer-model (70.24s) ===
[CRITICAL] Missing test case update. Per Rule #17, every commit that changes product behavior must update the corresponding test cases in the same commit. You added a new fallback behavior for stale file handles (falling back to Save As), which is a testable edge case, but `docs/test-cases/REQ-418.yaml` was not updated in this diff.

[INFO] The commit message states "File System Access API handles go stale after page reload." However, `fileHandle` is stored in standard React state (`useState`), which is cleared entirely on a page reload anyway (it becomes `null`). The stale handle issue you fixed was likely caused by the browser revoking permissions after idle time, or the file being modified/deleted externally, rather than a page reload. The fix itself is correct and robust.

[INFO] By using a generic `catch { ... }` block, you are also catching `AbortError` if the user explicitly denies the browser's permission prompt for `createWritable()`. This means denying permission will immediately pop up the "Save As" picker. This is acceptable fallback UX, but you could specifically check the error name if you wanted to avoid the double-prompt on cancellation.

=== AGGREGATED ===
As your moderator, I have synthesized the reviews from the six models. There is a strong consensus that while the intent of the fix is correct, the implementation is currently unsafe for production.

### Summary of Expert Perspectives

*   **The "Broad Catch" Consensus:** Every model identified the `catch {}` block as a critical flaw. By failing to discriminate between a "stale handle" (which justifies a fallback to Save As) and "transient/fatal write errors" (like disk full, permission denied, or quota exceeded), the code risks masking genuine system failures and forcing unnecessary "Save As" prompts on the user.
*   **The Testing Disagreement:** There is a nuanced disagreement regarding the "Manual" test plan. While some models (e.g., `panel-model`, `panel-model`) argue that the logic is testable via mocks and therefore requires automated tests, others focus on the procedural violation of Ground Rule #17 (updating `REQUIREMENTS.md` or test documentation).
*   **Unique Insights:**
    *   `panel-model` provides a valuable technical correction: the "stale handle" is likely due to permission revocation or external file modification, not page reloads (as React state is wiped on reload).
    *   `reviewer-model` highlights a "destructive state mutation" concern: clearing the handle on *any* error is a poor UX pattern that forces users to re-import files unnecessarily.
    *   `reviewer-model provides a concrete code snippet for error discrimination, which is the recommended path forward.

---

### Consolidated Review Findings

**[BLOCK]** The `catch` block is too broad. It treats all write errors (disk full, permission denied, etc.) as stale handles. This violates REQ-418 by triggering a "Save As" flow when the system should instead report a save failure. You must inspect the error name (e.g., `NotFoundError`, `NotAllowedError`) before clearing the handle.

**[BLOCK]** Missing automated test coverage. As this is a P0 feature (REQ-418) and you are introducing new control-flow logic, a manual test plan is insufficient. You must provide a unit or integration test that mocks the `fileHandle` to verify that the fallback logic triggers only on expected stale-handle errors.

**[CRITICAL]** Violation of Ground Rule #17. Any change to product behavior (the new fallback mechanism) requires an update to the corresponding test documentation (`docs/test-cases/REQ-418.yaml` or equivalent).

**[WARNING]** Destructive state mutation. `setFileHandle(null)` is called indiscriminately. If a transient error occurs (e.g., temporary file lock), the user loses their persistent handle, forcing them to re-import the file. Only clear the handle if the error is definitively related to handle staleness.

**[INFO]** Consider adding a `console.warn` or user-facing toast notification when a handle is cleared. Silently falling back to "Save As" without explanation may confuse users who expect their original file to be updated.

---

### Moderator Recommendation
**Do not push.** 
1.  **Refactor the `catch` block:** Implement specific error checking to ensure only stale handles trigger the `setFileHandle(null)` and fallback flow.
2.  **Add a test:** Create a mock-based test case that verifies the specific error-to-fallback path.
3.  **Update Documentation:** Ensure `docs/REQUIREMENTS.md` or the relevant test suite reflects this new error-handling behavior.
