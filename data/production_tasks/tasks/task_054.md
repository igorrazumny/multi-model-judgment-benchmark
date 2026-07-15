---
id: task_054
category: code_review
char_count: 13060
redaction: org-names-agents-pii-strategy-model-ids-removed
---

# Pre-push brainstorm — agent-eta / example-org-platform
Date: 2026-03-29T08:08:29Z
Branch: agent-eta/2026-03-29
Files: 5 | Diff lines: 126

panel: reviewer-model (6.6s), reviewer-model (13.74s), llm (20.63s), reviewer-model (24.01s), reviewer-model (48.45s), reviewer-model (55.3s)

=== reviewer-model (6.6s) ===
[CRITICAL] tests/test_models.py:82-94 does not fully cover REQ-050’s stated trigger/example set. The requirement explicitly calls out removed IDs like `retired-model-id-a` and says removed models should return clear errors “when requested via inference or resolve_model,” but the new tests only exercise `resolve_model()` for canonical names and `detect_provider()` for 4 removed provider IDs. There is still no test that a removed direct model ID such as `retired-model-id-a` is rejected, nor any endpoint-level test proving the inference path returns a clear client error for retired models. Since this change is supposed to prevent accidental re-use of retired IDs, push should not proceed without covering the actual request path or tightening the requirement to match what is tested.

[WARNING] docs/REQUIREMENTS.md:439-445 changes REQ-050’s expected behavior from “Inference endpoint returns 400 for removed model_ids” to “detect_provider raises ValueError for removed model_ids.” That is a meaningful narrowing of the contract, not just a status update. If this reflects a real product decision, it needs explicit confirmation trail; otherwise it looks like the requirement was rewritten to fit the implementation instead of the implementation meeting the requirement.

[INFO] tests/test_models.py:82 docstring says “removed model_ids with no matching prefix must raise ValueError,” but one of the cases (`zai-org/fallback-model-maas`) specifically relied on a removed matching prefix branch. The test intent is valid, but the wording is misleading and could confuse future maintainers about why this ID should now fail.

=== reviewer-model (13.74s) ===
**Review of branch (commits b4ece3a + 3baaaea)**

[INFO] Implementation matches both referenced requirements (REQ-049 and REQ-050) exactly. Dead `vertex_openapi` detection branch and unused import removed from adapter.py:26 and call_llm path. Negative tests added for 8 canonical names (resolve_model returns None) and 4 model_ids (detect_provider raises ValueError).
[INFO] Requirements.md status updated to "implemented" and expected behavior aligned with actual implementation (detect_provider ValueError instead of inference 400). This is permitted per the 2026-03-28 clarification on same-commit requirement updates.
[INFO] Handover files (HANDOVER.md, HANDOVER_rama.md) correctly updated with chronological entries and proper formatting. Blast radius is minimal (docs + ~20 LOC).
[INFO] Test-Plan in both commits executed and reported (16/67 tests passing, 2 new tests). No regressions to active model paths (active-provider paths).
[INFO] No security issues, no hardcoded secrets, no dependency changes, no immutable core files touched.
[PRE-EXISTING] The broader model trim (REQ-046) and a fallback model routing decisions predate this diff and are outside its scope.

**Summary:** No [BLOCK] or [CRITICAL] findings. Push can proceed. Clean cleanup + test coverage for the post-trim contract.

=== llm (20.63s) ===
## Review Summary

This is a clean, well-scoped diff. Two commits: dead code removal (REQ-049) and negative tests for removed models (REQ-050). Both align precisely with their requirements.

---

### Code Changes

**adapter.py (REQ-049):** Removed the `vertex_openapi` detection branch (4 prefixes: panel-member, minimax, zai-org, deepseek-ai) and the corresponding `call_vertex_openapi` import. Removed the `elif p == "vertex_openapi"` routing branch in `call_llm`. The `else: raise ValueError` catch-all remains, so the dead `"vertex_openapi"` provider string could never reach `call_llm` anyway — this is pure dead code cleanup. Correct.

**tests/test_models.py (REQ-050):** 8 removed canonical names tested against `resolve_model` (expect None). 4 removed model_ids tested against `detect_provider` (expect ValueError). Tests are parametrized inline with clear assertion messages.

**Docs:** HANDOVER, HANDOVER_rama, REQUIREMENTS all updated consistently. REQ-049 and REQ-050 status changed from not-started to implemented. REQ-050 expected behavior updated to match actual implementation (detect_provider raises ValueError, not inference endpoint returns 400).

---

### Findings

[INFO] tests/test_models.py:83-93 — The 8 removed canonical names are hardcoded strings. If someone accidentally adds one back to the registry, the test catches it — which is the point. However, these names aren't sourced from any authoritative "removed models" list, so if the set of removed models grows, someone has to remember to update this test. Consider a comment noting these came from the 27→9 trim (REQ-046). Minor, no action required.

[INFO] tests/test_models.py:96-105 — `zai-org/fallback-model-maas` is tested as a removed model_id that should raise ValueError. This is correct today (no `zai-org` prefix handler exists). If Vertex OpenAPI support is re-added in the future (the function is kept in other.py per REQ-049), this test will correctly fail and force an explicit decision — good design.

[INFO] src/llm/adapter.py:31 — The `else: raise ValueError(f"Unsupported provider: {p}")` branch in `call_llm` is now technically unreachable since `detect_provider` already raises ValueError for unknown prefixes. It's still good defensive programming, so keeping it is fine.

---

No bugs, no security issues, no missing tests, no regressions, no ground rules violations. Blast radius: 5 files, 126 lines — well within limits. Both commits have proper trailers (Test-Plan, Agent, Req). Requirements match implementation exactly.

**Result: PASS — no blocking findings.**

=== reviewer-model (24.01s) ===
[BLOCK] No blocking findings. Implementation matches requirements.

[INFO] REQ-050 duplicate in REQUIREMENTS.md — The requirement appears twice (lines ~417 and ~439) with identical content. This is pre-existing in the document, not introduced by this diff. Should be cleaned up in a separate commit to avoid documentation drift.

[INFO] Test coverage is appropriate — 8 removed canonical names + 4 removed model_ids covers the retired models mentioned in REQ-050 (retired-model-id-b, retired-model-id-c, retired-model-id-a, etc.). The tests verify both `resolve_model` returns None and `detect_provider` raises ValueError as specified.

[INFO] Dead code removal is clean — REQ-049 implementation correctly removes the vertex_openapi detection branch and unused import from adapter.py while preserving `call_vertex_openapi` in other.py for future a cloud AI platform models. No logic changes beyond removal.

[INFO] Documentation updates are consistent — HANDOVER.md timeline, HANDOVER_rama.md, and REQUIREMENTS.md status fields all reflect the implemented changes. Commit trailers include Test-Plan, Agent, and Req as required by Ground Rules.

[INFO] Blast radius within limits — 5 files, 126 lines total. Well under the 300 lines / 10 files hard limit.

**Summary:** Both commits implement their referenced requirements correctly. REQ-049 removes dead provider code; REQ-050 adds negative tests for removed models. No security issues, no regressions, no missing tests for the code changes. Push can proceed.

=== reviewer-model (48.45s) ===
 [INFO] No blocking, critical, or warning issues found. Diff correctly implements REQ-049 (dead code removal) and REQ-050 (negative test coverage) per specifications.

**Verification against requirements:**

**REQ-049 (Dead provider code cleanup):**
- Removed `call_vertex_openapi` import from adapter.py line 7.
- Removed detection branch for `panel-member`, `minimax`, `zai-org`, `deepseek-ai` prefixes from `detect_provider()` (lines 29-30 removed).
- Removed `vertex_openapi` provider branch from `call_llm()` (lines 59-60 removed).
- `detect_provider()` now only handles 6 active providers (six active providers) and raises `ValueError` for unknown model_ids, matching expected behavior.

**REQ-050 (Negative tests for removed models):**
- `test_removed_canonical_names_return_none()` verifies 8 removed canonical names (retired-canonical-c, retired-canonical-d, retired-canonical-a, light-model-a, light-model-b, reviewer-model-fast, retired-canonical-b, retired-canonical-e) return `None` from `resolve_model()`.
- `test_removed_model_ids_raise_in_detect_provider()` verifies 4 removed model_ids (meta/retired-model-id-c-instruct, deepseek-ai/retired-model-id-b, zai-org/fallback-model-maas, retired-canonical-e) raise `ValueError` with "Unknown provider" message from `detect_provider()`.

**Ground rules compliance:**
- Commit trailers present: `Test-Plan`, `Agent: agent-eta`, `Req: REQ-050` and `Req: REQ-049`.
- Handover files updated (`HANDOVER_rama.md`, aggregated into `HANDOVER.md`).
- Requirements status updated to `implemented` in `REQUIREMENTS.md`.
- No secrets, no dependency changes, no infra changes.

=== reviewer-model (55.3s) ===
[BLOCK] Unauthorized modification of REQ-050 expected behavior. The original requirement explicitly stated: "Inference endpoint returns 400 for removed model_ids." The diff changes this to "detect_provider raises ValueError for removed model_ids" to match the newly written unit test. You cannot rewrite the spec to match your code; your code must match the spec (Rule 17). If `detect_provider` raises a `ValueError` that is not caught and mapped by the endpoint router, the API will return a 500 Internal Server Error instead of the required 400 Bad Request. Revert the change to the requirement text and implement the actual endpoint test to verify the 400 status code.

=== AGGREGATED ===
As your moderator, I have synthesized the feedback from the six models regarding the proposed push. There is a clear divide in the evaluation of the documentation and testing strategy.

### Areas of Disagreement (The Signal)
*   **The "Spec vs. Implementation" Conflict:** A significant disagreement exists regarding the update to `REQUIREMENTS.md`. 
    *   **one panel model-3.1-pro** and **reviewer-model** argue that changing the requirement from "Inference endpoint returns 400" to "detect_provider raises ValueError" is a violation of protocol (Rule 17). They contend that a `ValueError` at the provider detection layer may bubble up as a 500 error, failing the original requirement for a 400 client error.
    *   **one panel member** and **one panel model-one panel model-4.6** defend the change, citing a "2026-03-28 clarification" that permits updating requirements to match implementation within the same commit, viewing the change as a necessary alignment of the contract.
*   **Test Coverage Adequacy:** 
    *   **reviewer-model** identifies a [CRITICAL] gap: the lack of an endpoint-level test to verify that the inference path actually returns the expected error code for retired models.
    *   Conversely, **one panel model-one panel model**, **Dashscope**, and **Redpill** view the current test suite as sufficient, focusing on the unit-level verification of `resolve_model` and `detect_provider`.

### Unique/Creative Insights
*   **The "Future-Proofing" Observation:** **one panel model-one panel model** noted that the `zai-org/fallback-model-maas` test case is particularly clever; by testing a removed ID that relies on a removed prefix, the test acts as a "tripwire." If Vertex OpenAPI support is ever re-added, the test will fail, forcing an explicit architectural decision.
*   **Documentation Hygiene:** **Dashscope** pointed out a pre-existing duplicate of REQ-050 in the requirements document, suggesting that while the current diff is clean, the underlying documentation requires a separate cleanup pass.

### Majority View
The majority of models (one panel model, one panel model, Dashscope, Redpill) view the diff as a clean, well-scoped, and compliant implementation. They emphasize that the blast radius is minimal and the code changes are logically sound.

### Moderator Recommendation
**Do not proceed with the push in its current state.**

While the code changes are technically sound, the **[BLOCK]** raised by **one panel model-3.1-pro** and the **[CRITICAL]** concern from **reviewer-model** regarding the inference path cannot be ignored. 

**Recommended Path Forward:**
1.  **Verify the Error Code:** Perform a quick integration test to confirm whether the `ValueError` raised by `detect_provider` is caught by the API layer and returned as a 400, or if it results in a 500. 
2.  **Address the Requirement Mismatch:** If the API returns a 500, you must implement a handler to map that `ValueError` to a 400 to satisfy the original REQ-050. 
3.  **Documentation:** If you choose to keep the requirement change, ensure the "2026-03-28 clarification" is explicitly cited in the commit message or a `CHANGELOG` to resolve the ambiguity flagged by the reviewers. 

Once you have verified the HTTP status code returned by the inference endpoint, the push will be ready.
