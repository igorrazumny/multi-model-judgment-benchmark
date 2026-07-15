---
id: task_016
category: code_review
char_count: 11181
redaction: org-names-agents-pii-strategy-model-ids-removed
---

# Pre-push brainstorm — agent-alpha / service-eval
Date: 2026-03-28T18:23:28Z
Branch: agent-alpha/2026-03-28-ui
Files: 8 | Diff lines: 300

panel: reviewer-model (9.83s), reviewer-model (12.72s), one panel model 4.2 → one panel model 4.1 Fast (5.67s), an LLM (28.2s)

=== reviewer-model (9.83s) ===
[WARNING] `queries_raw.py:180` — Division by zero risk if `fp_total` is 0 and `found_all` is 0; current logic returns `None`, but the condition `if fp_total > 0` prevents the division, so it's safe. However, the fallback `999.0` for `found_all > 0` with `fp_total == 0` is correct per requirements. No bug, but worth noting the logic is slightly complex; consider a comment explaining the `999.0` sentinel value represents "perfect reliability" to aid future maintainers.

[INFO] `Overview.jsx:56` — Sorting logic for `fp_ratio` uses `?? -1` as fallback for `null`. This places models with no FP data (null) at the bottom when sorting ascending, which is reasonable. Ensure this aligns with user expectation: models with undefined reliability should sort lower than those with measured low ratios.

[INFO] `App.css:54-56` — Use of `!important` on `text-transform` and `letter-spacing` is justified here to override inherited styles from `th` elements (which have `text-transform: uppercase`). This is a targeted fix for REQ-WEB-204 and acceptable given the specificity conflict.

[INFO] Commit `c74f129` references three requirements (REQ-WEB-200/204/205) in one commit. While allowed, splitting UI column changes (200), tooltip fixes (204), and filtering logic (205) into separate commits would improve traceability and rollback granularity if needed. Not a block, but a suggestion for future work.

=== reviewer-model (12.72s) ===
[CRITICAL] Missing executable tests for code changes in this branch. Both commits use `Test-Skip` for UI/code changes without evidence that tests were impossible, and the added YAML files are manual test-case docs only, not automated or run tests. Per ground rules, code changes should have written/run tests when feasible; push should not proceed without at least backend coverage for `get_raw_stats()` FP ratio + hidden model behavior and frontend coverage for the new column/rendering/sort behavior.

[WARNING] `src/web/api/queries_raw.py:118-124` counts false positives from all participated `model_responses`, but `model_found_all` only counts findings attached via `model_findings`. If `false_positive_count` is populated for participated responses that produced no confirmed findings, `fp_ratio` becomes `0 / fp_total = 0`, which may be intended; however models with no participated findings history but stale/partial FP data will render as `0.00` instead of dash, conflating “no successful findings” with “data unavailable.” Consider basing the nullability on participation/data presence explicitly.

[WARNING] `src/web/ui/src/pages/Overview.jsx:62-66` sorts `fp_ratio` nulls as `-1`, which pushes “no data” rows to the top when sorting ascending. That’s likely a confusing UX regression for the new column because dash/no-data entries sort ahead of legitimate low ratios. Use a sentinel that keeps nulls last in both directions or a comparator that handles null explicitly.

[INFO] `src/web/ui/src/App.css:54` uses `word-wrap: break-word;`; modern CSS prefers `overflow-wrap: break-word;` for consistent wrapping behavior. If the tooltip caps issue was inheritance-related, you may also need to inspect the tooltip wrapper/content in DevTools because `text-transform` on descendants is already overridden here and the requirement notes the fix is “deployed but not working.”

[INFO] `src/web/api/queries_raw.py:191-193` hardcodes `HIDDEN_MODELS = {"glm_5"}` in application code. It satisfies the current requirement, but if this is expected to change by user decision later, moving it to config/DB would avoid another code deploy for a purely display-policy change.

=== one panel model 4.2 → one panel model 4.1 Fast (5.67s) ===
**[INFO] docs/REQUIREMENTS.md:17**
REQ-WEB-200 status remains "in-progress" despite implementation of all listed columns, a fallback model filter, tooltip fixes, and FP Ratio. Should be updated to "implemented".

**[INFO] docs/REQUIREMENTS.md:39**
REQ-WEB-204 status remains "in-progress (fix deployed but not working — caps lock persists)" but this commit implements the `!important` CSS fix and updates tooltip text. Status should be updated to "implemented".

**[INFO] docs/REQUIREMENTS.md:52**
REQ-WEB-205 status remains "in-progress" despite successful implementation of `HIDDEN_MODELS = {"glm_5"}` filter. Should be updated to "implemented".

**[WARNING] src/web/api/queries_raw.py:177**
Division by zero protection is incomplete. The FP ratio calculation `round(found_all / fp_total, 2)` occurs before the `if fp_total > 0` check in the ternary. While the current expression avoids runtime error due to short-circuiting, the logic is fragile. The commit message claims "fix: FP ratio edge case" but the previous commit already introduced this exact logic.

**[CRITICAL] src/web/api/queries_raw.py:166**
`fp_total = model_fp.get(mid, 0)` is used but `model_fp` only includes models where `participated = TRUE`. Models with no `model_responses` rows will have fp_total=0, triggering the 999.0 special case. However, the test case (TC-REQ-WEB-200-02) expects "Models with no data show dash" — this code shows 999.0 instead. This directly contradicts the documented expected behavior added in this branch.

**[BLOCK] src/web/api/queries_raw.py:172**
`fp_ratio` is always calculated using `found_all / fp_total` (global totals), but all other percentages (`all_pct`, category pcts) correctly use `eligible` (participated-runs only). This is inconsistent with REQ-BENCH-300 and creates misleading ratios for models with partial participation. The FP ratio should be calculated against findings from participated runs only.

**[WARNING] src/web/ui/src/pages/Overview.jsx:60**
`getSortVal` returns `m.fp_ratio ?? -1` for FP Ratio column. This places models with `null` (no data) at the top when sorting ascending, which is likely incorrect UX. Should treat nulls as lowest reliability or use a sentinel that sorts them last.

**[INFO] src/web/ui/src/pages/Overview.jsx:200**
"How to read" section still references old column names and missing categories in some places (e.g. no Non-Critical description) even though the diff attempts to clean this up. Some stale text remains.

**[INFO] Test coverage**
New test cases added for REQ-WEB-200 and REQ-WEB-204, but no unit tests for the new FP ratio calculation logic in `queries_raw.py`, particularly the edge case of FP=0. "Test-Skip: UI verified after deploy" is acceptable per ground rules only because it is UI-only and has explicit user confirmation.

**[PRE-EXISTING] src/web/api/queries_raw.py:118**
The solo calculation query still uses global `total_findings` denominator, which is correct per REQ-BENCH-301, but the comment says "Solo discoveries" while column is now "Unique". Minor.

**Summary:** Two [BLOCK]/[CRITICAL] issues must be fixed before push: inconsistent FP ratio denominator (should respect participation like other metrics) and mismatch between FP=0 behavior (999.0) vs test case expectation ("dash"). Requirements status updates also needed.

=== an LLM (28.2s) ===
## Code Review: `agent-alpha/2026-03-28` — FP Ratio, Columns, a fallback model Hidden

---

[WARNING] `src/web/ui/src/pages/Overview.jsx:8-9` — `unique_insight` still in `CAT_LABELS` and `CAT_HEADER_TIPS` but the "How to read" section (line 194) no longer handles `c.key === "unique_insight"`. If the API still returns a `unique_insight` category, the column renders but the "How to read" `<dd>` will be empty. Not a crash, but visually broken for that entry. If the category was removed from the DB, this is dead code that should be cleaned up.

[WARNING] `src/web/api/queries_raw.py:180` — `fp_ratio` uses `found_all` (confirmed findings the model identified) as numerator, but `found_all` comes from `model_findings` which tracks attributed findings — not total *claimed* findings. REQ-WEB-200 says "confirmed findings / false positives" which matches, but REQ-PIPE-007 says "FP% = rejected_findings / total_claimed_findings". The ratio semantics are inconsistent between requirements. The implementation gives `found_confirmed / false_positives` which is a useful signal-to-noise ratio, but doesn't match REQ-PIPE-007's definition. Confirm this is the intended metric.

[WARNING] `src/web/api/queries_raw.py:180` — The magic value `999.0` for zero-FP models is exposed to the frontend and rendered directly via `.toFixed(2)` as "999.00" in the table. This is a user-facing display concern — a model with zero false positives shows "999.00" which is confusing without explanation. The tooltip says "Above 1.0 = reliable" but doesn't explain 999. Consider either capping display (e.g., "∞" or "—" with a different tooltip) or documenting this in REQ-WEB-200 test cases. The test case TC-REQ-WEB-200-02 says "Zero FP models show high value (reliable)" which is vague.

[INFO] `src/web/api/queries_raw.py:188-189` — `HIDDEN_MODELS` is hardcoded as a set in the query function. This works for now but per REQ-WEB-205 "re-introduction requires user decision" — consider making this configurable (env var or DB flag on the `models` table) rather than a code change for each model hide/show. Not blocking; the current approach is simple and correct.

[INFO] `src/web/ui/src/pages/Overview.jsx:42` — `CELL_TIPS` still contains `unique_insight` key. Dead code if the category is removed. Minor cleanup.

[INFO] `src/web/api/queries_raw.py:122` — The FP query sums across all participated responses. If a model has 0 rows in `model_responses` (new model, never ran), it won't appear in `model_fp` dict, and `model_fp.get(mid, 0)` returns 0 — which is correct. Good default handling.

[INFO] Commit trailers: Both commits have `Req: REQ-WEB-200`, `Test-Skip` with user confirmation, and `Agent: agent-alpha`. The `Test-Skip` for `.py` code changes is acceptable given the stated UI verification. Second commit covers REQ-WEB-204 and REQ-WEB-205 but only references `Req: REQ-WEB-200` — minor trailer gap, not blocking.

---

**Summary:** No BLOCK/CRITICAL findings. Three warnings — the most substantive is the `999.00` magic value displayed to end users, which will confuse anyone reading the table. The other two are about dead code paths and requirement definition consistency. Clean implementation overall; FP query, a fallback model filtering, and column additions are correct.

=== AGGREGATED ===
Experts clash over the `999.0` FP ratio fallback: one defends it, another flags it as confusing UX, and a third elevates it to a CRITICAL violation of your new test case which explicitly expects a dash. Additionally, reviewers uniquely highlight a BLOCK-level math error where the FP ratio uses global totals instead of participated runs, alongside a sorting bug where `null ?? -1` incorrectly pushes no-data rows to the top. **Recommendation:** Block the push to fix the FP ratio denominator to use participated runs, replace the `999.0` magic number with `null` to render the expected dash, and adjust the sorting sentinel to handle nulls gracefully.
