---
id: task_041
category: code_review
char_count: 23520
redaction: org-names-agents-pii-strategy-model-ids-removed
---

# Code Generation: llm
# Task: REQ-BENCH-315 (light models through full pipeline)
# Time: 59.8s, Status: completed
# Length: 23337 chars
# Prompt size: trimmed (~15KB)

--- a/src/pipeline/run_benchmark.py
+++ b/src/pipeline/run_benchmark.py
@@ -26,6 +26,18 @@
 OPEN_MODELS = [
     "alibaba-reviewer-model", "moonshot-reviewer-model",
     # a fallback model dropped: 0% aggregation, 0% debate, 28K chars of noise. Tested 2026-04-01.
+]
+LIGHT_MODELS = [
+    "light-model-d", "light-model-f",
+    "light-model-b", "light-model-a",
+    "reviewer-model-fast", "light-model-e",
+]
+LIGHT_ALIASES = {
+    "light-model-d": "light_slot_d",
+    "light-model-f": "glm_4_7_flash",
+    "light-model-b": "gpt_5_4_mini",
+    "light-model-a": "light_slot_a",
+    "reviewer-model-fast": "grok_4_2_fast",
+    "light-model-e": "qwen3_5_flash",
 ]
 
 # === process_file SIGNATURE (line 302) ===
@@ -299,7 +311,7 @@
-def process_file(filepath, dry_run=False, expert_only=False):
+def process_file(filepath, dry_run=False, expert_only=False, light_only=False):
     """Process a single service-eval data point."""
     name = filepath.name
     content = filepath.read_text()
@@ -307,6 +319,34 @@
 
     log.info(f"Processing: {name} ({len(content)} chars, hash={prompt_hash})")
 
+    results_file = Path("data/results") / f"{prompt_hash}.json"
+
+    def load_golden_set():
+        if not results_file.exists():
+            return None
+        try:
+            existing = json.loads(results_file.read_text())
+            final_confirmed = existing.get("baseline_findings", []) or []
+            if not final_confirmed:
+                return None
+            baseline_ids = set(existing.get("baseline_ids", [])) or {
+                f.get("id", "") for f in final_confirmed if f.get("id")
+            }
+            weighted_total = existing.get("weighted_total")
+            if weighted_total is None:
+                weighted_total = sum(f.get("severity_weight", 1) for f in final_confirmed) if final_confirmed else 1
+            return {
+                "final_confirmed": final_confirmed,
+                "baseline_ids": baseline_ids,
+                "weighted_total": weighted_total,
+                "existing": existing,
+            }
+        except Exception as e:
+            log.warning(f"Could not load existing golden set from {results_file}: {e}")
+            return None
+
+    using_existing_golden = False
+    existing_results = {}
+    final_confirmed = []
+
 # === STEP 5: CLASSIFICATION + STEP 6: SCORING (lines 525-658) ===
-    # Step 5: Classification vote — Material or Minor for each golden set finding
-    log.info("Step 5: Classification vote (Material vs Minor)...")
-    classification_results = {}  # finding_id -> {"material": N, "minor": N}
-    if final_confirmed:
+    if light_only:
+        golden = load_golden_set()
+        if not golden:
+            log.error("Light-only requested but no expert golden set found")
+            return False
+        using_existing_golden = True
+        existing_results = golden.get("existing", {})
+        final_confirmed = golden["final_confirmed"]
+        baseline_ids = golden["baseline_ids"]
+        weighted_total = golden["weighted_total"]
+        log.info("Using existing expert golden set from results file")
+    else:
+        # Step 5: Classification vote — Material or Minor for each golden set finding
+        log.info("Step 5: Classification vote (Material vs Minor)...")
+        classification_results = {}  # finding_id -> {"material": N, "minor": N}
+        if final_confirmed:
         findings_for_vote = "\n".join(
             f'  {f.get("id","?")}: {f.get("description","")}' for f in final_confirmed)
         classify_prompt = f"""For each finding below, classify as MATERIAL or MINOR.
@@ -348,20 +388,20 @@
             log.info(f"  {fid}: {f['severity'].upper()} "
                      f"(material={votes['material']}, minor={votes['minor']})")
 
-    # Calculate weighted baseline total
-    weighted_total = sum(f.get("severity_weight", 1) for f in final_confirmed) if final_confirmed else 1
+        # Calculate weighted baseline total
+        weighted_total = sum(f.get("severity_weight", 1) for f in final_confirmed) if final_confirmed else 1
 
-    # Build baseline list with IDs for matching
-    baseline_list = "\n".join(
-        f'  {f.get("id","B"+str(i+1))}: {f.get("description","")}' for i, f in enumerate(final_confirmed))
+        # Build baseline IDs for matching
+        baseline_ids = {f.get("id", "") for f in final_confirmed if f.get("id")}
 
     def score_response_by_ids(model_response_text):
         """Score by identifying WHICH specific baseline findings are covered. Returns (weighted_pct, matched_ids)."""
         if not model_response_text or not final_confirmed:
             return 0.0, []
+        baseline_list = "\n".join(
+            f'  {f.get("id","B"+str(i+1))}: {f.get("description","")}' for i, f in enumerate(final_confirmed))
         finding_ids = [f.get("id", "") for f in final_confirmed]
         ids_str = ", ".join(finding_ids)
         prompt = f"""Which of the BASELINE findings are identified or mentioned in the MODEL RESPONSE below?
 Two findings match if they describe the same issue, even in different words.
-
 BASELINE FINDINGS (the reference set):
 {baseline_list}
 
@@ -381,13 +421,30 @@
         pct = round(100.0 * weighted_found / weighted_total, 1)
         return pct, matched_ids
 
+    def score_models(models, individual, aggregation_per_model, debate_data, label):
+        log.info(f"Scoring {label} tiers against weighted baseline...")
+        model_standalone_scores = {}
+        model_aggregation_scores = {}
+        model_debate_scores = {}
+        model_standalone_ids = {}
+        model_aggregation_ids = {}
+        model_debate_ids = {}
+
+        all_debate_data = debate_data.get("interim", []) if debate_data else []
+        for model_name in models:
+            standalone_resp = next((r.get("response", "") for r in individual
+                                    if r["model"] == model_name), "")
+            std_pct, std_ids = score_response_by_ids(standalone_resp)
+            model_standalone_scores[model_name] = std_pct
+            model_standalone_ids[model_name] = std_ids
+
+            agg_text = json.dumps(aggregation_per_model.get(model_name, []))
+            agg_pct, agg_ids = score_response_by_ids(agg_text)
+            model_aggregation_scores[model_name] = agg_pct
+            model_aggregation_ids[model_name] = agg_ids
+
-    log.info("Scoring all tiers against weighted baseline...")
-    model_standalone_scores = {}
-    model_aggregation_scores = {}
-    model_debate_scores = {}
-    model_standalone_ids = {}
-    model_aggregation_ids = {}
-    model_debate_ids = {}
-
-    for model_name in PROPRIETARY_MODELS + OPEN_MODELS:
-        # Standalone: score the raw response
-        standalone_resp = next((r.get("response", "") for r in individual
-                                if r["model"] == model_name), "")
-        std_pct, std_ids = score_response_by_ids(standalone_resp)
-        model_standalone_scores[model_name] = std_pct
-        model_standalone_ids[model_name] = std_ids
-
-        # Aggregation: score the aggregation response
-        agg_text = json.dumps(aggregation_per_model.get(model_name, []))
-        agg_pct, agg_ids = score_response_by_ids(agg_text)
-        model_aggregation_scores[model_name] = agg_pct
-        model_aggregation_ids[model_name] = agg_ids
-
-        # Debate: count baseline findings this model voted VALID on
-        all_debate_data = debate_prop.get("interim", []) + debate_open.get("interim", [])
-        model_valid_findings = set()
-        for rd in all_debate_data:
-            for fid, vdata in rd.get("verdicts_by_finding", {}).items():
-                for arg in vdata.get("arguments", []):
-                    if arg.get("model") == model_name:
-                        verdict = arg.get("conclusion", "").upper()
-                        if "VALID" in verdict and "INVALID" not in verdict:
-                            model_valid_findings.add(fid)
-                        elif "INVALID" in verdict:
-                            model_valid_findings.discard(fid)
-        debate_matched_ids = list(model_valid_findings & baseline_ids)
-        debate_weighted = sum(
-            next((f.get("severity_weight", 1) for f in final_confirmed if f.get("id") == mid), 1)
-            for mid in debate_matched_ids)
-        model_debate_scores[model_name] = round(100.0 * debate_weighted / weighted_total, 1)
-        model_debate_ids[model_name] = debate_matched_ids
+            model_valid_findings = set()
+            for rd in all_debate_data:
+                for fid, vdata in rd.get("verdicts_by_finding", {}).items():
+                    for arg in vdata.get("arguments", []):
+                        if arg.get("model") == model_name:
+                            verdict = arg.get("conclusion", "").upper()
+                            if "VALID" in verdict and "INVALID" not in verdict:
+                                model_valid_findings.add(fid)
+                            elif "INVALID" in verdict:
+                                model_valid_findings.discard(fid)
+            debate_matched_ids = list(model_valid_findings & baseline_ids)
+            debate_weighted = sum(
+                next((f.get("severity_weight", 1) for f in final_confirmed if f.get("id") == mid), 1)
+                for mid in debate_matched_ids)
+            model_debate_scores[model_name] = round(100.0 * debate_weighted / weighted_total, 1)
+            model_debate_ids[model_name] = debate_matched_ids
 
-        log.info(f"  {model_name:40} standalone={model_standalone_scores[model_name]}%  "
-                 f"agg={model_aggregation_scores[model_name]}%  debate={model_debate_scores[model_name]}%")
+            log.info(f"  {model_name:40} standalone={model_standalone_scores[model_name]}%  "
+                     f"agg={model_aggregation_scores[model_name]}%  debate={model_debate_scores[model_name]}%")
+        return (
+            model_standalone_scores, model_aggregation_scores, model_debate_scores,
+            model_standalone_ids, model_aggregation_ids, model_debate_ids
+        )
 
-    log.info("Per-model weighted scores:")
-    for m in PROPRIETARY_MODELS + OPEN_MODELS:
+    expert_models = PROPRIETARY_MODELS + OPEN_MODELS
+    expert_debate_combined = {
+        "interim": debate_prop.get("interim", []) + debate_open.get("interim", [])
+    }
+    (model_standalone_scores, model_aggregation_scores, model_debate_scores,
+     model_standalone_ids, model_aggregation_ids, model_debate_ids) = score_models(
+        expert_models, individual, aggregation_per_model, expert_debate_combined, "expert"
+    )
+
+    log.info("Per-model weighted scores:")
+    for m in expert_models:
         log.info(f"  {m:40} std={model_standalone_scores.get(m, 0)}%  "
                  f"agg={model_aggregation_scores.get(m, 0)}%  debate={model_debate_scores.get(m, 0)}%")
+
+    light_scores = {}
+    if not expert_only:
+        log.info("Running light models through same pipeline...")
+        light_individual = call_model_group(LIGHT_MODELS, content)
+        light_aggregation_per_model = aggregate_findings_by_model(light_individual, content)
+        light_debate = run_debate_rounds(light_aggregation_per_model, LIGHT_MODELS, content)
+        (light_model_standalone_scores, light_model_aggregation_scores, light_model_debate_scores,
+         light_model_standalone_ids, light_model_aggregation_ids, light_model_debate_ids) = score_models(
+            LIGHT_MODELS, light_individual, light_aggregation_per_model, light_debate, "light"
+        )
+        light_scores = {
+            m: {
+                "standalone_pct": light_model_standalone_scores.get(m),
+                "standalone_ids": light_model_standalone_ids.get(m, []),
+                "aggregation_pct": light_model_aggregation_scores.get(m),
+                "aggregation_ids": light_model_aggregation_ids.get(m, []),
+                "debate_pct": light_model_debate_scores.get(m),
+                "debate_ids": light_model_debate_ids.get(m, []),
+            }
+            for m in LIGHT_MODELS
+        }
 
 # === CURRENT STEP 9: LIGHT BACKFILL — TO BE REPLACED (lines 669-782) ===
-                "original_content": content,
-                "timestamp": datetime.now(timezone.utc).isoformat(),
-                "request_type": req_type,
-                # Step 1: Standalone responses (full text)
-                "standalone_responses": [
-                    {"model": r.get("model"), "response": r.get("response", ""),
-                     "time": r.get("time", 0), "status": r.get("status")}
-                    for r in individual
-                ],
-                # Step 2: Aggregation per model (full findings)
-                "aggregation_per_model": {
-                    m: findings_list for m, findings_list in aggregation_per_model.items()
-                },
-                # Step 3: Extraction (unified finding list)
-                "extracted_findings": [
-                    {"id": f.get("id"), "category": f.get("category"),
-                     "description": f.get("description")}
-                    for f in confirmed
-                ],
-                # Step 4: Debate
-                "proprietary_debate": {
-                    "rounds": debate_prop["rounds"],
-                    "confirmed_ids": list(prop_confirmed),
-                    "models": PROPRIETARY_MODELS,
-                    "interim": debate_prop.get("interim", []),
-                },
-                "open_debate": {
-                    "rounds": debate_open["rounds"],
-                    "confirmed_ids": list(open_confirmed),
-                    "models": OPEN_MODELS,
-                    "interim": debate_open.get("interim", []),
-                },
-                # Cross-verification
-                "cross_confirmed": list(cross_confirmed),
-                "cross_accepted": list(cross_accepted),
-                "cross_rejected": list(
-                    (prop_only | open_only) - cross_accepted
-                ),
-                # Final baseline with classification
-                "baseline_ids": list(baseline_ids),
-                "baseline_findings": [
-                    {"id": f.get("id"), "category": f.get("category"),
-                     "severity": f.get("severity"), "severity_weight": f.get("severity_weight"),
-                     "severity_votes": f.get("severity_votes"),
-                     "description": f.get("description"), "source": f.get("source")}
-                    for f in final_confirmed
-                ],
-                "weighted_total": weighted_total,
-                # Per-model scores with matched finding IDs
-                "scores": {
-                    m: {
-                        "standalone_pct": model_standalone_scores.get(m),
-                        "standalone_ids": model_standalone_ids.get(m, []),
-                        "aggregation_pct": model_aggregation_scores.get(m),
-                        "aggregation_ids": model_aggregation_ids.get(m, []),
-                        "debate_pct": model_debate_scores.get(m),
-                        "debate_ids": model_debate_ids.get(m, []),
-                    }
-                    for m in PROPRIETARY_MODELS + OPEN_MODELS
-                },
-            }, rf, indent=2, default=str)
+                result_payload = existing_results if using_existing_golden else {}
+                if not using_existing_golden:
+                    result_payload.update({
+                        "original_content": content,
+                        "timestamp": datetime.now(timezone.utc).isoformat(),
+                        "request_type": req_type,
+                        "standalone_responses": [
+                            {"model": r.get("model"), "response": r.get("response", ""),
+                             "time": r.get("time", 0), "status": r.get("status")}
+                            for r in individual
+                        ],
+                        "aggregation_per_model": {
+                            m: findings_list for m, findings_list in aggregation_per_model.items()
+                        },
+                        "extracted_findings": [
+                            {"id": f.get("id"), "category": f.get("category"),
+                             "description": f.get("description")}
+                            for f in confirmed
+                        ],
+                        "proprietary_debate": {
+                            "rounds": debate_prop["rounds"],
+                            "confirmed_ids": list(prop_confirmed),
+                            "models": PROPRIETARY_MODELS,
+                            "interim": debate_prop.get("interim", []),
+                        },
+                        "open_debate": {
+                            "rounds": debate_open["rounds"],
+                            "confirmed_ids": list(open_confirmed),
+                            "models": OPEN_MODELS,
+                            "interim": debate_open.get("interim", []),
+                        },
+                        "cross_confirmed": list(cross_confirmed),
+                        "cross_accepted": list(cross_accepted),
+                        "cross_rejected": list(
+                            (prop_only | open_only) - cross_accepted
+                        ),
+                        "baseline_ids": list(baseline_ids),
+                        "baseline_findings": [
+                            {"id": f.get("id"), "category": f.get("category"),
+                             "severity": f.get("severity"), "severity_weight": f.get("severity_weight"),
+                             "severity_votes": f.get("severity_votes"),
+                             "description": f.get("description"), "source": f.get("source")}
+                            for f in final_confirmed
+                        ],
+                        "weighted_total": weighted_total,
+                        "scores": {
+                            m: {
+                                "standalone_pct": model_standalone_scores.get(m),
+                                "standalone_ids": model_standalone_ids.get(m, []),
+                                "aggregation_pct": model_aggregation_scores.get(m),
+                                "aggregation_ids": model_aggregation_ids.get(m, []),
+                                "debate_pct": model_debate_scores.get(m),
+                                "debate_ids": model_debate_ids.get(m, []),
+                            }
+                            for m in expert_models
+                        },
+                    })
+                result_payload["light_scores"] = light_scores
+                json.dump(result_payload, rf, indent=2, default=str)
         log.info(f"  Full results saved: {results_file.name}")
     except Exception as e:
         log.warning(f"  Could not save results: {e}")
@@ -454,120 +511,17 @@
     # Step 5: Write to Cloud SQL
     log.info("Step 5: Writing to Cloud SQL...")
     try:
-        db_spec = importlib.util.spec_from_file_location(
-            "db_writer", Path(__file__).parent / "db_writer.py")
-        db_writer = importlib.util.module_from_spec(db_spec)
-        db_spec.loader.exec_module(db_writer)
-        write_to_cloud_sql = db_writer.write_to_cloud_sql
-        write_to_cloud_sql(name, prompt_hash, req_type, final_confirmed, individual, rejected_by_model,
-                          model_standalone_scores=model_standalone_scores,
-                          model_aggregation_scores=model_aggregation_scores,
-                          model_debate_scores=model_debate_scores)
+        if not light_only:
+            db_spec = importlib.util.spec_from_file_location(
+                "db_writer", Path(__file__).parent / "db_writer.py")
+            db_writer = importlib.util.module_from_spec(db_spec)
+            db_spec.loader.exec_module(db_writer)
+            write_to_cloud_sql = db_writer.write_to_cloud_sql
+            write_to_cloud_sql(name, prompt_hash, req_type, final_confirmed, individual, rejected_by_model,
+                              model_standalone_scores=model_standalone_scores,
+                              model_aggregation_scores=model_aggregation_scores,
+                              model_debate_scores=model_debate_scores)
     except Exception as e:
         log.error(f"DB write failed: {e}")
         return False
-
-    # Step 6: Light model backfill — proper extraction against debate baseline
-    LIGHT_MODELS = [
-        "light-model-d", "light-model-f",
-        "light-model-b", "light-model-a",
-        "reviewer-model-fast", "light-model-e",
-    ]
-    LIGHT_ALIASES = {
-        "light-model-d": "light_slot_d",
-        "light-model-f": "glm_4_7_flash",
-        "light-model-b": "gpt_5_4_mini",
-        "light-model-a": "light_slot_a",
-        "reviewer-model-fast": "grok_4_2_fast",
-        "light-model-e": "qwen3_5_flash",
-    }
-    if expert_only:
-        log.info("Step 6: Skipped (--expert-only)")
-    elif final_confirmed:
-        log.info("Step 6: Light model backfill (extraction + matching)...")
-        # Build categorized baseline for matching prompt
-        cat_baseline = []
-        for i, f in enumerate(final_confirmed):
-            cat_baseline.append(f'  B{i+1} [{f.get("category","unknown")}]: {f.get("description","")}')
-        baseline_text = "\n".join(cat_baseline)
-
-        conn = None
-        try:
-            conn = db_writer._get_connection()
-            cur = conn.cursor()
-            cur.execute("SELECT id FROM benchmark_runs WHERE external_id = %s", (prompt_hash,))
-            run_row = cur.fetchone()
-            if not run_row:
-                log.warning("  No run found for light backfill")
-            else:
 
 # === MAIN (lines 790-830) ===
@@ -575,6 +529,7 @@
     parser.add_argument("--file", type=str, help="Process a single file")
     parser.add_argument("--dry-run", action="store_true", help="Do not write to DB")
     parser.add_argument("--expert-only", action="store_true", help="Run expert models only")
+    parser.add_argument("--light-only", action="store_true", help="Run light models only using existing golden set")
     args = parser.parse_args()
 
     if args.file:
@@ -582,7 +537,7 @@
         if not filepath.exists():
             log.error(f"File not found: {filepath}")
             sys.exit(1)
-        ok = process_file(filepath, dry_run=args.dry_run, expert_only=args.expert_only)
+        ok = process_file(filepath, dry_run=args.dry_run, expert_only=args.expert_only, light_only=args.light_only)
         sys.exit(0 if ok else 1)
 
     ok_count = 0
@@ -592,7 +547,7 @@
     for filepath in files:
         try:
-            if process_file(filepath, dry_run=args.dry_run, expert_only=args.expert_only):
+            if process_file(filepath, dry_run=args.dry_run, expert_only=args.expert_only, light_only=args.light_only):
                 ok_count += 1
         except Exception as e:
             log.exception(f"Failed processing {filepath.name}: {e}")
