---
id: task_051
category: code_review
char_count: 100652
redaction: org-names-agents-pii-strategy-model-ids-removed
---

# Multi-model brainstorm — internal evaluation task
Mode: brainstorm
Models: reviewer-model (15.02s), moderator-model (20.7s), llm (44.56s), reviewer-model (98.08s), reviewer-model (112.4s), reviewer-model (149.37s)
is_code_review: false
code_generated_by: llm

## Prompt
````
debate Post-merge review of REQ-BENCH-318. This code is already on main. Flag any CRITICAL issues that warrant stopping the pipeline and fixing before data is collected.

DIFF:
diff --git a/src/pipeline/db_writer.py b/src/pipeline/db_writer.py
index 8dfabf0..048bfef 100644
--- a/src/pipeline/db_writer.py
+++ b/src/pipeline/db_writer.py
@@ -113,7 +113,7 @@ def _resolve_model(model_name, models_db):
 def write_to_cloud_sql(original_file, prompt_hash, request_type, confirmed_findings,
                        model_responses, rejected_by_model,
                        model_standalone_scores=None, model_aggregation_scores=None,
-                       model_debate_scores=None):
+                       model_debate_scores=None, model_standalone_ids=None):
     """Write confirmed findings + FP tracking to Cloud SQL."""
     conn = _get_connection()
     cur = conn.cursor()
@@ -196,6 +196,7 @@ def write_to_cloud_sql(original_file, prompt_hash, request_type, confirmed_findi
                 response_map[model_name] = (row["id"], model_row["id"])
 
         # Insert confirmed findings with vote metadata
+        finding_id_map = {}  # external_finding_id → DB finding_id
         for idx, f in enumerate(confirmed_findings):
             cat_key = CATEGORY_MAP.get(f.get("category"), "perspective")
             cur.execute("SELECT id FROM finding_categories WHERE key = %s", (cat_key,))
@@ -212,6 +213,8 @@ def write_to_cloud_sql(original_file, prompt_hash, request_type, confirmed_findi
                   f.get("description", "")[:500], f.get("vote_valid"),
                   f.get("source", "aggregation")))
             finding_id = cur.fetchone()["id"]
+            ext_fid = f.get("id", f"F{idx+1}")
+            finding_id_map[ext_fid] = finding_id
 
             # Link to models that found it (exact alias match only)
             for found_model_name in f.get("found_by", []):
@@ -226,6 +229,24 @@ def write_to_cloud_sql(original_file, prompt_hash, request_type, confirmed_findi
                         """, (finding_id, resp_id))
                         break
 
+        # Link findings to models via standalone scoring (covers light models + any model
+        # whose response matched golden set findings, even if not in found_by)
+        if model_standalone_ids and finding_id_map:
+            for model_name, matched_ids in model_standalone_ids.items():
+                if model_name not in response_map:
+                    continue
+                resp_id, _ = response_map[model_name]
+                for ext_fid in matched_ids:
+                    db_fid = finding_id_map.get(ext_fid)
+                    if db_fid:
+                        cur.execute("""
+                            INSERT INTO model_findings (finding_id, model_response_id)
+                            VALUES (%s, %s) ON CONFLICT DO NOTHING
+                        """, (db_fid, resp_id))
+                    else:
+                        log.warning(f"Standalone ID '{ext_fid}' matched by {model_name} "
+                                    f"not in finding_id_map (keys: {list(finding_id_map.keys())[:5]})")
+
         # Update per-model confirmed finding counts
         for resp_name, (resp_id, model_id) in response_map.items():
             cur.execute("""
diff --git a/src/pipeline/debate.py b/src/pipeline/debate.py
index fc65423..3e918a0 100644
--- a/src/pipeline/debate.py
+++ b/src/pipeline/debate.py
@@ -100,6 +100,9 @@ explain whether the counter-arguments changed your assessment.
     if agreed_findings:
         agreed_section = f"\nALREADY AGREED ({len(agreed_findings)} findings, not shown): {', '.join(agreed_findings)}\n"
 
+    # Use first actual finding ID as example in prompt (not hardcoded "F1")
+    example_id = findings[0]["id"] if findings else "F1"
+
     if round_num == 1:
         # Step 4: Position Statement — collect arguments only, no conclusion
         return f"""FINDINGS ANALYSIS
@@ -107,6 +110,7 @@ explain whether the counter-arguments changed your assessment.
 You are analyzing findings from a code/architecture/business review.
 For EACH finding, provide arguments FOR and AGAINST its validity. Be specific.
 Do NOT state a conclusion — just provide the strongest arguments on both sides.
+Use the EXACT finding IDs from the list below.
 
 Also: are there CRITICAL findings about the ORIGINAL TASK that were MISSED?
 Only findings about the actual code/architecture/business question.
@@ -130,7 +134,7 @@ FINDINGS TO ANALYZE:
 
 Return ONLY valid JSON:
 {{"arguments": [
-    {{"id": "F1", "argument_for": "why this finding is valid", "argument_against": "why it might not be valid"}}
+    {{"id": "{example_id}", "argument_for": "why this finding is valid", "argument_against": "why it might not be valid"}}
 ],
 "missed_critical": [
     {{"description": "critical finding not listed above", "reasoning": "why this is critical"}}
@@ -142,6 +146,7 @@ Return ONLY valid JSON:
 You have seen all arguments FOR and AGAINST each finding from multiple models.
 Now make your FINAL decision on each finding: VALID or INVALID.
 No justification needed — just your honest pick based on all the evidence.
+Use the EXACT finding IDs from the list below.
 
 ---
 
@@ -162,7 +167,7 @@ FINDINGS:
 
 Return ONLY valid JSON:
 {{"verdicts": [
-    {{"id": "F1", "verdict": "VALID|INVALID"}}
+    {{"id": "{example_id}", "verdict": "VALID|INVALID"}}
 ]}}"""
 
 
@@ -209,14 +214,31 @@ def run_debate(original_prompt, confirmed_findings, all_model_responses, api_key
         log.info(f"Debate round {round_num}: {len(debate_findings)} under debate, "
                  f"{len(agreed_findings)} agreed")
 
-        prompt = build_challenge_prompt(
-            original_preview, active_findings, responses_summary, round_num,
-            previous_arguments, agreed_findings if agreed_findings else None,
-        )
-
         start = time.time()
         try:
-            result = _call_model_group(model_names, prompt, api_key=api_key)
+            if round_num > 1 and previous_arguments:
+                # Round 2+: per-model prompts excluding own arguments (prevent self-confirmation)
+                per_model_results = []
+                for mn in model_names:
+                    # Filter out this model's own arguments from previous round
+                    filtered_args = "\n".join(
+                        line for line in previous_arguments.split("\n")
+                        if mn not in line
+                    ) if previous_arguments else ""
+                    model_prompt = build_challenge_prompt(
+                        original_preview, active_findings, responses_summary, round_num,
+                        filtered_args, agreed_findings if agreed_findings else None,
+                    )
+                    resp = _call_model(mn, model_prompt, api_key=api_key)
+                    per_model_results.append(resp)
+                result = {"individual_responses": per_model_results}
+            else:
+                # Round 1: same prompt for all models
+                prompt = build_challenge_prompt(
+                    original_preview, active_findings, responses_summary, round_num,
+                    previous_arguments, agreed_findings if agreed_findings else None,
+                )
+                result = _call_model_group(model_names, prompt, api_key=api_key)
         except Exception as e:
             log.error(f"Debate round {round_num} failed: {e}")
             break
@@ -257,7 +279,15 @@ def run_debate(original_prompt, confirmed_findings, all_model_responses, api_key
             for v in parsed.get("arguments", []) + parsed.get("verdicts", []):
                 fid = v.get("id", "")
                 if fid not in per_finding_votes:
-                    continue
+                    # Fallback: model may have returned unprefixed ID (e.g., "F1" instead of "expert_prop_F1")
+                    matched = [k for k in per_finding_votes if k.endswith(f"_{fid}")]
+                    if len(matched) == 1:
+                        fid = matched[0]
+                    else:
+                        # 0 matches or ambiguous (>1) — skip
+                        if len(matched) > 1:
+                            log.warning(f"  Ambiguous ID '{fid}' matches {matched}, rejecting")
+                        continue
                 verdict = v.get("verdict", "").upper()
                 arg_for = v.get("argument_for", "")
                 arg_against = v.get("argument_against", "")
diff --git a/src/pipeline/run_unified.py b/src/pipeline/run_unified.py
index 0cf6355..d0b9ebb 100644
--- a/src/pipeline/run_unified.py
+++ b/src/pipeline/run_unified.py
@@ -33,29 +33,44 @@ RESULTS_DIR = _SCRIPT_DIR / "data" / "results"
 
 # Import helpers from run_benchmark
 sys.path.insert(0, str(Path(__file__).parent))
+import run_benchmark as _rb
 from run_benchmark import (
     load_api_key, call_model, extract_json,
-    META_EVAL_PROMPT, EXTRACTION_MODEL, PLATFORM_URL, API_KEY,
+    META_EVAL_PROMPT, EXTRACTION_MODEL, PLATFORM_URL,
 )
 
-# Model groups — 4 tracks
-EXPERT_PROP = ["reviewer-model", "llm", "google-reviewer-model", "reviewer-model"]
-EXPERT_OPEN = ["alibaba-reviewer-model", "moonshot-reviewer-model"]
-LIGHT_PROP = ["light-model-b", "light-model-a", "light-model-c", "light-model-d"]
-LIGHT_OPEN = ["light-model-e", "light-model-f"]
+# Model groups — 2 tracks (no proprietary/open split)
+EXPERT_MODELS = [
+    "reviewer-model", "llm", "google-reviewer-model",
+    "reviewer-model", "alibaba-reviewer-model", "moonshot-reviewer-model",
+]
+LIGHT_MODELS = [
+    "light-model-b", "light-model-a", "light-model-c",
+    "light-model-d", "light-model-e",
+]
 
-# Debate thresholds per track
-THRESHOLDS = {
-    "expert_prop": 3/4,    # 3 of 4
-    "expert_open": 1.0,    # 2 of 2 (both must agree)
-    "light_prop": 0.5,     # 50%
-    "light_open": 0.5,     # 50%
-}
+# Debate threshold — only used for expert golden set construction
+EXPERT_DEBATE_THRESHOLD = 4/6  # 4 of 6 (supermajority)
 
 # Global thread pool — all API calls go through this, no nested pools
 POOL = ThreadPoolExecutor(max_workers=16)
 
 
+def resolve_id(fid, known_ids):
+    """Resolve a finding ID against known IDs. Handles prefixed/unprefixed mismatches.
+    Returns the matched known ID, or None if no match."""
+    if fid in known_ids:
+        return fid
+    # Model returned unprefixed "F1" but we have "expert_prop_F1"
+    matches = [k for k in known_ids if k.endswith(f"_{fid}")]
+    if len(matches) == 1:
+        return matches[0]
+    if len(matches) > 1:
+        log.warning(f"  Ambiguous ID '{fid}' matches {matches}, rejecting")
+        return None
+    return None
+
+
 def call_models_parallel(models, prompt):
     """Call multiple models in parallel using the global pool."""
     futures = {POOL.submit(call_model, m, prompt): m for m in models}
@@ -79,7 +94,15 @@ def run_track(models, content, track_name, threshold):
     track_start = time.time()
 
     # --- Standalone ---
-    standalone = call_models_parallel(models, content)
+    # Wrap raw content with minimal review instruction to reduce format variance
+    # without coaching models on what to find (per debate consensus)
+    standalone_prompt = f"""Review the following content and identify any findings, issues, or notable observations.
+Present your findings clearly.
+
+---
+
+{content}"""
+    standalone = call_models_parallel(models, standalone_prompt)
     succeeded = [r for r in standalone if r.get("status") == "completed" and r.get("response")]
     log.info(f"  [{track_name}] Standalone: {len(succeeded)}/{len(models)} responded")
     for r in standalone:
@@ -92,26 +115,55 @@ def run_track(models, content, track_name, threshold):
                 "status": "degraded"}
 
     # --- Aggregation ---
+    # Each model aggregates all other models' standalone responses
     responses_text = ""
     for r in succeeded:
         responses_text += f"\n=== {r['model']} ===\n{r['response']}\n"
 
-    agg_prompt = META_EVAL_PROMPT.format(
+    agg_prompt = f"""You are reviewing responses from multiple AI models to the same prompt.
+Each model provided its analysis independently. Your job is to identify SPECIFIC findings.
+
+List every distinct finding, issue, or insight from all responses combined. For each:
+1. State the finding clearly in one sentence
+2. Note if multiple models agree on it
+3. Flag if you think it is a false positive
+
+Also list any critical issues you see that ALL models missed.
+
+Do NOT provide meta-commentary about response quality. Focus on the SPECIFIC findings.
+
+ORIGINAL PROMPT:
+{content[:2000]}
+
+MODEL RESPONSES:
+{responses_text[:6000]}
+
+List all findings:"""
+
+    log.info(f"  [{track_name}] Aggregation (per-model)...")
+    agg_responses = call_models_parallel(models, agg_prompt)
+    agg_per_model = {}
+    for r in agg_responses:
+        agg_per_model[r.get("model", "")] = r.get("response", "")
+        log.info(f"    {r.get('model','?'):40} {len(r.get('response',''))} chars")
+
+    # Extraction — one panel model extracts unified findings from all standalone responses
+    extraction_prompt = META_EVAL_PROMPT.format(
         original_prompt_preview=content[:2000],
         model_responses=responses_text,
     )
-    log.info(f"  [{track_name}] Aggregation (extraction)...")
-    agg_result = call_model(EXTRACTION_MODEL, agg_prompt)
-    parsed = extract_json(agg_result.get("response", ""))
+    log.info(f"  [{track_name}] Extraction...")
+    extraction_result = call_model(EXTRACTION_MODEL, extraction_prompt)
+    parsed = extract_json(extraction_result.get("response", ""))
     if parsed and "findings" in parsed:
         findings = parsed["findings"]
         req_type = parsed.get("request_type", "unknown")
     else:
         findings = []
         req_type = "unknown"
-    # Prefix finding IDs with track name to avoid collisions across tracks
+    # Prefix finding IDs with track name — prevents dict key collision when merging tracks
     for f in findings:
-        if f.get("id") and not f["id"].startswith(track_name):
+        if f.get("id") and not f["id"].startswith(f"{track_name}_"):
             f["id"] = f"{track_name}_{f['id']}"
     log.info(f"  [{track_name}] Extraction: {len(findings)} findings, type={req_type}")
 
@@ -126,7 +178,22 @@ def run_track(models, content, track_name, threshold):
 
             debate_result = debate_mod.run_debate(
                 content, findings, succeeded,
+                api_key=_rb.API_KEY,
                 convergence_threshold=threshold)
+            # Prefix any NEW findings generated during debate (D1-* → track_D1-*)
+            for f in debate_result.get("final_confirmed", []):
+                if f.get("id") and not f["id"].startswith(f"{track_name}_"):
+                    f["id"] = f"{track_name}_{f['id']}"
+            # Also prefix IDs in interim data (verdict_by_finding keys)
+            for rd in debate_result.get("interim", []):
+                old_vbf = rd.get("verdicts_by_finding", {})
+                new_vbf = {}
+                for fid, vdata in old_vbf.items():
+                    if not fid.startswith(f"{track_name}_"):
+                        new_vbf[f"{track_name}_{fid}"] = vdata
+                    else:
+                        new_vbf[fid] = vdata
+                rd["verdicts_by_finding"] = new_vbf
             confirmed = len(debate_result.get("final_confirmed", []))
             log.info(f"  [{track_name}] Debate: {confirmed} confirmed, {debate_result['rounds']} rounds")
         except Exception as e:
@@ -139,102 +206,22 @@ def run_track(models, content, track_name, threshold):
         "track_name": track_name,
         "models": models,
         "standalone": standalone,
-        "aggregation": {"findings": findings, "request_type": req_type},
+        "aggregation": {"findings": findings, "request_type": req_type, "per_model": agg_per_model},
         "debate": debate_result,
         "status": "complete",
         "elapsed_s": elapsed,
     }
 
 
-def build_golden_set(track_a, track_b, content):
-    """Build golden set from expert tracks A + B via cross-verification + classification."""
-
-    # Get confirmed findings from each track
-    a_confirmed = {f["id"]: f for f in track_a["debate"].get("final_confirmed", [])}
-    b_confirmed = {f["id"]: f for f in track_b["debate"].get("final_confirmed", [])}
-
-    a_ids = set(a_confirmed.keys())
-    b_ids = set(b_confirmed.keys())
-    cross_confirmed = a_ids & b_ids
-    a_only = a_ids - b_ids
-    b_only = b_ids - a_ids
-
-    log.info(f"  Golden set: cross-confirmed={len(cross_confirmed)}, "
-             f"prop-only={len(a_only)}, open-only={len(b_only)}")
-
-    # Cross-verification for unique findings
-    all_findings = {**a_confirmed, **b_confirmed}
-    cross_accepted = set()
 
-    if a_only or b_only:
-        log.info("  Cross-verification of unique findings...")
 
-        if a_only:
-            # Prop-only findings → send to open models for review
-            a_only_text = "\n".join(f"  {fid}: {all_findings[fid].get('description','')}" for fid in a_only)
-            review_prompt = f"""Review these findings. For each, vote ACCEPT or REJECT.
-Only ACCEPT if the finding is genuinely valid and important.
-
-FINDINGS TO REVIEW:
-{a_only_text}
-
-ORIGINAL CONTEXT:
-{content[:2000]}
-
-Return JSON: {{"votes": [{{"id": "...", "accept": true/false}}]}}"""
-            open_reviews = call_models_parallel(EXPERT_OPEN, review_prompt)
-            # Count accepts per finding
-            for fid in a_only:
-                accepts = 0
-                for r in open_reviews:
-                    p = extract_json(r.get("response", ""))
-                    if p:
-                        for v in p.get("votes", []):
-                            if v.get("id") == fid and v.get("accept"):
-                                accepts += 1
-                if accepts >= 1:  # at least 1 open model accepts
-                    cross_accepted.add(fid)
-                    log.info(f"    {fid}: ACCEPTED by open ({accepts}/{len(EXPERT_OPEN)})")
-
-        if b_only:
-            # Open-only findings → send to proprietary models
-            b_only_text = "\n".join(f"  {fid}: {all_findings[fid].get('description','')}" for fid in b_only)
-            review_prompt = f"""Review these findings. For each, vote ACCEPT or REJECT.
-Only ACCEPT if the finding is genuinely valid and important.
-
-FINDINGS TO REVIEW:
-{b_only_text}
-
-ORIGINAL CONTEXT:
-{content[:2000]}
+def _classify_and_build_golden(confirmed_findings, expert_track, content):
+    """Build golden set from expert debate-confirmed findings with Material/Minor classification.
+    Simplified from build_golden_set — no cross-verification needed with single expert track."""
+    golden_findings = [dict(f) for f in confirmed_findings]  # copy to avoid mutation
+    for f in golden_findings:
+        f["source"] = "debate"
 
-Return JSON: {{"votes": [{{"id": "...", "accept": true/false}}]}}"""
-            prop_reviews = call_models_parallel(EXPERT_PROP, review_prompt)
-            for fid in b_only:
-                accepts = 0
-                for r in prop_reviews:
-                    p = extract_json(r.get("response", ""))
-                    if p:
-                        for v in p.get("votes", []):
-                            if v.get("id") == fid and v.get("accept"):
-                                accepts += 1
-                if accepts >= 3:  # 3/4 proprietary must accept
-                    cross_accepted.add(fid)
-                    log.info(f"    {fid}: ACCEPTED by proprietary ({accepts}/{len(EXPERT_PROP)})")
-
-    # Build final golden set
-    golden_ids = cross_confirmed | cross_accepted
-    golden_findings = []
-    for fid in golden_ids:
-        f = all_findings.get(fid)
-        if f:
-            f["source"] = "debate"
-            golden_findings.append(f)
-
-    log.info(f"  Golden set: {len(golden_findings)} findings "
-             f"(cross={len(cross_confirmed)}, accepted={len(cross_accepted)})")
-
-    # --- Classification vote: Material vs Minor ---
     if golden_findings:
         log.info("  Classification vote (Material vs Minor)...")
         findings_text = "\n".join(
@@ -247,41 +234,47 @@ MINOR = useful but incremental: style issues, naming conventions, minor optimiza
 FINDINGS:
 {findings_text}
 
+Use the EXACT finding IDs from the list above.
+
 Return ONLY valid JSON:
-{{"classifications": [{{"id": "F1", "class": "material"}}, {{"id": "F2", "class": "minor"}}]}}"""
+{{"classifications": [{{"id": "{golden_findings[0]['id'] if golden_findings else 'F1'}", "class": "material"}}, {{"id": "...", "class": "minor"}}]}}"""
 
-        all_expert_models = EXPERT_PROP + EXPERT_OPEN
-        classify_responses = call_models_parallel(all_expert_models, classify_prompt)
+        classify_responses = call_models_parallel(EXPERT_MODELS, classify_prompt)
 
+        known_ids = {f.get("id", "") for f in golden_findings}
         votes = {f.get("id", ""): {"material": 0, "minor": 0} for f in golden_findings}
         for cr in classify_responses:
             parsed = extract_json(cr.get("response", ""))
             if not parsed:
                 continue
             for c in parsed.get("classifications", []):
-                fid = c.get("id", "")
+                fid = resolve_id(c.get("id", ""), known_ids)
+                if not fid:
+                    continue
                 cls = c.get("class", "").lower()
-                if fid in votes:
-                    if "material" in cls:
-                        votes[fid]["material"] += 1
-                    elif "minor" in cls:
-                        votes[fid]["minor"] += 1
+                if "material" in cls:
+                    votes[fid]["material"] += 1
+                elif "minor" in cls:
+                    votes[fid]["minor"] += 1
 
         for f in golden_findings:
             fid = f.get("id", "")
             v = votes.get(fid, {"material": 0, "minor": 0})
-            f["severity"] = "material" if v["material"] >= v["minor"] else "minor"
+            if v["material"] == 0 and v["minor"] == 0:
+                f["severity"] = "minor"
+                log.warning(f"    {fid}: no classification votes — defaulting to MINOR")
+            else:
+                f["severity"] = "material" if v["material"] >= v["minor"] else "minor"
             f["severity_weight"] = 10 if f["severity"] == "material" else 1
             f["severity_votes"] = v
             log.info(f"    {fid}: {f['severity'].upper()} (m={v['material']}, n={v['minor']})")
 
+    golden_ids = [f.get("id", "") for f in golden_findings]
     weighted_total = sum(f.get("severity_weight", 1) for f in golden_findings) or 1
 
     return {
         "findings": golden_findings,
-        "golden_ids": list(golden_ids),
-        "cross_confirmed": list(cross_confirmed),
-        "cross_accepted": list(cross_accepted),
+        "golden_ids": golden_ids,
         "weighted_total": weighted_total,
     }
 
@@ -297,11 +290,24 @@ def score_track(track_data, golden_set, content):
     valid_ids = {f.get("id", "") for f in findings}
     ids_str = ", ".join(valid_ids)
 
+    # Debate-style extraction: one panel model + one panel model argue FOR/AGAINST, one panel model moderates
+    SCORER_A = "google-reviewer-model"
+    SCORER_B = "reviewer-model"
+    MODERATOR = "reviewer-model"
+
+    example_id = list(valid_ids)[0] if valid_ids else "F1"
+
     def score_by_ids(response_text):
         if not response_text or not findings:
             return 0.0, []
-        prompt = f"""Which of the BASELINE findings are identified or mentioned in the MODEL RESPONSE below?
-Two findings match if they describe the same issue, even in different words.
+
+        # Stage 1: Two scorers argue FOR/AGAINST and give verdict per finding (parallel)
+        argue_prompt = f"""For each BASELINE finding below, determine whether it is identified in the MODEL RESPONSE.
+For each finding, provide:
+1. An argument FOR why it IS present
+2. An argument AGAINST why it might NOT be
+3. Your verdict: PRESENT or ABSENT
+Focus on semantic meaning, not exact wording. A finding is present if the core concern is the same.
 
 BASELINE FINDINGS:
 {baseline_list}
@@ -309,12 +315,97 @@ BASELINE FINDINGS:
 MODEL RESPONSE:
 {response_text[:4000]}
 
-Return ONLY valid JSON: {{"matched_ids": ["F1", "D1-6"]}}
-Only include IDs from this list: {ids_str}"""
-        r = call_model(EXTRACTION_MODEL, prompt)
-        parsed = extract_json(r.get("response", ""))
-        matched = list(set(parsed.get("matched_ids", []))) if parsed else []
-        matched = [m for m in matched if m in valid_ids]
+Return ONLY valid JSON:
+{{"arguments": [{{"id": "{example_id}", "for": "why present", "against": "why not", "verdict": "PRESENT"}}]}}
+Use EXACT finding IDs from: {ids_str}"""
+
+        scorer_futures = {}
+        with ThreadPoolExecutor(max_workers=2) as scorer_pool:
+            scorer_futures["A"] = scorer_pool.submit(call_model, SCORER_A, argue_prompt)
+            scorer_futures["B"] = scorer_pool.submit(call_model, SCORER_B, argue_prompt)
+        try:
+            resp_a = scorer_futures["A"].result()
+        except Exception as e:
+            log.warning(f"      Scorer A ({SCORER_A}) failed: {e}")
+            resp_a = {"response": ""}
+        try:
+            resp_b = scorer_futures["B"].result()
+        except Exception as e:
+            log.warning(f"      Scorer B ({SCORER_B}) failed: {e}")
+            resp_b = {"response": ""}
+
+        # Parse verdicts + arguments from both scorers
+        parsed_a = extract_json(resp_a.get("response", "")) or {}
+        parsed_b = extract_json(resp_b.get("response", "")) or {}
+
+        verdicts_a = {}  # fid → "PRESENT"/"ABSENT"
+        verdicts_b = {}
+        args_by_finding = {}  # for moderator context on disputes
+
+        for source, parsed, verdicts in [("Scorer A", parsed_a, verdicts_a),
+                                          ("Scorer B", parsed_b, verdicts_b)]:
+            for arg in parsed.get("arguments", []):
+                fid = resolve_id(arg.get("id", ""), valid_ids)
+                if not fid:
+                    continue
+                v = arg.get("verdict", "").upper()
+                verdicts[fid] = "PRESENT" if "PRESENT" in v else "ABSENT"
+                if fid not in args_by_finding:
+                    args_by_finding[fid] = []
+                args_by_finding[fid].append(
+                    f"{source} FOR: {arg.get('for', '')[:300]}\n"
+                    f"{source} AGAINST: {arg.get('against', '')[:300]}\n"
+                    f"{source} VERDICT: {verdicts[fid]}")
+
+        if not args_by_finding:
+            log.warning(f"      Scoring: both scorers returned no parseable arguments — "
+                        f"returning None (scorer failure, not model failure)")
+            return None, []
+
+        # Determine agreement vs disputes
+        agreed_present = set()
+        agreed_absent = set()
+        disputed = {}  # fid → args text
+
+        for fid in args_by_finding:
+            va = verdicts_a.get(fid)
+            vb = verdicts_b.get(fid)
+            if va == "PRESENT" and vb == "PRESENT":
+                agreed_present.add(fid)
+            elif va == "ABSENT" and vb == "ABSENT":
+                agreed_absent.add(fid)
+            else:
+                disputed[fid] = "\n".join(args_by_finding[fid])
+
+        # Stage 2: Moderator only runs on disputes
+        resolved_present = set()
+        if disputed:
+            dispute_text = ""
+            for fid, args in disputed.items():
+                dispute_text += f"\n{fid}:\n{args}\n"
+
+            moderate_prompt = f"""Two reviewers DISAGREE on whether these findings appear in a model response.
+Review their arguments and render a FINAL VERDICT for each: PRESENT or ABSENT.
+
+DISPUTED FINDINGS:
+{dispute_text}
+
+Return ONLY valid JSON:
+{{"verdicts": [{{"id": "{example_id}", "verdict": "PRESENT"}}]}}
+Use EXACT finding IDs. Only mark PRESENT if genuinely identified."""
+
+            mod_resp = call_model(MODERATOR, moderate_prompt)
+            mod_parsed = extract_json(mod_resp.get("response", "")) or {}
+
+            for v in mod_parsed.get("verdicts", []):
+                fid = resolve_id(v.get("id", ""), valid_ids)
+                if fid and "PRESENT" in v.get("verdict", "").upper():
+                    resolved_present.add(fid)
+
+        matched = list(agreed_present | resolved_present)
+        log.info(f"      Scoring: agreed={len(agreed_present)} disputed={len(disputed)} "
+                 f"moderator→present={len(resolved_present)} total={len(matched)}")
+
         w = sum(next((bf.get("severity_weight", 1) for bf in findings if bf.get("id") == m), 1)
                 for m in matched)
         return round(100.0 * w / weighted_total, 1), matched
@@ -326,19 +417,20 @@ Only include IDs from this list: {ids_str}"""
     for r in track_data["standalone"]:
         model_name = r.get("model", "")
         if r.get("status") != "completed" or not r.get("response"):
-            scores[model_name] = {"standalone_pct": 0, "standalone_ids": [],
-                                   "aggregation_pct": 0, "aggregation_ids": [],
-                                   "debate_pct": 0, "debate_ids": []}
+            scores[model_name] = {"standalone_pct": None, "standalone_ids": [],
+                                   "aggregation_pct": None, "aggregation_ids": [],
+                                   "debate_pct": None, "debate_ids": [],
+                                   "status": "failed"}
+            log.warning(f"    {model_name:40} FAILED — excluded from scoring (not counted as 0%)")
             continue
 
         # Standalone
         std_pct, std_ids = score_by_ids(r["response"])
 
-        # Aggregation — score the track's aggregated finding list against golden set
-        # Each track produced a unified finding list from all models' responses
-        # This measures: did the aggregation process capture the golden set findings?
-        agg_findings_text = json.dumps(track_data.get("aggregation", {}).get("findings", []))
-        agg_pct, agg_ids = score_by_ids(agg_findings_text) if agg_findings_text != "[]" else (0.0, [])
+        # Aggregation — score each model's individual aggregation response
+        agg_per_model = track_data.get("aggregation", {}).get("per_model", {})
+        model_agg_text = agg_per_model.get(model_name, "")
+        agg_pct, agg_ids = score_by_ids(model_agg_text) if model_agg_text else (None, [])
 
         # Debate — which golden set findings did this model vote VALID on
         deb_valid = set()
@@ -347,10 +439,11 @@ Only include IDs from this list: {ids_str}"""
                 for arg in vdata.get("arguments", []):
                     if arg.get("model") == model_name:
                         verdict = arg.get("conclusion", "").upper()
+                        resolved_fid = resolve_id(fid, baseline_ids) or fid
                         if "VALID" in verdict and "INVALID" not in verdict:
-                            deb_valid.add(fid)
+                            deb_valid.add(resolved_fid)
                         elif "INVALID" in verdict:
-                            deb_valid.discard(fid)
+                            deb_valid.discard(resolved_fid)
         deb_matched = list(deb_valid & baseline_ids)
         deb_w = sum(next((bf.get("severity_weight", 1) for bf in findings if bf.get("id") == m), 1)
                     for m in deb_matched)
@@ -381,19 +474,17 @@ def process_data_point(filepath):
         log.info(f"  Result file already exists, skipping")
         return True
 
-    # --- Step 1: Run 4 tracks in parallel ---
+    # --- Step 1: Run 2 tracks in parallel ---
+    # Expert (6 models) and Light (5 models) — no proprietary/open split
     # Tracks run as threads (NOT in the global pool — avoids deadlock)
-    # Each track uses the global pool internally for API calls
     import threading
 
-    log.info("Step 1: Running 4 tracks in parallel...")
+    log.info("Step 1: Running 2 tracks in parallel...")
     start = time.time()
 
     track_configs = [
-        ("A", EXPERT_PROP, "expert_prop", THRESHOLDS["expert_prop"]),
-        ("B", EXPERT_OPEN, "expert_open", THRESHOLDS["expert_open"]),
-        ("C", LIGHT_PROP, "light_prop", THRESHOLDS["light_prop"]),
-        ("D", LIGHT_OPEN, "light_open", THRESHOLDS["light_open"]),
+        ("expert", EXPERT_MODELS, "expert", EXPERT_DEBATE_THRESHOLD),
+        ("light", LIGHT_MODELS, "light", None),  # no threshold — golden set comes from expert only
     ]
 
     tracks = {}
@@ -420,34 +511,38 @@ def process_data_point(filepath):
     for t in threads:
         t.join()
 
-    # Build golden set from expert tracks
+    # Build golden set from expert track debate-confirmed findings
     golden_set = None
-    if tracks.get("A", {}).get("status") != "failed" and tracks.get("B", {}).get("status") != "failed":
-        log.info("Step 2: Building golden set (expert tracks complete)...")
-        golden_set = build_golden_set(tracks["A"], tracks["B"], content)
-        log.info(f"  Golden set: {len(golden_set['findings'])} findings, "
-                 f"weighted_total={golden_set['weighted_total']}")
+    expert_track = tracks.get("expert", {})
+    if expert_track.get("status") != "failed":
+        confirmed = expert_track.get("debate", {}).get("final_confirmed", [])
+        if confirmed:
+            log.info(f"Step 2: Building golden set from expert debate ({len(confirmed)} confirmed)...")
+            # Classification vote: all expert models vote Material vs Minor
+            golden_set = _classify_and_build_golden(confirmed, expert_track, content)
+            log.info(f"  Golden set: {len(golden_set['findings'])} findings, "
+                     f"weighted_total={golden_set['weighted_total']}")
 
     elapsed_tracks = time.time() - start
     log.info(f"All tracks complete in {elapsed_tracks:.0f}s")
 
     if golden_set is None or not golden_set["findings"]:
-        log.warning("No golden set — expert tracks failed or no findings")
-        golden_set = golden_set or {"findings": [], "golden_ids": [], "cross_confirmed": [],
-                                     "cross_accepted": [], "weighted_total": 1}
+        log.warning("No golden set — expert track failed or no findings confirmed")
+        golden_set = golden_set or {"findings": [], "golden_ids": [],
+                                     "weighted_total": 1}
 
     # --- Step 3: Score all tracks ---
     log.info("Step 3: Scoring all tracks against golden set...")
     all_scores = {}
-    for label in ["A", "B", "C", "D"]:
+    for label in ["expert", "light"]:
         if label not in tracks or tracks[label].get("status") == "failed":
             continue
-        log.info(f"  Scoring track {label} ({tracks[label]['track_name']})...")
+        log.info(f"  Scoring track {label}...")
         track_scores = score_track(tracks[label], golden_set, content)
         all_scores.update(track_scores)
 
     # Get request type from expert track
-    req_type = tracks.get("A", {}).get("aggregation", {}).get("request_type", "unknown")
+    req_type = expert_track.get("aggregation", {}).get("request_type", "unknown")
 
     # --- Step 4: Save ---
     log.info("Step 4: Saving results...")
@@ -496,6 +591,7 @@ def process_data_point(filepath):
         model_standalone = {m: s["standalone_pct"] for m, s in all_scores.items()}
         model_agg = {m: s["aggregation_pct"] for m, s in all_scores.items()}
         model_debate = {m: s["debate_pct"] for m, s in all_scores.items()}
+        model_standalone_ids = {m: s.get("standalone_ids", []) for m, s in all_scores.items()}
 
         # Build model responses for DB writer
         all_standalone = []
@@ -506,7 +602,8 @@ def process_data_point(filepath):
                  golden_set["findings"], all_standalone, {},
                  model_standalone_scores=model_standalone,
                  model_aggregation_scores=model_agg,
-                 model_debate_scores=model_debate)
+                 model_debate_scores=model_debate,
+                 model_standalone_ids=model_standalone_ids)
     except Exception as e:
         log.error(f"  DB write failed: {e}")
 
diff --git a/src/web/ui/src/pages/Overview.jsx b/src/web/ui/src/pages/Overview.jsx
index 5ac6ac5..ac5e39d 100644
--- a/src/web/ui/src/pages/Overview.jsx
+++ b/src/web/ui/src/pages/Overview.jsx
@@ -113,6 +113,14 @@ export default function Overview() {
     return {};
   };
 
+  // Show "Multiple" when top models tie
+  const bestName = (sorted, field) => {
+    if (!sorted || sorted.length === 0) return <span style={{color:"#9ca3af"}}>pending</span>;
+    const topVal = sorted[0][field];
+    const tied = sorted.filter((m) => Math.round(m[field]) === Math.round(topVal));
+    return tied.length > 1 ? "Multiple" : sorted[0].display_name;
+  };
+
   const typeLabel = (m) => {
     const tier = getTier(m);
     if (m.provider_type === "proprietary") return `proprietary ${tier}`;
@@ -191,7 +199,7 @@ export default function Overview() {
           <div style={colStyle}>
             <div style={{...card, minHeight: 90}}>
               <div style={{ fontSize: 11, color: "#9ca3af" }}>Best Proprietary Aggregator</div>
-              <div style={{ fontSize: 13, fontWeight: 600 }}>{bestPropAgg?.display_name || <span style={{color:"#9ca3af"}}>pending</span>}</div>
+              <div style={{ fontSize: 13, fontWeight: 600 }}>{bestName(withAgg.filter((m) => m.provider_type === "proprietary").sort((a, b) => b.aggregation_pct - a.aggregation_pct), "aggregation_pct")}</div>
               <div style={{ fontSize: 20, fontWeight: 700 }}>
                 {bestPropAgg ? pct(bestPropAgg.aggregation_pct) : "\u2014"}
                 {bestPropAgg && (() => {
@@ -203,7 +211,7 @@ export default function Overview() {
             </div>
             <div style={{...card, minHeight: 90}}>
               <div style={{ fontSize: 11, color: "#9ca3af" }}>Best Open Source Aggregator</div>
-              <div style={{ fontSize: 13, fontWeight: 600 }}>{bestOpenAgg?.display_name || <span style={{color:"#9ca3af"}}>pending</span>}</div>
+              <div style={{ fontSize: 13, fontWeight: 600 }}>{bestName(withAgg.filter((m) => m.provider_type !== "proprietary").sort((a, b) => b.aggregation_pct - a.aggregation_pct), "aggregation_pct")}</div>
               <div style={{ fontSize: 20, fontWeight: 700 }}>
                 {bestOpenAgg ? pct(bestOpenAgg.aggregation_pct) : "\u2014"}
                 {bestOpenAgg && (() => {
@@ -225,7 +233,7 @@ export default function Overview() {
           <div style={colStyle}>
             <div style={{...card, minHeight: 90}}>
               <div style={{ fontSize: 11, color: "#9ca3af" }}>Best Proprietary After Debate</div>
-              <div style={{ fontSize: 13, fontWeight: 600 }}>{bestPropDeb?.display_name || <span style={{color:"#9ca3af"}}>pending</span>}</div>
+              <div style={{ fontSize: 13, fontWeight: 600 }}>{bestName(withDeb.filter((m) => m.provider_type === "proprietary").sort((a, b) => b.debate_pct - a.debate_pct), "debate_pct")}</div>
               <div style={{ fontSize: 20, fontWeight: 700 }}>
                 {bestPropDeb ? pct(bestPropDeb.debate_pct) : "\u2014"}
                 {bestPropDeb && (() => {
@@ -237,7 +245,7 @@ export default function Overview() {
             </div>
             <div style={{...card, minHeight: 90}}>
               <div style={{ fontSize: 11, color: "#9ca3af" }}>Best Open Source After Debate</div>
-              <div style={{ fontSize: 13, fontWeight: 600 }}>{bestOpenDeb?.display_name || <span style={{color:"#9ca3af"}}>pending</span>}</div>
+              <div style={{ fontSize: 13, fontWeight: 600 }}>{bestName(withDeb.filter((m) => m.provider_type !== "proprietary").sort((a, b) => b.debate_pct - a.debate_pct), "debate_pct")}</div>
               <div style={{ fontSize: 20, fontWeight: 700 }}>
                 {bestOpenDeb ? pct(bestOpenDeb.debate_pct) : "\u2014"}
                 {bestOpenDeb && (() => {
@@ -370,10 +378,10 @@ export default function Overview() {
                 {categories.filter((c) => c.key !== "perspective").map((c) => (
                   <th key={c.key} className="sortable-th" onClick={() => handleSort(c.key)} style={{...thStyle, whiteSpace: "nowrap", color: "#9ca3af"}}>
                     <Tip text={
-                      c.key === "critical" ? "Critical findings: crashes, data loss, security, wrong behavior" :
-                      c.key === "non_critical" ? "Non-critical findings: style, performance, code quality" :
+                      c.key === "critical" ? "Material findings: consequential to outcome — crashes, data loss, security, wrong behavior" :
+                      c.key === "non_critical" ? "Minor findings: useful but incremental — style, performance, code quality" :
                       c.name
-                    }>{c.key === "critical" ? "Critical Findings" : "Non-Critical Findings"}{arrow(c.key)}</Tip>
+                    }>{c.key === "critical" ? "Material Findings" : "Minor Findings"}{arrow(c.key)}</Tip>
                   </th>
                 ))}
                 <th style={{...thStyle, color: "#9ca3af"}}>
diff --git a/tests/test_golden_set.py b/tests/test_golden_set.py
new file mode 100644
index 0000000..2251b65
--- /dev/null
+++ b/tests/test_golden_set.py
@@ -0,0 +1,758 @@
+"""Tests for golden set construction in unified pipeline.
+
+Tests call real build_golden_set() and score_track() with mocked API calls.
+"""
+
+import sys
+import json
+import unittest
+from unittest.mock import patch, MagicMock
+from pathlib import Path
+
+sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "pipeline"))
+
+
+def make_track(findings, track_name="expert_prop"):
+    """Helper: build a minimal track result dict."""
+    return {
+        "track_name": track_name,
+        "models": [],
+        "standalone": [],
+        "aggregation": {"findings": findings},
+        "debate": {
+            "rounds": 2,
+            "final_confirmed": findings,
+            "interim": [],
+        },
+        "status": "complete",
+    }
+
+
+def mock_call_model_match(a_findings, b_findings, matches):
+    """Create a mock call_model that returns semantic match JSON."""
+    match_json = json.dumps({
+        "matches": [{"a_id": a, "b_id": b} for a, b in matches],
+        "a_only": [f["id"] for f in a_findings if f["id"] not in [m[0] for m in matches]],
+        "b_only": [f["id"] for f in b_findings if f["id"] not in [m[1] for m in matches]],
+    })
+    classify_json = json.dumps({
+        "classifications": [{"id": f["id"], "class": "material"} for f in a_findings + b_findings]
+    })
+    responses = iter([
+        {"response": match_json, "status": "completed", "time": 1, "model": "panel-model"},
+        # Cross-verification responses (accept everything)
+        {"response": json.dumps({"votes": [{"id": f["id"], "accept": True} for f in a_findings + b_findings]}),
+         "status": "completed", "time": 1, "model": "m1"},
+        {"response": json.dumps({"votes": [{"id": f["id"], "accept": True} for f in a_findings + b_findings]}),
+         "status": "completed", "time": 1, "model": "m2"},
+        {"response": json.dumps({"votes": [{"id": f["id"], "accept": True} for f in a_findings + b_findings]}),
+         "status": "completed", "time": 1, "model": "m3"},
+        {"response": json.dumps({"votes": [{"id": f["id"], "accept": True} for f in a_findings + b_findings]}),
+         "status": "completed", "time": 1, "model": "m4"},
+    ])
+    # Classification responses
+    classify_responses = [
+        {"response": classify_json, "status": "completed", "time": 1, "model": f"m{i}"}
+        for i in range(6)
+    ]
+
+    call_count = [0]
+    def mock_call(model, prompt):
+        call_count[0] += 1
+        try:
+            return next(responses)
+        except StopIteration:
+            return {"response": classify_json, "status": "completed", "time": 1, "model": model}
+
+    return mock_call, classify_responses
+
+
[REDACTED_EMAIL]("build_golden_set deprecated — replaced by _classify_and_build_golden (REQ-BENCH-318)")
+class TestBuildGoldenSet(unittest.TestCase):
+    """Test build_golden_set() with mocked API calls."""
+
+    @patch("run_unified.call_models_parallel")
+    @patch("run_unified.call_model")
+    def test_matched_findings_in_golden_set(self, mock_call, mock_parallel):
+        from run_unified import build_golden_set
+
+        a_findings = [
+            {"id": "expert_prop_F1", "description": "SQL injection", "category": "critical_bug"},
+        ]
+        b_findings = [
+            {"id": "expert_open_F1", "description": "SQL injection vulnerability", "category": "critical_bug"},
+        ]
+
+        # one panel model returns a match
+        mock_call.return_value = {"response": json.dumps({
+            "matches": [{"a_id": "expert_prop_F1", "b_id": "expert_open_F1"}],
+            "a_only": [], "b_only": []
+        }), "status": "completed", "time": 1, "model": "panel-model"}
+
+        # Classification vote
+        mock_parallel.return_value = [
+            {"response": json.dumps({"classifications": [{"id": "expert_prop_F1", "class": "material"}]}),
+             "status": "completed", "time": 1, "model": f"m{i}"}
+            for i in range(6)
+        ]
+
+        track_a = make_track(a_findings, "expert_prop")
+        track_b = make_track(b_findings, "expert_open")
+
+        result = build_golden_set(track_a, track_b, "test content")
+
+        self.assertEqual(len(result["findings"]), 1)
+        self.assertIn("expert_prop_F1", result["golden_ids"])
+        self.assertEqual(result["id_aliases"], {"expert_open_F1": "expert_prop_F1"})
+
+    @patch("run_unified.call_models_parallel")
+    @patch("run_unified.call_model")
+    def test_unmatched_go_to_cross_verification(self, mock_call, mock_parallel):
+        from run_unified import build_golden_set
+
+        a_findings = [
+            {"id": "expert_prop_F1", "description": "Auth bypass", "category": "critical_bug"},
+        ]
+        b_findings = [
+            {"id": "expert_open_F1", "description": "Race condition", "category": "critical_bug"},
+        ]
+
+        # No matches — different issues
+        call_count = [0]
+        def side_effect(model, prompt):
+            call_count[0] += 1
+            if call_count[0] == 1:  # Semantic matching
+                return {"response": json.dumps({
+                    "matches": [], "a_only": ["expert_prop_F1"], "b_only": ["expert_open_F1"]
+                }), "status": "completed", "time": 1, "model": "panel-model"}
+            return {"response": "", "status": "completed", "time": 1, "model": model}
+
+        mock_call.side_effect = side_effect
+
+        # Cross-verification: open models accept A's finding
+        mock_parallel.side_effect = [
+            # Cross-verification call for a_only
+            [{"response": json.dumps({"votes": [{"id": "expert_prop_F1", "accept": True}]}),
+              "status": "completed", "time": 1, "model": "m1"}],
+            # Cross-verification call for b_only
+            [{"response": json.dumps({"votes": [{"id": "expert_open_F1", "accept": True}]}),
+              "status": "completed", "time": 1, "model": f"m{i}"}
+             for i in range(4)],  # 3+ accepts needed
+            # Classification vote
+            [{"response": json.dumps({"classifications": [
+                {"id": "expert_prop_F1", "class": "material"},
+                {"id": "expert_open_F1", "class": "minor"},
+            ]}), "status": "completed", "time": 1, "model": f"m{i}"}
+             for i in range(6)],
+        ]
+
+        track_a = make_track(a_findings, "expert_prop")
+        track_b = make_track(b_findings, "expert_open")
+
+        result = build_golden_set(track_a, track_b, "test content")
+
+        # Both should be in golden set (cross-accepted)
+        self.assertEqual(len(result["findings"]), 2)
+        self.assertEqual(len(result["id_aliases"]), 0)  # No aliases since no matches
+
+    @patch("run_unified.call_models_parallel")
+    @patch("run_unified.call_model")
+    def test_empty_track_b(self, mock_call, mock_parallel):
+        from run_unified import build_golden_set
+
+        a_findings = [
+            {"id": "expert_prop_F1", "description": "Bug", "category": "critical_bug"},
+        ]
+
+        # Cross-verification: open models accept A's finding, then classification
+        mock_parallel.side_effect = [
+            # Cross-verification for a_only
+            [{"response": json.dumps({"votes": [{"id": "expert_prop_F1", "accept": True}]}),
+              "status": "completed", "time": 1, "model": "m1"}],
+            # Classification vote
+            [{"response": json.dumps({"classifications": [{"id": "expert_prop_F1", "class": "material"}]}),
+             "status": "completed", "time": 1, "model": f"m{i}"}
+            for i in range(6)],
+        ]
+
+        track_a = make_track(a_findings, "expert_prop")
+        track_b = make_track([], "expert_open")
+
+        result = build_golden_set(track_a, track_b, "test content")
+
+        self.assertEqual(len(result["findings"]), 1)
+        self.assertEqual(len(result["id_aliases"]), 0)
+
+
[REDACTED_EMAIL]("id_aliases deprecated — single expert track needs no cross-track aliasing (REQ-BENCH-318)")
+class TestDuplicateAliasHandling(unittest.TestCase):
+    """Test that duplicate semantic matches are rejected, not silently overwritten."""
+
+    @patch("run_unified.call_models_parallel")
+    @patch("run_unified.call_model")
+    def test_duplicate_b_id_rejected(self, mock_call, mock_parallel):
+        from run_unified import build_golden_set
+
+        a_findings = [
+            {"id": "expert_prop_F1", "description": "Bug A", "category": "critical_bug"},
+            {"id": "expert_prop_F2", "description": "Bug B", "category": "critical_bug"},
+        ]
+        b_findings = [
+            {"id": "expert_open_F1", "description": "Bug matching both", "category": "critical_bug"},
+        ]
+
+        # one panel model incorrectly maps both A findings to same B finding
+        mock_call.return_value = {"response": json.dumps({
+            "matches": [
+                {"a_id": "expert_prop_F1", "b_id": "expert_open_F1"},
+                {"a_id": "expert_prop_F2", "b_id": "expert_open_F1"},  # duplicate b_id
+            ],
+            "a_only": [], "b_only": []
+        }), "status": "completed", "time": 1, "model": "panel-model"}
+
+        mock_parallel.return_value = [
+            {"response": json.dumps({"classifications": [
+                {"id": "expert_prop_F1", "class": "material"},
+                {"id": "expert_prop_F2", "class": "material"},
+            ]}), "status": "completed", "time": 1, "model": f"m{i}"}
+            for i in range(6)
+        ]
+
+        track_a = make_track(a_findings, "expert_prop")
+        track_b = make_track(b_findings, "expert_open")
+
+        result = build_golden_set(track_a, track_b, "test content")
+
+        # First match accepted, second rejected (duplicate b_id)
+        self.assertEqual(len(result["id_aliases"]), 1)
+        self.assertEqual(result["id_aliases"]["expert_open_F1"], "expert_prop_F1")
+        # F2 should end up in cross-verification path since its match was rejected
+        self.assertIn("expert_prop_F1", result["golden_ids"])
+
+
[REDACTED_EMAIL]("id_aliases deprecated — single expert track needs no cross-track aliasing (REQ-BENCH-318)")
+class TestScoreTrackWithAliases(unittest.TestCase):
+    """Test score_track() calls real function with alias resolution."""
+
+    @patch("run_unified.call_model")
+    def test_b_side_debate_verdict_resolves_via_alias(self, mock_call):
+        """Real score_track() resolves B-side verdict IDs via id_aliases."""
+        from run_unified import score_track
+        import json
+
+        golden_set = {
+            "findings": [
+                {"id": "expert_prop_F1", "severity_weight": 10, "description": "Critical bug"},
+                {"id": "expert_prop_F2", "severity_weight": 1, "description": "Style issue"},
+            ],
+            "golden_ids": ["expert_prop_F1", "expert_prop_F2"],
+            "id_aliases": {"expert_open_F1": "expert_prop_F1"},
+            "weighted_total": 11,
+        }
+
+        # Track B with a model that voted VALID on expert_open_F1 in debate
+        track_data = {
+            "track_name": "expert_open",
+            "standalone": [
+                {"model": "alibaba-reviewer-model", "response": "Found SQL injection", "time": 1, "status": "completed"},
+            ],
+            "aggregation": {"findings": []},
+            "debate": {
+                "rounds": 2,
+                "final_confirmed": [],
+                "interim": [
+                    {"verdicts_by_finding": {
+                        "expert_open_F1": {"arguments": [
+                            {"model": "alibaba-reviewer-model", "conclusion": "VALID"}
+                        ]},
+                    }},
+                ],
+            },
+        }
+
+        # Mock one panel model scoring calls — return matched IDs
+        mock_call.return_value = {
+            "response": json.dumps({"matched_ids": ["expert_prop_F1"]}),
+            "status": "completed", "time": 1, "model": "panel-model",
+        }
+
+        scores = score_track(track_data, golden_set, "test content")
+
+        # one panel model should get credit for expert_prop_F1 via alias resolution
+        qwen_scores = scores.get("alibaba-reviewer-model", {})
+        self.assertGreater(qwen_scores.get("debate_pct", 0), 0)
+        self.assertIn("expert_prop_F1", qwen_scores.get("debate_ids", []))
+
+    @patch("run_unified.call_model")
+    def test_a_side_verdict_no_alias_needed(self, mock_call):
+        """Real score_track() — Track A model uses A-side IDs directly."""
+        from run_unified import score_track
+        import json
+
+        golden_set = {
+            "findings": [
+                {"id": "expert_prop_F1", "severity_weight": 10, "description": "Bug"},
+            ],
+            "golden_ids": ["expert_prop_F1"],
+            "id_aliases": {},
+            "weighted_total": 10,
+        }
+
+        track_data = {
+            "track_name": "expert_prop",
+            "standalone": [
+                {"model": "llm", "response": "Found bug", "time": 1, "status": "completed"},
+            ],
+            "aggregation": {"findings": []},
+            "debate": {
+                "rounds": 2,
+                "final_confirmed": [],
+                "interim": [
+                    {"verdicts_by_finding": {
+                        "expert_prop_F1": {"arguments": [
+                            {"model": "llm", "conclusion": "VALID"}
+                        ]},
+                    }},
+                ],
+            },
+        }
+
+        mock_call.return_value = {
+            "response": json.dumps({"matched_ids": ["expert_prop_F1"]}),
+            "status": "completed", "time": 1, "model": "panel-model",
+        }
+
+        scores = score_track(track_data, golden_set, "test content")
+        gpt_scores = scores.get("llm", {})
+        self.assertEqual(gpt_scores.get("debate_pct", 0), 100.0)
+
+    @patch("run_unified.call_model")
+    def test_invalid_b_id_from_gemini_no_match(self, mock_call):
+        """TC-06: Invalid b_id from one panel model rejected — real build_golden_set."""
+        from run_unified import build_golden_set
+        import json
+
+        a_findings = [{"id": "expert_prop_F1", "description": "Bug", "category": "critical_bug"}]
+        b_findings = [{"id": "expert_open_F1", "description": "Different bug", "category": "critical_bug"}]
+
+        call_count = [0]
+        def side_effect(model, prompt):
+            call_count[0] += 1
+            if call_count[0] == 1:
+                # one panel model returns match with INVALID b_id
+                return {"response": json.dumps({
+                    "matches": [{"a_id": "expert_prop_F1", "b_id": "expert_open_FAKE"}],
+                    "a_only": [], "b_only": ["expert_open_F1"]
+                }), "status": "completed", "time": 1, "model": "panel-model"}
+            return {"response": "", "status": "completed", "time": 1, "model": model}
+
+        mock_call.side_effect = side_effect
+
+        track_a = make_track(a_findings, "expert_prop")
+        track_b = make_track(b_findings, "expert_open")
+
+        with patch("run_unified.call_models_parallel") as mock_parallel:
+            # Cross-verification accepts both
+            mock_parallel.side_effect = [
+                [{"response": json.dumps({"votes": [{"id": "expert_prop_F1", "accept": True}]}),
+                  "status": "completed", "time": 1, "model": "m1"}],
+                [{"response": json.dumps({"votes": [{"id": "expert_open_F1", "accept": True}]}),
+                  "status": "completed", "time": 1, "model": f"m{i}"} for i in range(4)],
+                [{"response": json.dumps({"classifications": [
+                    {"id": "expert_prop_F1", "class": "material"},
+                    {"id": "expert_open_F1", "class": "minor"}
+                ]}), "status": "completed", "time": 1, "model": f"m{i}"} for i in range(6)],
+            ]
+            result = build_golden_set(track_a, track_b, "test content")
+
+        # Invalid b_id rejected — no aliases created
+        self.assertEqual(len(result["id_aliases"]), 0)
+        # Both findings should still be in golden set via cross-verification
+        self.assertEqual(len(result["findings"]), 2)
+
+
+class TestResolveId(unittest.TestCase):
+    """Test resolve_id() helper for prefix/unprefix matching."""
+
+    def test_exact_match(self):
+        from run_unified import resolve_id
+        known = {"expert_prop_F1", "expert_prop_F2"}
+        self.assertEqual(resolve_id("expert_prop_F1", known), "expert_prop_F1")
+
+    def test_unprefixed_resolves(self):
+        from run_unified import resolve_id
+        known = {"expert_prop_F1", "expert_prop_F2"}
+        self.assertEqual(resolve_id("F1", known), "expert_prop_F1")
+
+    def test_ambiguous_returns_none(self):
+        from run_unified import resolve_id
+        known = {"expert_prop_F1", "expert_open_F1"}
+        self.assertIsNone(resolve_id("F1", known))
+
+    def test_no_match_returns_none(self):
+        from run_unified import resolve_id
+        known = {"expert_prop_F1"}
+        self.assertIsNone(resolve_id("F99", known))
+
+    def test_empty_known_ids(self):
+        from run_unified import resolve_id
+        self.assertIsNone(resolve_id("F1", set()))
+
+    def test_empty_fid(self):
+        from run_unified import resolve_id
+        known = {"expert_prop_F1"}
+        self.assertIsNone(resolve_id("", known))
+
+
[REDACTED_EMAIL]("build_golden_set deprecated — replaced by _classify_and_build_golden (REQ-BENCH-318)")
+class TestZeroVoteClassification(unittest.TestCase):
+    """Test that zero votes defaults to minor, not material."""
+
+    @patch("run_unified.call_models_parallel")
+    @patch("run_unified.call_model")
+    def test_zero_votes_defaults_minor(self, mock_call, mock_parallel):
+        from run_unified import build_golden_set
+
+        a_findings = [
+            {"id": "expert_prop_F1", "description": "Bug", "category": "critical_bug"},
+        ]
+
+        # Classification returns empty — no votes parsed
+        mock_parallel.side_effect = [
+            # Cross-verification
+            [{"response": json.dumps({"votes": [{"id": "expert_prop_F1", "accept": True}]}),
+              "status": "completed", "time": 1, "model": "m1"}],
+            # Classification — returns garbage, no parseable votes
+            [{"response": "invalid json", "status": "completed", "time": 1, "model": f"m{i}"}
+             for i in range(6)],
+        ]
+
+        track_a = make_track(a_findings, "expert_prop")
+        track_b = make_track([], "expert_open")
+
+        result = build_golden_set(track_a, track_b, "test content")
+
+        # Zero votes → minor (not material)
+        self.assertEqual(len(result["findings"]), 1)
+        self.assertEqual(result["findings"][0]["severity"], "minor")
+        self.assertEqual(result["findings"][0]["severity_weight"], 1)
+
+
+class TestClassifyAndBuildGolden(unittest.TestCase):
+    """Tests for _classify_and_build_golden (new simplified golden set builder)."""
+
+    @patch("run_unified.call_models_parallel")
+    def test_basic_classification(self, mock_parallel):
+        """Confirmed findings get classified as Material or Minor."""
+        from run_unified import _classify_and_build_golden
+
+        findings = [
+            {"id": "F1", "description": "Critical security flaw", "found_by": ["m1"]},
+            {"id": "F2", "description": "Minor style issue", "found_by": ["m2"]},
+        ]
+        track = make_track(findings, "expert")
+
+        # Classification responses — 6 models vote
+        mock_parallel.return_value = [
+            {"response": json.dumps({"classifications": [
+                {"id": "F1", "class": "material"}, {"id": "F2", "class": "minor"}
+            ]}), "status": "completed", "time": 1, "model": f"m{i}"}
+            for i in range(6)
+        ]
+
+        result = _classify_and_build_golden(findings, track, "test content")
+
+        self.assertEqual(len(result["findings"]), 2)
+        f1 = next(f for f in result["findings"] if f["id"] == "F1")
+        f2 = next(f for f in result["findings"] if f["id"] == "F2")
+        self.assertEqual(f1["severity"], "material")
+        self.assertEqual(f1["severity_weight"], 10)
+        self.assertEqual(f2["severity"], "minor")
+        self.assertEqual(f2["severity_weight"], 1)
+        self.assertEqual(result["weighted_total"], 11)
+
+    @patch("run_unified.call_models_parallel")
+    def test_empty_findings(self, mock_parallel):
+        """Empty findings list returns valid empty golden set."""
+        from run_unified import _classify_and_build_golden
+
+        result = _classify_and_build_golden([], make_track([], "expert"), "test")
+
+        self.assertEqual(len(result["findings"]), 0)
+        self.assertEqual(result["weighted_total"], 1)  # floor of 1
+
+    @patch("run_unified.call_models_parallel")
+    def test_zero_votes_default_minor(self, mock_parallel):
+        """Findings with no parseable classification votes default to Minor."""
+        from run_unified import _classify_and_build_golden
+
+        findings = [{"id": "F1", "description": "test", "found_by": ["m1"]}]
+        mock_parallel.return_value = [
+            {"response": "garbage", "status": "completed", "time": 1, "model": "m1"}
+            for _ in range(6)
+        ]
+
+        result = _classify_and_build_golden(findings, make_track(findings, "expert"), "test")
+
+        self.assertEqual(result["findings"][0]["severity"], "minor")
+        self.assertEqual(result["findings"][0]["severity_weight"], 1)
+
+
+class TestScoreByIdsDebateStyle(unittest.TestCase):
+    """Tests for debate-style score_by_ids (one panel model+one panel model argue, one panel model moderates)."""
+
+    def _make_golden(self, findings):
+        return {
+            "findings": findings,
+            "golden_ids": [f["id"] for f in findings],
+            "weighted_total": sum(f.get("severity_weight", 1) for f in findings) or 1,
+        }
+
+    @patch("run_unified.call_model")
+    def test_moderator_confirms_findings(self, mock_call):
+        """Moderator PRESENT verdict → finding counted."""
+        from run_unified import score_track
+
+        findings = [
+            {"id": "F1", "description": "bug", "severity_weight": 10},
+            {"id": "F2", "description": "style", "severity_weight": 1},
+        ]
+        golden = self._make_golden(findings)
+        track = {
+            "track_name": "expert",
+            "standalone": [{"model": "test-model", "response": "found both bugs",
+                           "status": "completed", "time": 1}],
+            "aggregation": {"per_model": {}},
+            "debate": {"interim": []},
+        }
+
+        # Both scorers agree PRESENT on both — no moderator needed
+        mock_call.side_effect = [
+            {"response": json.dumps({"arguments": [
+                {"id": "F1", "for": "clearly mentioned", "against": "none", "verdict": "PRESENT"},
+                {"id": "F2", "for": "mentioned", "against": "none", "verdict": "PRESENT"},
+            ]})},
+            {"response": json.dumps({"arguments": [
+                {"id": "F1", "for": "yes present", "against": "none", "verdict": "PRESENT"},
+                {"id": "F2", "for": "yes present", "against": "none", "verdict": "PRESENT"},
+            ]})},
+        ]
+
+        scores = score_track(track, golden, "test content")
+        self.assertEqual(scores["test-model"]["standalone_pct"], 100.0)
+        self.assertEqual(len(scores["test-model"]["standalone_ids"]), 2)
+
+    @patch("run_unified.call_model")
+    def test_moderator_rejects_findings(self, mock_call):
+        """Moderator ABSENT verdict → finding not counted."""
+        from run_unified import score_track
+
+        findings = [{"id": "F1", "description": "bug", "severity_weight": 10}]
+        golden = self._make_golden(findings)
+        track = {
+            "track_name": "expert",
+            "standalone": [{"model": "test-model", "response": "nothing relevant",
+                           "status": "completed", "time": 1}],
+            "aggregation": {"per_model": {}},
+            "debate": {"interim": []},
+        }
+
+        # Both scorers agree ABSENT — no moderator needed
+        mock_call.side_effect = [
+            {"response": json.dumps({"arguments": [
+                {"id": "F1", "for": "not really", "against": "not mentioned", "verdict": "ABSENT"},
+            ]})},
+            {"response": json.dumps({"arguments": [
+                {"id": "F1", "for": "no evidence", "against": "completely absent", "verdict": "ABSENT"},
+            ]})},
+        ]
+
+        scores = score_track(track, golden, "test content")
+        self.assertEqual(scores["test-model"]["standalone_pct"], 0.0)
+
+    @patch("run_unified.call_model")
+    def test_scorer_failure_returns_none(self, mock_call):
+        """Both scorers returning garbage → None (not 0%)."""
+        from run_unified import score_track
+
+        findings = [{"id": "F1", "description": "bug", "severity_weight": 10}]
+        golden = self._make_golden(findings)
+        track = {
+            "track_name": "expert",
+            "standalone": [{"model": "test-model", "response": "some response",
+                           "status": "completed", "time": 1}],
+            "aggregation": {"per_model": {}},
+            "debate": {"interim": []},
+        }
+
+        mock_call.side_effect = [
+            {"response": "unparseable garbage"},
+            {"response": "also garbage"},
+        ]
+
+        scores = score_track(track, golden, "test content")
+        self.assertIsNone(scores["test-model"]["standalone_pct"])
+
+
+    @patch("run_unified.call_model")
+    def test_no_aggregation_text_returns_none(self, mock_call):
+        """Model with no aggregation response gets None for agg score."""
+        from run_unified import score_track
+
+        findings = [{"id": "F1", "description": "bug", "severity_weight": 10}]
+        golden = self._make_golden(findings)
+        track = {
+            "track_name": "expert",
+            "standalone": [{"model": "test-model", "response": "found the bug",
+                           "status": "completed", "time": 1}],
+            "aggregation": {"per_model": {}},  # empty — no aggregation text
+            "debate": {"interim": []},
+        }
+
+        # Both agree PRESENT — no moderator
+        mock_call.side_effect = [
+            {"response": json.dumps({"arguments": [
+                {"id": "F1", "for": "present", "against": "none", "verdict": "PRESENT"}]})},
+            {"response": json.dumps({"arguments": [
+                {"id": "F1", "for": "present", "against": "none", "verdict": "PRESENT"}]})},
+        ]
+
+        scores = score_track(track, golden, "test content")
+        self.assertIsNone(scores["test-model"]["aggregation_pct"])
+        self.assertEqual(scores["test-model"]["aggregation_ids"], [])
+
+    @patch("run_unified.call_model")
+    def test_scorer_exception_returns_none(self, mock_call):
+        """Scorer raising exception → treated as failure, returns None."""
+        from run_unified import score_track
+
+        findings = [{"id": "F1", "description": "bug", "severity_weight": 10}]
+        golden = self._make_golden(findings)
+        track = {
+            "track_name": "expert",
+            "standalone": [{"model": "test-model", "response": "some response",
+                           "status": "completed", "time": 1}],
+            "aggregation": {"per_model": {}},
+            "debate": {"interim": []},
+        }
+
+        # Both scorers raise exceptions
+        mock_call.side_effect = [
+            Exception("API timeout"),
+            Exception("Connection refused"),
+        ]
+
+        scores = score_track(track, golden, "test content")
+        self.assertIsNone(scores["test-model"]["standalone_pct"])
+
+    @patch("run_unified.call_model")
+    def test_moderator_only_sees_disputed(self, mock_call):
+        """When scorers agree on F1 but disagree on F2, moderator only sees F2."""
+        from run_unified import score_track
+
+        findings = [
+            {"id": "F1", "description": "agreed finding", "severity_weight": 10},
+            {"id": "F2", "description": "disputed finding", "severity_weight": 10},
+        ]
+        golden = self._make_golden(findings)
+        track = {
+            "track_name": "expert",
+            "standalone": [{"model": "test-model", "response": "some analysis",
+                           "status": "completed", "time": 1}],
+            "aggregation": {"per_model": {}},
+            "debate": {"interim": []},
+        }
+
+        call_log = []
+        def tracking_call(model, prompt):
+            call_log.append({"model": model, "prompt": prompt})
+            if model == "reviewer-model":  # moderator
+                # Moderator should only see F2 (disputed), not F1 (agreed)
+                disputed_section = prompt.split("DISPUTED FINDINGS:")[-1] if "DISPUTED" in prompt else ""
+                # F2 args should be present, F1 args should not
+                assert "\nF2:" in disputed_section, "Moderator should see F2 (disputed)"
+                assert "\nF1:" not in disputed_section, "Moderator should NOT see F1 (agreed)"
+                return {"response": json.dumps({"verdicts": [
+                    {"id": "F2", "verdict": "PRESENT"}]})}
+            elif model == "google-reviewer-model":
+                return {"response": json.dumps({"arguments": [
+                    {"id": "F1", "for": "present", "against": "none", "verdict": "PRESENT"},
+                    {"id": "F2", "for": "maybe", "against": "unclear", "verdict": "PRESENT"},
+                ]})}
+            else:  # panel-model-b
+                return {"response": json.dumps({"arguments": [
+                    {"id": "F1", "for": "present", "against": "none", "verdict": "PRESENT"},
+                    {"id": "F2", "for": "weak", "against": "not found", "verdict": "ABSENT"},
+                ]})}
+
+        mock_call.side_effect = tracking_call
+
+        scores = score_track(track, golden, "test content")
+        # F1 agreed (both PRESENT), F2 disputed → moderator says PRESENT
+        self.assertEqual(scores["test-model"]["standalone_pct"], 100.0)
+        # Moderator was called (3 total calls: scorer A, scorer B, moderator)
+        self.assertEqual(len(call_log), 3)
+        self.assertEqual(call_log[2]["model"], "reviewer-model")
+
+    @patch("run_unified.call_model")
+    def test_empty_golden_set_returns_zero(self, mock_call):
+        """Empty golden set → 0% score, no scorer calls."""
+        from run_unified import score_track
+
+        golden = self._make_golden([])
+        track = {
+            "track_name": "expert",
+            "standalone": [{"model": "test-model", "response": "some response",
+                           "status": "completed", "time": 1}],
+            "aggregation": {"per_model": {}},
+            "debate": {"interim": []},
+        }
+
+        scores = score_track(track, golden, "test content")
+        self.assertEqual(scores["test-model"]["standalone_pct"], 0.0)
+        mock_call.assert_not_called()
+
+    @patch("run_unified.call_model")
+    def test_scorers_disagree_moderator_resolves(self, mock_call):
+        """When scorers argue differently, moderator makes final call."""
+        from run_unified import score_track
+
+        findings = [
+            {"id": "F1", "description": "real bug", "severity_weight": 10},
+            {"id": "F2", "description": "not real", "severity_weight": 1},
+        ]
+        golden = self._make_golden(findings)
+        track = {
+            "track_name": "expert",
+            "standalone": [{"model": "test-model", "response": "mentions F1 only",
+                           "status": "completed", "time": 1}],
+            "aggregation": {"per_model": {}},
+            "debate": {"interim": []},
+        }
+
+        # Scorer A: both PRESENT. Scorer B: F1 PRESENT, F2 ABSENT.
+        # F1 agreed (both PRESENT). F2 disputed → moderator decides ABSENT.
+        mock_call.side_effect = [
+            {"response": json.dumps({"arguments": [
+                {"id": "F1", "for": "clearly present", "against": "none", "verdict": "PRESENT"},
+                {"id": "F2", "for": "somewhat present", "against": "weak", "verdict": "PRESENT"},
+            ]})},
+            {"response": json.dumps({"arguments": [
+                {"id": "F1", "for": "definitely present", "against": "none", "verdict": "PRESENT"},
+                {"id": "F2", "for": "not really", "against": "not mentioned", "verdict": "ABSENT"},
+            ]})},
+            # Moderator only sees F2 (disputed) and rejects it
+            {"response": json.dumps({"verdicts": [
+                {"id": "F2", "verdict": "ABSENT"},
+            ]})},
+        ]
+
+        scores = score_track(track, golden, "test content")
+        # F1 (weight 10) present, F2 (weight 1) absent → 10/11 = 90.9%
+        self.assertAlmostEqual(scores["test-model"]["standalone_pct"], 90.9, places=1)
+        self.assertIn("F1", scores["test-model"]["standalone_ids"])
+        self.assertNotIn("F2", scores["test-model"]["standalone_ids"])
+
+
+if __name__ == "__main__":
+    unittest.main()
````

## Individual Responses

### reviewer-model (15.02s)
Yes: I’d flag **one CRITICAL issue** that is sufficient to stop the pipeline before collecting data.

## CRITICAL: scoring can deadlock / massively stall due to nested thread pools and provider fan-out

The new `score_track()` introduces this inside `score_by_ids()`:

```python
with ThreadPoolExecutor(max_workers=2) as scorer_pool:
    scorer_futures["A"] = scorer_pool.submit(call_model, SCORER_A, argue_prompt)
    scorer_futures["B"] = scorer_pool.submit(call_model, SCORER_B, argue_prompt)
```

That is being called **inside** the pipeline which already uses a global executor:

```python
POOL = ThreadPoolExecutor(max_workers=16)
```

and runs lots of model calls in parallel elsewhere. Even though the comment says “no nested pools,” this patch reintroduces nested pools during the hottest path: scoring every model, for multiple stages.

### Why this is pipeline-stopping
This isn’t just style. It can break data collection in practice:

- `process_data_point()` runs 2 tracks.
- Each track scores multiple models.
- For each model, `score_by_ids()` may do:
  - 2 parallel scorer calls
  - plus 1 moderator call
- And it does that for:
  - standalone
  - aggregation
  - potentially repeated across 11 models

That creates a large burst of concurrent outbound API calls from ad hoc pools, outside the intended global concurrency control.

If `call_model()` itself shares HTTP/session/rate-limit behavior with the rest of the system, this can lead to:
- request storms,
- throttling cascades,
- hangs/stalls,
- non-deterministic partial scoring,
- biased data where failures show up as `None` rather than comparable scores.

This is especially bad because the patch explicitly changed failures from `0` to `None`, so a concurrency-induced scoring collapse won’t look like a bad model; it will look like missing data. That corrupts service-eval collection.

### Why I think this is genuinely critical
Because this code is now on the **measurement path**, not an optional feature path. If scoring becomes unstable, the dataset you collect is not trustworthy. You won’t just get a crash; worse, you may get silently incomplete service-eval rows.

The old architecture at least had a single shared pool. This patch violates that design in the most expensive section.

## What I would do before proceeding
At minimum, do one of these before collecting data:

1. **Remove the inner `ThreadPoolExecutor`** and call the two scorers sequentially.
   - Slower, but safe and deterministic.

2. Better: route those scorer calls through the existing global `POOL` / shared orchestration layer.

3. Add a hard timeout around scoring calls so a single scorer/moderator stall cannot block the datapoint indefinitely.

---

## Things I would *not* call critical
There are several weaker issues, but I would not stop the pipeline for them alone:

- `api_key=_rb.API_KEY` vs imported `API_KEY`: odd, but probably fine if `run_benchmark` initializes module state.
- Debate round 2 filtering with `if mn not in line`: brittle, but more quality-risk than stop-the-line.
- `bestName()` in UI using `Math.round` on possibly null fields: UI bug, not pipeline-critical.
- Deprecated tests left skipped while new tests are added: not great, but not a release blocker by itself.

## Bottom line
**Stop the pipeline.**
The nested executor introduced in `score_track()` is a **critical operational/data-integrity risk** for service-eval collection.

### moderator-model (20.7s)
**CRITICAL ISSUES (stop the pipeline)**

### 1. Frontend will break on null scores (highest priority)
The new scoring system intentionally returns `None` (→ `null` in JSON) in two cases:
- Model API failure (`status != "completed"`)
- Scorer failure (both one panel model/one panel model return unparseable output → "scorer failure, not model failure")

`Overview.jsx` does:
```js
.sort((a, b) => b.aggregation_pct - a.aggregation_pct)
Math.round(m[field])
```
and `bestName()` assumes numeric values. `null - null` is `NaN`. JS sort becomes unstable, "Best Proprietary Aggregator" can pick wrong model or tie incorrectly, and `Math.round(null) === 0` creates phantom ties.

This is **guaranteed** to produce misleading leaderboard data once any model flakes. Fix before collecting real data.

### 2. ID resolution is duplicated and fragile
Both `debate.py:264-272` and `run_unified.py:resolve_id()` contain nearly identical "try exact, then `endswith(f"_{fid}")`" logic, with slightly different warning messages and edge-case handling.

The new `model_standalone_ids` path in `db_writer.py` relies on `finding_id_map` being complete. If a model returns an ID that is ambiguous or the prefixing logic in `run_track()` fails for any debate-generated finding (`track_D1-*`), you will get:
- Silent drops (`ON CONFLICT DO NOTHING`)
- Wrong `model_findings` links
- Inconsistent golden set ↔ standalone matching

This is the exact class of bug the old `id_aliases` machinery was trying to solve. Now it's spread across three files with no single source of truth.

**Recommendation:** Extract `resolve_finding_id()` to a shared utility and add strict validation that every ID in `model_standalone_ids` resolves to exactly one DB finding. Fail the run if not.

### Non-critical but worth noting
- The debate round-2 per-model prompt filtering (`if mn not in line`) is a hack. Model names appear in headers, not just arguments. Risk of over-filtering is real but probably not fatal.
- Golden set methodology changed radically (no more cross-validation between proprietary and open experts). This is a *feature* of the ticket, not a bug, but it makes the "golden" label much weaker. The new Material/Minor classification vote is reasonable.
- Test file is messy (many skipped tests with deprecation messages). Acceptable for internal tooling but signals the refactor was large.

### Overall assessment
The *intent* of REQ-BENCH-318 is sound: simplify tracks, make scoring more intelligent via debate-style argument, stop pretending open/expert split was magically better. The new scorer (one panel model+one panel model argue, one panel model moderates) is genuinely clever.

However, the combination of **null scores + duplicated ID logic** is enough to corrupt both the database and the displayed results. Fix those two things before turning this on for real data collection. Do not merge more data until the frontend safely excludes `null` scores from "best" calculations and the ID resolution is centralized and hardened.

### llm (44.56s)
# Post-Merge Review: REQ-BENCH-318

## CRITICAL Issues — Stop Pipeline

### 1. `score_by_ids` returns `None` but callers don't handle it

**File:** `run_unified.py`, around line 370+

`score_by_ids` now returns `None, []` when both scorers fail:

```python
if not args_by_finding:
    log.warning(f"      Scoring: both scorers returned no parseable arguments — "
                f"returning None (scorer failure, not model failure)")
    return None, []
```

But downstream, the return value is unpacked and used in arithmetic:

```python
std_pct, std_ids = score_by_ids(r["response"])
```

Then later:

```python
deb_w = sum(...)
deb_pct = round(100.0 * deb_w / weighted_total, 1)
```

And in `db_writer.py`, these scores are passed directly to SQL. The `None` propagates into:
- The weighted scoring arithmetic (`100.0 * None / ...` → `TypeError`)
- `write_to_cloud_sql` where `model_standalone_scores` values get compared/inserted

The test `test_scorer_failure_returns_none` validates that `None` is *returned*, but there's no test or code showing the `process_data_point` → `write_to_cloud_sql` path handles `None` scores without crashing. **If any scorer pair fails during a real run, the entire data point likely crashes after scoring completes.**

**Severity: CRITICAL.** This will surface as soon as any model's scorer calls both return unparseable output or timeout, which is a normal operational scenario. The pipeline will crash partway through, leaving partial state.

---

### 2. `_call_model` is not defined/imported — `debate.py` round 2+ will crash

**File:** `debate.py`, line ~230

```python
resp = _call_model(mn, model_prompt, api_key=api_key)
```

The original code calls `_call_model_group`. The new per-model path calls `_call_model`, but I see no definition or import of `_call_model` in the diff. The existing function visible in the diff is `_call_model_group`. If `_call_model` doesn't exist elsewhere in the module (not shown in diff), **every debate that reaches round 2 will crash with `NameError`.**

**Severity: CRITICAL.** Round 1 works (uses `_call_model_group`), but round 2 always takes the new branch. Every multi-round debate will fail. Since expert track debates are the source of the golden set, this means **no golden set gets built**, which means **no scoring happens**, which means **no data is collected**.

---

## HIGH Issues — Fix Before Next Batch

### 3. Light track runs debate with `threshold=None`

```python
("light", LIGHT_MODELS, "light", None),  # no threshold — golden set comes from expert only
```

In `run_track`, `threshold` is passed to `debate_mod.run_debate(convergence_threshold=threshold)`. If `run_debate` doesn't explicitly handle `None` for this parameter (not visible in diff), this either crashes or produces undefined convergence behavior. Even if it doesn't crash, running a full debate on 5 light models with no convergence criterion wastes API spend for data that's never used in golden set construction.

### 4. Nested `ThreadPoolExecutor` inside global pool tasks

`score_by_ids` creates a nested `ThreadPoolExecutor(max_workers=2)` for scorer parallelism. But `score_by_ids` is called from within `score_track`, which is called from the main thread *after* tracks complete. However, if this ever runs inside a pool task, you get nested pool deadlock — the same pattern the code comments explicitly warn about. Currently safe but fragile.

### 5. Finding ID prefix check is subtly wrong across debate boundary

Debate findings get prefixed *after* `run_debate` returns:
```python
for f in debate_result.get("final_confirmed", []):
    if f.get("id") and not f["id"].startswith(f"{track_name}_"):
        f["id"] = f"{track_name}_{f['id']}"
```

But inside `run_debate`, the `per_finding_votes` keys use unprefixed IDs. The fuzzy fallback match (`k.endswith(f"_{fid}")`) in debate.py will never trigger during debate because IDs aren't prefixed yet. This is actually fine — but the *same* fuzzy match logic is duplicated in `debate.py` AND `run_unified.py` (`resolve_id`), creating maintenance risk.

---

## Recommendation

**Stop the pipeline.** Issues #1 and #2 are independently pipeline-breaking under normal operating conditions. #2 in particular means no useful data will be collected — debates will crash at round 2, producing no golden set and therefore no scores.

### reviewer-model (98.08s)
This commit introduces a **CRITICAL logic flaw in how debate scores are calculated for the `light` track**, which will result in all light models receiving a **0% debate score**. You must stop the pipeline and fix this before collecting data, or your debate metrics for half your models will be invalid.

### The Issue: Missing Cross-Track Semantic Mapping
In `run_unified.py`, the pipeline now runs two tracks (`expert` and `light`). 
1. The `expert` track generates findings (e.g., `expert_F1`), debates them, and these become the `golden_set`. Thus, `baseline_ids` are `{"expert_F1", "expert_F2", ...}`.
2. The `light` track extracts its *own* findings from the light models, prefixes them (e.g., `light_F1`), and debates them.
3. When `score_track` evaluates the `light` track's debate performance, it looks at the interim debate votes to see which models voted `VALID` on the golden findings. 

Here is the broken logic in `score_track`:
```python
resolved_fid = resolve_id(fid, baseline_ids) or fid
if "VALID" in verdict and "INVALID" not in verdict:
    deb_valid.add(resolved_fid)
...
deb_matched = list(deb_valid & baseline_ids)
```
Because `fid` is `light_F1` and `baseline_ids` contains

### reviewer-model (112.4s)
STOP THE PIPELINE. Do not collect data with this merge.

While the architectural simplification (4 tracks → 2 tracks) reduces operational overhead, it introduces critical code defects that will crash the pipeline and corrupt the dashboard, alongside strategic degradations to the service-eval's scientific validity.

Here are the specific issues warranting an immediate halt:

### 1. CRITICAL: `NameError` in Scoring Logic (`run_unified.py`)
**The pipeline will crash on the first data point.**
In `src/pipeline/run_unified.py`, the `score_track` function defines a nested closure `score_by_ids`. Inside this closure (line 339), the variable `weighted_total` is used:
```python
return round(100.0 * w / weighted_total, 1), matched
```
However, `weighted_total` is **never defined** within the scope of `score_track`. It exists in `golden_set["weighted_total"]`, but the local variable assignment is missing in the refactored code.
*   **Impact:** `NameError: name 'weighted_total' is not defined`. The scoring step fails immediately. No results are written to the DB.
*   **Fix:** Add `weighted_total = golden_set["weighted_total"]` at the start of `score_track`.

### 2. CRITICAL: UI Dashboard Crash via `NaN` Propagation (`Overview.jsx` & `run_unified.py`)
**The results dashboard will break if any model scoring fails.**
The new scoring logic in `run_unified.py` explicitly returns `None` for scores when the scorer models fail or return unparseable JSON (e.g., line 350, 420):
```python
scores[model_name] = {"standalone_pct": None, ...}
```
These `None` values are passed to the DB and subsequently served to the frontend. In `src/web/ui/src/pages/Overview.jsx` (line 199), the sorting logic performs arithmetic on these values:
```javascript
.sort((a, b) => b.aggregation_pct - a.aggregation_pct)
```
*   **Impact:** In JavaScript, `null - null` equals `NaN`. Passing `NaN` to `Array.sort` comparators causes undefined behavior (often freezing the UI or destroying sort order). The "Best Aggregator" cards will fail to render correctly.
*   **Fix:** Coerce `None` scores to `0.0` (or `-1.0` to indicate failure) in `run_unified.py` before saving. Ensure the UI handles nulls defensively.

### 3. STRATEGIC: Degradation of Golden Set Validity
**Disagree with Conventional Wisdom:** Simplification here sacrifices robustness.
The merge removes the cross-verification step between Proprietary and Open Source tracks (`build_golden_set` old logic). Previously, a finding unique to one provider family had to be validated by the other family to enter the Golden Set.
*   **Risk:** The new logic relies solely on consensus within the "Expert" track (4/6 models). If the 6 expert models share a systemic training bias or hallucination pattern (common in same-generation models), the Golden Set will codify this bias as "Ground Truth."
*   **Consequence:** The service-eval stops measuring objective code quality and starts measuring "agreement with the majority." This invalidates the service-eval's primary value proposition.
*   **Recommendation:** Reintroduce a cross-family verification step (e.g., Expert findings must be validated by at least one Light model from a different provider family) before finalizing the Golden Set.

### 4. OPERATIONAL: API Cost & Latency Explosion
**The new scoring mechanism is unsustainable.**
The `score_by_ids` function implements a "debate-style" scorer (one panel model + one panel model argue, one panel model moderates) for *every* model response being evaluated.
*   **Math:** 11 Models × 2 Metrics (Standalone + Aggregation) × 2 Scorers = **44 API calls per data point** just for scoring, excluding the actual service-eval runs.
*   **Impact:** This triples the API cost per service-eval run and significantly increases latency. It also increases the surface area for rate-limit failures, which triggers the `None` score bug mentioned in #2.
*   **Recommendation:** Revert to a single-call evaluator (e.g., one panel model extracts matches) or use embedding-based semantic similarity. Using a multi-model debate to *score* a service-eval is over-engineering that introduces more variance than it resolves.

### 5. HIGH RISK: Fragile ID Resolution (`run_unified.py` & `debate.py`)
**Data integrity relies on brittle string matching.**
The `resolve_id` function (line 66) and similar logic in `debate.py` rely on suffix matching (`k.endswith(f"_{fid}")`) to map model outputs (e.g., "F1") to internal IDs (e.g., "expert_F1").
*   **Risk:** If a model outputs an ID that ambiguously matches multiple prefixes (e.g., "F1" matches both "expert_F1" and "light_F1"), the code logs a warning and drops the finding (`return None`).
*   **Consequence:** Valid findings are silently discarded, artificially lowering model scores. This creates noise in the data that is hard to debug post-collection.
*   **Fix:** Enforce strict ID formatting in the system prompts (e.g., "You MUST use the ID exactly as shown: expert_F1") rather than trying to fix it programmatically downstream.

### Summary of Actions
1.  **Revert Merge:** Do not collect data until these are fixed.
2.  **Fix `NameError`:** Define `weighted_total` in `score_track`.
3.  **Fix Data Types:** Ensure scores are never `None` before DB write or UI render.
4.  **Re-evaluate Golden Set:** Restore cross-family verification to ensure service-eval validity.
5.  **Simplify Scorer:** Replace the debate-style scorer with a single-pass evaluator to control costs and latency.

### reviewer-model (149.37s)
 **CRITICAL ISSUE 1: Fragile string filtering in Round 2+ debate destroys argument context**
The Round 2+ debate logic filters `previous_arguments` using `if mn not in line` (line ~224 in debate.py). This is a naive substring match that will:
- Filter out arguments **from** other models if the model name appears in the argument text (e.g., "Provider A claims X" when filtering for model "reviewer-model")
- Fail to filter correctly if model names are substrings of each other (e.g., "reviewer-model" vs "reviewer-model-mini")
- **Impact:** Debate votes will be cast on incomplete or corrupted context, invalidating the consensus mechanism. Models will see partial arguments or miss rebuttals entirely.

**CRITICAL ISSUE 2: ID resolution gaps cause silent data loss in debate votes**
The fallback logic for finding IDs (lines ~264-272 in debate.py and `resolve_id()` in run_unified.py) assumes IDs are prefixed with `{track}_`. If a model returns an unprefixed ID like "F1" and there are multiple findings with suffix "_F1" across tracks (or if the prefix format drifts), the code either:
- Rejects valid votes due to ambiguity (>`1` match)
- Fails to resolve IDs when the separator doesn't match exactly (looking for `_F1` but ID is `track-F1`)
- **Impact:** Vote counts in debate will be artificially low, causing valid findings to be rejected or improperly confirmed based on incomplete tallies.

**CRITICAL ISSUE 3: Database integrity breakage from mismatched standalone ID formats**
In `db_writer.py` (lines ~229-240), `model_standalone_ids` is passed to link models to findings via `finding_id_map`. The code warns and continues when `ext_fid` is not found in the map. However:
- `finding_id_map` uses keys from `confirmed_findings` (e.g., `"expert_F1"`)
- `model_standalone_ids` comes from scoring, which may use raw IDs (e.g., `"F1"`) or differently prefixed IDs
- **Impact:** Database will be missing `model_findings` relationships for valid matches, breaking downstream analytics that rely on standalone coverage. The warning will spam logs but the data loss is permanent.

**CRITICAL ISSUE 4: Scoring infrastructure failures mask model failures**
The new `score_by_ids()` returns `(None, [])` when both scorers (one panel model/one panel model) fail to return parseable JSON or raise exceptions. This `None` is stored as the score and treated as "excluded from scoring" rather than 0%.
- **Impact:** If the scorer models are flaky (rate limits, bad JSON), target models get excluded from aggregation statistics rather than scored 0. This creates survival bias—only "lucky" models that got successful scorer calls get measured, invalidating service-eval comparability.

**CRITICAL ISSUE 5: Methodology discontinuity invalidates historical baseline**
The shift from 4-track (expert_prop/expert_open/light_prop/light_open) with cross-verification to 2-track (expert/light) with single-track golden set construction removes the cross-validation safety mechanism.
- **Impact:** If the single "expert" track produces systematic false positives (e.g., all 6 models hallucinate the same issue), there is no longer a cross-track verification to catch it. Historical data from the 4-track system is no longer comparable to data from the 2-track system, contaminating longitudinal service-eval trends.

**Recommendation:** Stop the pipeline. Fix Issue 1 by using structured argument objects (with explicit model attribution fields) instead of line-based string filtering. Fix Issue 3 by enforcing ID normalization (always using full prefixed IDs) before DB writes. Verify Issue 4 handling—decide whether scorer failure should default to 0% (penalizes model for infrastructure issues) or trigger a retry, but not exclusion.

## Aggregated
As a synthesizer of these expert perspectives, I have categorized the findings regarding the `REQ-BENCH-318` merge. There is a **unanimous consensus** among the models that the pipeline must be halted immediately.

### 1. The "Stop-the-Line" Consensus (Critical Failures)
The experts identified three categories of failure that will cause immediate, non-recoverable data corruption or system crashes:

*   **The `None` Propagation/Crash:** Multiple models (panel members) highlight that `score_by_ids` returns `None` on scorer failure, which then propagates into arithmetic operations (`TypeError`) or database writes. This will crash the pipeline mid-run.
*   **The `NameError` / Missing Logic:** one panel model identified a specific `NameError` where `weighted_total` is used but not defined in `score_track`. one panel model identified a `NameError` where `_call_model` is called in debate round 2 but is not defined in the scope.
*   **The UI/Dashboard Collapse:** one panel model and one panel model point out that `None` values (from scorer failures) will be passed to the frontend, where JavaScript `sort` and `Math.round` operations will encounter `NaN` or `null`, effectively breaking the leaderboard and rendering the dashboard unusable.

### 2. Areas of Disagreement & Nuance
While all agree on stopping, the experts offer distinct perspectives on the *nature* of the risk:

*   **Operational vs. Strategic:** 
    *   **reviewer-model** focuses on **concurrency/deadlock**, arguing that the nested `ThreadPoolExecutor` is a ticking time bomb for system stability.
    *   **one panel model and one panel model** focus on **scientific validity**, arguing that the removal of cross-family verification (the "Golden Set" change) is a strategic degradation that makes the service-eval susceptible to systemic bias.
*   **The "Debate" Scorer:** There is a creative tension here. While some models (one panel model) find the "debate-style" scorer "genuinely clever," others (one panel model) view it as "over-engineering" that triples API costs and introduces unnecessary variance.
*   **ID Resolution:** There is a recurring debate on whether the ID resolution logic is a "bug" or a "design flaw." Some suggest it is a simple coding error (duplicated logic), while others (one panel model) argue it is a fundamental architectural failure that will lead to permanent, silent data loss.

### 3. Unique/Creative Insights
*   **Survival Bias:** one panel model-k2.5 notes that by returning `None` instead of `0` for scorer failures, the system creates **survival bias**. Only models that successfully trigger the scorer are measured, while others are excluded, making the resulting leaderboard statistically invalid.
*   **The "Light" Track Logic:** one panel model-3.1-pro-preview identified a specific logic flaw where the `light` track will receive a 0% score because the `resolved_fid` mapping fails to bridge the gap between `light_F1` and the `expert` baseline IDs.

### Moderator Recommendation
**Stop the pipeline immediately.** 

The code is currently in a state that will produce "silent" data corruption (via ID resolution failures and survival bias) and "loud" crashes (via `NameError` and `TypeError`). 

**Immediate Action Plan:**
1.  **Patch the Crashes:** Define `weighted_total`, fix the `_call_model` import, and ensure `None` scores are coerced to `0.0` or handled via a robust default before they reach the DB or UI.
2.  **Flatten Concurrency:** Remove the nested `ThreadPoolExecutor` to prevent the deadlock/throttling cascades identified by reviewer-model.
3.  **Centralize ID Logic:** Refactor the ID resolution into a single, hardened utility function to prevent the silent data loss identified by one panel model and one panel model.
4.  **Re-evaluate the Golden Set:** Before resuming, address the strategic concern regarding the loss of cross-family verification. If the service-eval is to remain a "ground truth" source, the current "consensus-only" approach is likely insufficient.
