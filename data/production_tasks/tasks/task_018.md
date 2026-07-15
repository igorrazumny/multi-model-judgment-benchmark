---
id: task_018
category: code_review
char_count: 5835
redaction: org-names-agents-pii-strategy-labels-removed
---

# Code Review — GPT-5.4 generated code
# code_generated_by: openai-gpt-5.4

You are a code review gate. Review this branch diff before push.
Check for bugs, security issues, ground rules compliance, missing tests, regressions.

BRANCH: cvc/2026-03-28-rename-src-package
COMMIT: 85b958b
REPO: product-code (Product Code — AI dev assistant)

=== DIFF (     105 lines) ===
diff --git a/cvc/__main__.py b/cvc/__main__.py
index 7c820d7..6541d61 100644
--- a/cvc/__main__.py
+++ b/cvc/__main__.py
@@ -2,4 +2,6 @@
 
 from cvc.cli import main
 
-main()
+
+if __name__ == "__main__":
+    main()
diff --git a/cvc/version.py b/cvc/version.py
index 86c5add..9374954 100644
--- a/cvc/version.py
+++ b/cvc/version.py
@@ -1,2 +1,2 @@
 # Auto-bumped by CommitManager during successful commits.
-__version__ = "2026.03.28.6"
+__version__ = "2026.03.28.7"
diff --git a/docs/HANDOVER.md b/docs/HANDOVER.md
index 773015d..980baff 100644
--- a/docs/HANDOVER.md
+++ b/docs/HANDOVER.md
@@ -2,13 +2,14 @@
 **Current state and recent decisions — product-code**
 Aggregated from per-agent files in `docs/handover/`. Each agent writes to their own file.
 
-Last aggregated: 2026-03-28 | Agents: 4 | Entries: 62
+Last aggregated: 2026-03-28 | Agents: 4 | Entries: 63
 
 ---
 
 ## Timeline
 
 - 2026-03-28T13:14 [cvc] fix: simplified `cvc/__main__.py` so `python -m cvc` and editable installs both execute the CLI entrypoint cleanly. Verified with `python3 -m pytest -q`, `python3 -m pip install --break-system-packages --use-pep517 -e .`, and `cvc --version`.
+- 2026-03-28T12:55 [cvc] fix: restored `cvc.__main__` import safety by reinstating the `__name__ == "__main__"` guard and added tests covering safe import plus `python -m cvc` execution. Verified with 298 passing tests.
 - 2026-03-28T12:50 [cvc] fix: `cvc` now defaults to interactive REPL mode when invoked with no task or mode flags, and REPL help documents `/exit` as an alias for `/quit`. Updated REQ-087/REQ-140 and REQ-140 test cases. Verified with 296 passing tests.
 - 2026-03-28T05:29 [cvc] docs: switched the README Quick Start examples to the user-facing `cvc` CLI (`cvc "task"`, `cvc -i`, `cvc -w`). Re-verified targeted CLI/git/tool tests with 80 passing tests.
 - 2026-03-28T05:25 [cvc] docs: restored the README Quick Start API-key setup note after review feedback while keeping install + three usage examples. Re-verified targeted CLI/git/tool tests with 80 passing tests.
diff --git a/docs/handover/HANDOVER_cvc.md b/docs/handover/HANDOVER_cvc.md
index 40aebe1..fc4126a 100644
--- a/docs/handover/HANDOVER_cvc.md
+++ b/docs/handover/HANDOVER_cvc.md
@@ -1,5 +1,6 @@
 # Handover — cvc
 
+- 2026-03-28T12:55 fix: restored `cvc.__main__` import safety by reinstating the `__name__ == "__main__"` guard and added tests covering safe import plus `python -m cvc` execution. Verified with 298 passing tests.
 - 2026-03-28T12:50 fix: `cvc` now defaults to interactive REPL mode when invoked with no task or mode flags, and REPL help documents `/exit` as an alias for `/quit`. Updated REQ-087/REQ-140 and REQ-140 test cases. Verified with 296 passing tests.
 - 2026-03-28T05:29 docs: switched the README Quick Start examples to the user-facing `cvc` CLI (`cvc "task"`, `cvc -i`, `cvc -w`). Re-verified targeted CLI/git/tool tests with 80 passing tests.
 - 2026-03-28T05:25 docs: restored the README Quick Start API-key setup note after review feedback while keeping install + three usage examples. Re-verified targeted CLI/git/tool tests with 80 passing tests.
diff --git a/docs/history/2026-03-28_cvc.md b/docs/history/2026-03-28_cvc.md
index 23a3239..4d628b7 100644
--- a/docs/history/2026-03-28_cvc.md
+++ b/docs/history/2026-03-28_cvc.md
@@ -6,3 +6,4 @@
 - 2026-03-28T12:49 Added CLI regression test covering no-args default-to-interactive behavior and REPL help coverage for `/exit` alias.
 - 2026-03-28T12:49 Ran full pytest suite: 296 tests passing.
 - 2026-03-28T12:50 Commit hook rejected initial commit because requirement trailer/handover updates are mandatory; updated REQ-087 and REQ-140, refreshed REQ-140 test cases, and added handover/history entries.
+- 2026-03-28T12:54 Pre-push review flagged prior `cvc/__main__.py` simplification as unsafe on import. Restored the guard and added explicit tests for safe module import and `python -m cvc` execution semantics.
diff --git a/tests/test_cli.py b/tests/test_cli.py
index da9faa4..bfe9dff 100644
--- a/tests/test_cli.py
+++ b/tests/test_cli.py
@@ -3,6 +3,7 @@
 import json
 import logging
 import os
+import runpy
 import subprocess
 from datetime import datetime
 from unittest.mock import MagicMock
@@ -78,6 +79,32 @@ def test_main_version_flag_prints_version_and_exits(monkeypatch, capsys):
     assert captured.out.strip() == f"Product Code v{__version__}"
 
 
+def test_module_import_does_not_run_cli(monkeypatch):
+    real_import = __import__
+
+    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
+        if name == "cvc.cli":
+            module = real_import(name, globals, locals, fromlist, level)
+            module.main = MagicMock(side_effect=AssertionError("main should not run on import"))
+            return module
+        return real_import(name, globals, locals, fromlist, level)
+
+    monkeypatch.setattr("builtins.__import__", guarded_import)
+    runpy.run_module("cvc.__main__", run_name="cvc.__main__")
+
+
+def test_python_dash_m_cvc_executes_main(monkeypatch):
+    main_mock = MagicMock(side_effect=SystemExit(0))
+    monkeypatch.setattr("cvc.cli.main", main_mock)
+
+    try:
+        runpy.run_module("cvc.__main__", run_name="__main__")
+    except SystemExit as exc:
+        assert exc.code == 0
+
+    main_mock.assert_called_once_with()
+
+
 def test_main_timeout_flag_overrides_settings(monkeypatch, tmp_path):
     get_settings.cache_clear()
 
=== END DIFF ===
