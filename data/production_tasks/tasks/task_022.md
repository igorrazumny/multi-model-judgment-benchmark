---
id: task_022
category: code_review
char_count: 9256
redaction: org-names-agents-pii-strategy-labels-removed
---

# Code Review: fix: R22e CRITICALs — model health auth + streaming timeouts
Repository: example-org/example-org-platform
PR: #9
Type: code_review

## PR Description
## Summary
- `/api/health/models` moved behind auth → `/api/v1/health/models` (was public, exposed model inventory)
- Streaming timeouts increased: IDLE 5s→120s, FIRST_RESPONSE 15s→120s, STRAGGLER 15s→300s (Kimi/GLM-5 need >60s)
- Makefile updated for new endpoint path

## Test plan
- [x] 67/67 tests pass
- [x] New test verifies 403 without auth token
- [ ] Deploy and verify no model enumeration on public endpoint

Agent: agent-eta

## Diff
```diff
diff --git a/Makefile b/Makefile
index 75a35dd..adaff38 100644
--- a/Makefile
+++ b/Makefile
@@ -64,10 +64,10 @@ check-models-val:
 	@bash scripts/check-models.sh https://api-val.example.com
 
 model-health:
-	@curl -s https://api.example.com/api/health/models | python3 -m json.tool 2>/dev/null || echo "Not reachable"
+	@curl -s -H "Authorization: Bearer $${PLATFORM_API_KEY}" https://api.example.com/api/v1/health/models | python3 -m json.tool 2>/dev/null || echo "Not reachable (set PLATFORM_API_KEY)"
 
 model-health-val:
-	@curl -s https://api-val.example.com/api/health/models | python3 -m json.tool 2>/dev/null || echo "Not reachable"
+	@curl -s -H "Authorization: Bearer $${PLATFORM_API_KEY}" https://api-val.example.com/api/v1/health/models | python3 -m json.tool 2>/dev/null || echo "Not reachable (set PLATFORM_API_KEY)"
 
 logs-cloud:
 	@gcloud logging read 'resource.type="gce_instance" AND labels.app="platform"' \
diff --git a/docs/HANDOVER.md b/docs/HANDOVER.md
index bfa30f3..8086078 100644
--- a/docs/HANDOVER.md
+++ b/docs/HANDOVER.md
@@ -2,13 +2,18 @@
 **Current state and recent decisions — example-org-platform**
 Aggregated from per-agent files in `docs/handover/`. Each agent writes to their own file.
 
-Last aggregated: 2026-03-28 | Agents: 4 | Entries: 45
+Last aggregated: 2026-03-28 | Agents: 4 | Entries: 50
 
 ---
 
 ## Timeline
 
 - 2026-03-28T10:00 [agent-epsilon] docs: OPERATIONS.md — full ops runbook with monitoring commands, deployment procedures, API endpoint reference, model registry summary, known issues, GCP infrastructure overview. Covers make targets: health, check-models, model-health, logs-cloud, deploy-gcp.
+- 2026-03-28T05:30 [agent-eta] fix: R22e CRITICALs — /api/health/models moved behind auth (was public, exposed model names), streaming timeouts increased (5s→120s idle, 15s→120s first response, 15s→300s straggler) to accommodate Kimi/GLM-5
+- 2026-03-26T18:00 [agent-pi] Progress-based timeout: replaced fixed/calculated timeout with stall detection. Monitor vLLM container logs — as long as progress, keep waiting. Fail only if: preempted, container dead, or no progress for 5min. Max safety cap 2h (for 750GB models). Model-agnostic, SSD-agnostic.
+- 2026-03-26T17:00 [agent-pi] Smart timeout v1 (superseded by progress-based): HF API model size query + speed estimate.
+- 2026-03-26T15:00 [agent-pi] bugs R26 fixes: INT8 no longer maps to gptq (split INT8/GPTQ/FP8), vLLM image pinned to v0.18.0, provisioning scripts require explicit --project (no silent default). Scope issue registered as tracked bug (needs dedicated SA).
+- 2026-03-26T14:00 [agent-pi] Phase 3 code: added --port and --tensor-parallel to provision.sh, vllm-startup.sh, health.sh, test-inference.sh. Dynamic container naming (vllm-{port}), scaled shm-size, firewall tcp:8000-8001. Ready for multi-model testing when H100 Spot available.
 - 2026-03-26T08:00 [agent-pi] Phase 1 PROVEN: 3/3 e2e tests pass (Qwen2.5-7B, H100 Spot, us-central1-b, ~8min each). Updated ARCHITECTURE.md + GPU_OPERATIONS.md with full lifecycle docs, quick-start, scripts reference. Next: Phase 2 (Qwen3.5-27B-FP8 x3), then Phase 3 (2 models on 1 GPU).
 - 2026-03-26T07:30 [agent-epsilon] fix: panel review findings (2 rounds) — dedicated _EmptyResponseError (was swallowing config errors), model+model_id ambiguity check moved before mode dispatch, multi mode works without model field, REQUIREMENTS.md updated (REQ-015/018/021). Health check script tested on prod: 21/27 OK, 5 fail (Gemini Pro, GPT-5 Mini, Qwen Coder, MiniMax, vllm×2), 1 empty. agent-eta investigating broken models.
 - 2026-03-26T07:15 [agent-pi] PR #1 merged. E2e test: stockout in zone a, zone b worked but grep -P fails on macOS. Fixed to sed. gpu-down teardown confirmed working. Retesting.
diff --git a/docs/handover/HANDOVER_rama.md b/docs/handover/HANDOVER_rama.md
index a284460..eb473e1 100644
--- a/docs/handover/HANDOVER_rama.md
+++ b/docs/handover/HANDOVER_rama.md
@@ -1,3 +1,4 @@
+- 2026-03-28T05:30 fix: R22e CRITICALs — /api/health/models moved behind auth (was public, exposed model names), streaming timeouts increased (5s→120s idle, 15s→120s first response, 15s→300s straggler) to accommodate Kimi/GLM-5
 - 2026-03-26T07:00 docs: 200K token verification for all 7 models in ops/DECISIONS.md. GLM-5 confirmed at 197K tokens (605s). All others pass. REQ-038 added (provider-specific routing).
 - 2026-03-24T14:00 fix: GLM-5 route agent-chi — Vertex AI MaaS (zai-org/glm-5-maas) returns 429 on large diffs, RedPill (redpill/z-ai/glm-5) works. Switched all review modes to RedPill route. Tested: 46.82s/2642 chars on 22KB diff via RedPill vs instant 429 via Vertex AI.
 - 2026-03-24T13:30 fix: GLM-5 empty responses on code reviews — add max_tokens to Vertex AI OpenAPI request, log finish_reason on empty responses. Root cause: large code diffs exceeded context without max_tokens param. Tests added.
diff --git a/src/api/server.py b/src/api/server.py
index d17f466..9dcb619 100644
--- a/src/api/server.py
+++ b/src/api/server.py
@@ -71,9 +71,13 @@ def health():
     return {"status": "ok", "service": "example-org-platform", "version": "0.1.0"}
 
 
[REDACTED_EMAIL]("/api/health/models")
+# --- Protected endpoints (Bearer auth required) ---
+v1 = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_api_key)])
+
+
[REDACTED_EMAIL]("/health/models")
 def model_health():
-    """Model health dashboard — per-model success rates, errors, latency. No auth (ops tool)."""
+    """Model health dashboard — per-model success rates, errors, latency."""
     from src.api.health import get_health
     stats = get_health()
     degraded = [mid for mid, s in stats.items() if s["success_rate"] is not None and s["success_rate"] < 0.8]
@@ -85,10 +89,6 @@ def model_health():
     }
 
 
-# --- Protected endpoints (Bearer auth required) ---
-v1 = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_api_key)])
-
-
 class MultiConfig(BaseModel):
     return_individual: bool = False
 
diff --git a/src/api/streaming.py b/src/api/streaming.py
index 5460224..3a64877 100644
--- a/src/api/streaming.py
+++ b/src/api/streaming.py
@@ -18,10 +18,12 @@
 logger = get_logger(__name__)
 
 # --- Timeouts ---
-FIRST_RESPONSE_TIMEOUT = 15   # Max wait for first model to complete
-IDLE_TIMEOUT = 5              # Max wait with no events before we consider it dead
-STRAGGLER_THRESHOLD = 15      # Drop models this many seconds behind the last completion
-AGGREGATION_TIMEOUT = 30      # Max wait for aggregation model
+# GLM-5 takes up to 340s at 200K tokens, Kimi K2.5 up to 112s on typical diffs.
+# Timeouts must accommodate slowest model without dropping it.
+FIRST_RESPONSE_TIMEOUT = 120  # Max wait for first model to complete
+IDLE_TIMEOUT = 120            # Max wait with no events (models are processing, not streaming)
+STRAGGLER_THRESHOLD = 300     # Drop models this many seconds behind the last completion
+AGGREGATION_TIMEOUT = 60      # Max wait for aggregation model
 
 
 class StreamReviewRequest(BaseModel):
diff --git a/tests/test_health.py b/tests/test_health.py
index 37b676c..9fa0636 100644
--- a/tests/test_health.py
+++ b/tests/test_health.py
@@ -31,9 +31,15 @@ def client():
 
 # --- Health endpoint ---
 
-def test_health_models_no_auth(client):
-    """Model health endpoint is public (ops tool)."""
-    r = client.get("/api/health/models")
+def test_health_models_requires_auth(client):
+    """Model health endpoint requires auth (R22e fix)."""
+    r = client.get("/api/v1/health/models")
+    assert r.status_code == 403  # No Bearer token
+
+
+def test_health_models_with_auth(client):
+    """Model health endpoint works with valid auth."""
+    r = client.get("/api/v1/health/models", headers=AUTH)
     assert r.status_code == 200
     assert r.json()["status"] == "healthy"
 
@@ -45,7 +51,7 @@ def test_health_models_after_calls(client):
     record_success("gpt-5.4", 2.0, 200)
     record_error("glm-5", 0.3, "Empty response")
 
-    r = client.get("/api/health/models")
+    r = client.get("/api/v1/health/models", headers=AUTH)
     data = r.json()
     assert data["total_models_seen"] == 2
     assert data["models"]["gpt-5.4"]["success"] == 2
@@ -129,7 +135,7 @@ def test_degraded_status(client):
     record_error("model-b", 0.5, "timeout")
     record_success("model-b", 1.0, 50)
 
-    r = client.get("/api/health/models")
+    r = client.get("/api/v1/health/models", headers=AUTH)
     data = r.json()
     # model-b: 1 success, 2 errors = 33% success rate (<80%)
     assert "model-b" in data["degraded"]
```

Review this code change. Identify critical bugs, non-critical issues, and valuable perspectives.
