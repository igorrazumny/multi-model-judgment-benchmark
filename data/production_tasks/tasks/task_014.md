---
id: task_014
category: code_review
char_count: 3536
redaction: org-names-agents-pii-strategy-model-ids-removed
---

# Code Review — LLM-generated code
# code_generated_by: llm

You are a code review gate. Review this branch diff before push.
Check for bugs, security issues, ground rules compliance, missing tests, regressions.

BRANCH: cvc/2026-03-28-readme-project-rename
COMMIT: 34ab847
REPO: product-code (Product Code — AI dev assistant)

=== DIFF (      55 lines) ===
diff --git a/README.md b/README.md
index a5bb7d7..28df705 100644
--- a/README.md
+++ b/README.md
@@ -17,9 +17,9 @@ export PROVIDER_A_API_KEY=sk-...
 Usage examples:
 
 ```bash
-python -m src "add a health check endpoint" --project /path/to/repo
-python -m src --interactive --project /path/to/repo
-python -m src --watch --project /path/to/repo
+cvc "add a health check endpoint"
+cvc -i
+cvc -w
 ```
 
 ## BEFORE ANY CHANGES - READ GROUND RULES
diff --git a/docs/HANDOVER.md b/docs/HANDOVER.md
index 55dda63..e56fb3a 100644
--- a/docs/HANDOVER.md
+++ b/docs/HANDOVER.md
@@ -2,12 +2,13 @@
 **Current state and recent decisions — product-code**
 Aggregated from per-agent files in `docs/handover/`. Each agent writes to their own file.
 
-Last aggregated: 2026-03-28 | Agents: 4 | Entries: 59
+Last aggregated: 2026-03-28 | Agents: 4 | Entries: 60
 
 ---
 
 ## Timeline
 
+- 2026-03-28T05:29 [cvc] docs: switched the README Quick Start examples to the user-facing `cvc` CLI (`cvc "task"`, `cvc -i`, `cvc -w`). Re-verified targeted CLI/git/tool tests with 80 passing tests.
 - 2026-03-28T05:25 [cvc] docs: restored the README Quick Start API-key setup note after review feedback while keeping install + three usage examples. Re-verified targeted CLI/git/tool tests with 80 passing tests.
 - 2026-03-28T05:22 [cvc] docs: added a top-level README Quick Start section with editable install instructions and three CLI usage examples (task, interactive, watch). Verified with `python3 -m pytest -q` (no tests collected).
 - 2026-03-28T00:00 [cvc] docs: renamed README branding from CodeRobin to Product Code (CVC) and updated the repo URL to `example-org/product-code`. Kept commit/version-bump tests deterministic by asserting the fixture-driven bumped version. Verified with 294 passing tests.
diff --git a/docs/handover/HANDOVER_cvc.md b/docs/handover/HANDOVER_cvc.md
index 6c54f5c..1ad4485 100644
--- a/docs/handover/HANDOVER_cvc.md
+++ b/docs/handover/HANDOVER_cvc.md
@@ -1,5 +1,6 @@
 # Handover — cvc
 
+- 2026-03-28T05:29 docs: switched the README Quick Start examples to the user-facing `cvc` CLI (`cvc "task"`, `cvc -i`, `cvc -w`). Re-verified targeted CLI/git/tool tests with 80 passing tests.
 - 2026-03-28T05:25 docs: restored the README Quick Start API-key setup note after review feedback while keeping install + three usage examples. Re-verified targeted CLI/git/tool tests with 80 passing tests.
 - 2026-03-28T05:22 docs: added a top-level README Quick Start section with editable install instructions and three CLI usage examples (task, interactive, watch). Verified with `python3 -m pytest -q` (no tests collected).
 - 2026-03-28T00:00 docs: renamed README branding from CodeRobin to Product Code (CVC) and updated the repo URL to `example-org/product-code`. Kept commit/version-bump tests deterministic by asserting the fixture-driven bumped version. Verified with 294 passing tests.
diff --git a/src/version.py b/src/version.py
index 7876714..a56b092 100644
--- a/src/version.py
+++ b/src/version.py
@@ -1,2 +1,2 @@
 # Auto-bumped by CommitManager during successful commits.
-__version__ = "2026.03.28.4"
+__version__ = "2026.03.28.5"
=== END DIFF ===
