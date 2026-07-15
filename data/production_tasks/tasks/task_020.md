---
id: task_020
category: general_analysis
char_count: 53729
redaction: org-names-agents-pii-strategy-labels-removed
---

# Multi-model brainstorm — internal evaluation task
Mode: brainstorm
Models: grok-4.20-experimental-beta-0304-reasoning (9.4s), gpt-5.4 (52.85s), gemini-3.1-pro-preview (55.72s), claude-opus-4-6 (59.2s), dashscope/qwen3.5-plus (69.79s), redpill/moonshotai/kimi-k2.5 (89.16s)
is_code_review: false
code_generated_by: unknown

## Prompt
````
## Context
Living service-eval (service-eval.product.example.com) with adversarial consensus — 5 expert models debate findings on real production tasks (code reviews, brainstorms, architecture). 22 data points, 134 findings.

Current service-eval data shows debate dramatically improves most models (+15-40pp) but GPT-5.4 gains 0pp (contrarian). Opus is best debater (90% after debate).

We are implementing severity-weighted scoring. Here is the requirement:

### REQ-BENCH-311: Severity-weighted scoring with Material/Minor tiers
- Description: Two-tier weighted scoring across all task types.
  **Why weighted scoring:**
  Material findings are what matter in production. A critical security vulnerability is not equivalent to a style suggestion. Weighted scoring identifies which models excel at finding what actually matters — enabling informed decisions about which models to use for reviews, which to include in debate panels, and how to optimize review time. Models that consistently find Material findings are more valuable reviewers. Eventually, this data informs which models to use in production review panels (fewer models, faster reviews, focused on Material finding ability).
  **Golden set classification:**
  - After debate confirms which findings go in the golden set (existing process unchanged), models vote on each finding: Material or Minor.
  - Material = consequential to the outcome (critical bugs, paradigm-shifting insights). Weight: 10x.
  - Minor = useful but incremental (style issues, optimization ideas). Weight: 1x.
  - Old `valuable_perspective` category is eliminated — it maps to Material.
  - Classification vote: majority wins. Tie = Material. Rationale: when classification is uncertain, we would rather pay attention to something that might be Material than brush away something Material as Minor. Agents receiving review feedback are more likely to dismiss Minor findings — mislabeling a Material finding as Minor risks it being ignored. This is a safety-first default.
  **Scoring:**
  - At every tier (standalone, aggregation, debate), the pipeline identifies WHICH specific golden set findings (by ID) the model's response covers.
  - Scoring is binary per finding: model found it = full credit at the finding's weight. Model's own classification (Material vs Minor) is irrelevant — only the golden set classification matters.
  - Model's weighted score = sum of weights of matched findings / weighted total of golden set × 100.
  - Same scoring function for all tiers — no separate methods.
  **Traceability:**
  - Result files store matched finding IDs per model per tier.
  - Enables rescoring if weights change.
  **Existing data:**
  - Requires re-running pipeline with new scoring. Start with 1, then 2, then scale up.
- Trigger: Pipeline scoring, API stats calculation, website display.
- Expected: Weighted detection rates at all tiers. Models finding Material findings get 10x credit.
- Priority: P0
- Status: not-started
- Testable: Yes API
- Last-Updated-By: agent-alpha

### REQ-BENCH-312: Model versioning — each version is a separate entity

## Key Design Decisions Already Made
1. Golden set selection process unchanged (dual pipeline debate + cross-verification)
2. Classification is a NEW step AFTER golden set is confirmed — models vote Material vs Minor
3. Tie on classification = Material (safety-first: rather pay attention than dismiss)
4. Scoring is binary: found it = full credit at golden set weight. Model's own label irrelevant.
5. Same scoring at all tiers (standalone, aggregation, debate)
6. Old 'valuable_perspective' category eliminated — maps to Material

## Questions for Review
1. Is the classification vote (Material vs Minor) the right approach? Should it be part of the existing debate rounds or a separate step after?
2. Should classification happen within each group (proprietary/open separately) or across all models together?
3. Are there edge cases where 'found it = full credit regardless of model label' breaks down?
4. The tie = Material rule with the safety-first rationale — any risks of systematic over-weighting?
5. Any structural issues with this approach we haven't considered?
6. Does the 10x weight ratio feel right, or should it be different (5x? 20x?)?
````

## Individual Responses

### grok-4.20-experimental-beta-0304-reasoning (9.4s)
**Strategic Assessment**

This is a strong direction. Prioritizing Material findings is the correct strategic move. Most benchmarks optimize for volume; you're optimizing for *production value*. That's rare and valuable.

### 1. Classification approach and timing

**Separate step after golden set confirmation is correct.** Do not merge it into existing debate rounds.

**Reasoning:** 
- Golden set formation is a *truth-seeking* process. Classification is a *priority-setting* process. Conflating them degrades both.
- The current debate already has high cognitive load. Adding classification dilutes focus.
- Post-golden classification lets models evaluate severity with the full context of what survived debate, which improves judgment quality.

Keep it as a distinct phase.

### 2. Classification scope

**Classify across all models together, not in proprietary/open silos.**

The service-eval's value is in creating a single source of truth about what matters. Fragmenting the classification creates inconsistent standards and makes cross-model comparison messy. A finding is either Material or it isn't — the model family that surfaced it shouldn't change its weight.

### 3. Edge cases with "found it = full credit regardless of model label"

Yes, there is one meaningful edge case: **the model surfaces the finding but frames it in a way that makes it likely to be ignored.**

If a model correctly identifies a critical security vulnerability but buries it in the middle of 40 style suggestions with no emphasis, it *technically* "found it" but failed at the actual job. However, this is better handled through a separate *presentation quality* dimension later rather than contaminating the detection score now. Your current binary approach is correctly pragmatic for phase one.

### 4. Tie = Material rule

This is correct, but watch two risks:

- **Systematic over-weighting** is real if models are indecisive. Monitor the tie rate per finding. If >30% of classifications tie, your definition of Material/Minor is too vague and needs a sharper rubric.
- **Strategic voting**: Some models may learn to abstain or give weak signals to force ties. Less concerning with current model set, but worth watching.

The safety-first rationale is sound. False negatives on Material findings are much more expensive than false positives.

### 5. Structural issues not yet considered

Two significant ones:

- **Definition quality**: "Consequential to the outcome" is still too subjective. You need a sharper rubric with concrete anchors (security vulns, data loss, major architectural flaws, 10x efficiency improvements, etc.). Without this, classification variance will be high.
- **Score distortion on small sets**: With only 22 data points, having even 1-2 high-weight findings per task creates high variance. A model that luckily catches the single Material finding in a task gets an artificially massive boost. Consider **hierarchical scoring** (Material within task + overall) or requiring minimum finding counts before weighting fully kicks in.

### 6. Weight ratio

**10x is too high. Use 5x.**

**Reasoning:**
- 10x makes the service-eval almost entirely about Material detection. This sounds good until you realize many tasks have only 0-2 Material findings. The signal becomes extremely sparse.
- 5x gives Material findings dominant but not overwhelming weight. It still heavily rewards models that find what matters while preserving some signal from Minor findings (which still correlate with general capability).
- Opus being the best debater at 90% suggests the current setup already surfaces high-quality findings. We don't need to amplify the weighting to extremes.

**Final Recommendation Summary:**
- Proceed with separate classification step
- Classify across all models
- Keep "found it = full credit" (with presentation quality as future dimension)
- Keep tie = Material but monitor tie rate aggressively
- Drop to 5x weighting
- Invest heavily in a crisp Material/Minor rubric before launch

This system, once tuned, will give you something genuinely useful: a leaderboard that tells you which models to trust with your most important code and decisions. Most companies are still grading on style points. You're grading on what actually matters.

### gpt-5.4 (52.85s)
Here’s the blunt take: the overall design is directionally right, but your biggest risk is **turning “severity” into a noisy popularity contest** and then hard-baking that noise into a 10x multiplier. The scoring mechanics are fine. The weak point is the **classification process**.

## Bottom line answers

### 1. Is classification vote the right approach? Should it be part of debate or separate after?
**Yes, separate after golden set confirmation.**  
Do **not** mix it into the finding-discovery debate rounds.

Why:
- Discovery and severity are different cognitive tasks.
- If you combine them, strong personalities/models will anchor both “is this real?” and “how important is it?”
- You want severity judged on a **stable set of accepted findings**, not while findings are still being contested.
- Separate classification also improves auditability and rescoring.

But I would **not** rely on a raw simple vote alone. I’d use:
- **Independent first-pass classification** per model
- Then optional **short adjudication** only on split findings
- Store the vote distribution, not just the final label

That gives you:
- final binary label for scoring
- uncertainty metadata for analysis later

So: **separate step after golden set = correct**.  
But: **simple majority alone is too brittle unless you preserve disagreement data.**

---

### 2. Should classification happen within each group or across all models together?
**Across all models together for the canonical service-eval label.**

If you classify separately by proprietary/open groups, you create:
- two incompatible severity universes
- distorted comparisons
- incentives to cherry-pick which service-eval view to emphasize

Severity should be a property of the **finding in the task context**, not of the evaluator cohort.

That said, I’d absolutely compute **diagnostic slices**:
- proprietary-only classification agreement
- open-only classification agreement
- cross-group disagreement rate

But those should be analytics, **not the source of truth**.

So:
- **Canonical label:** all models together
- **Diagnostics:** subgroup breakdowns

---

### 3. Are there edge cases where “found it = full credit regardless of model label” breaks down?
Yes, but it’s still the right scoring rule.

You should keep it because otherwise you start rewarding agreement with the service-eval taxonomy rather than actual issue detection. Detection is the core skill you care about.

However, there are three edge cases to watch:

#### A. Model finds the issue but frames it as trivial
Example: model identifies a severe race condition but says “minor edge case.”  
Under your rule, it gets full 10x credit.

That feels wrong emotionally, but I still think the rule is correct for the main metric because:
- the hard part is often identifying the issue
- severity labeling is noisy and context-sensitive
- penalizing severity disagreement would entangle two tasks

My recommendation:
- Keep main score as detection-only
- Add a **secondary calibration metric**: “severity agreement on matched findings”

That gives you:
- primary metric = can it find important things?
- secondary metric = does it understand importance?

#### B. Model mentions a vague version of the finding
If matching is loose, a model can get 10x credit for a weak, hand-wavy mention of a Material issue.

This is a bigger problem than label disagreement.  
Your whole weighted system will be corrupted if **matching quality** is weak.

You need a strict coverage rule:
- finding match must capture the **substantive issue**, not a nearby symptom
- for security/perf/architecture findings, generic “there may be a problem here” should not count

If I were reviewing implementation, I’d focus more on **matching rigor** than the weight ratio.

#### C. Composite findings
Sometimes one golden finding bundles:
- root cause
- impact
- remediation insight

A model may identify only part of it and either get full credit or zero depending on matching policy.

That’s dangerous with 10x weights.  
So ensure Material findings are **atomic** enough that binary matching is fair.

If a finding can be half-found, it’s too coarse.

---

### 4. The tie = Material rule — any risks of systematic over-weighting?
**Yes. Definitely.**  
But it’s still a defensible default if you acknowledge what it does.

The risk:
- ambiguous findings get upgraded
- the service-eval becomes more “recall of possibly-important items” than “precision on clearly-material items”
- if your voters are conflict-averse or severity-happy, Material inflation creeps in

This is especially likely early on with only **22 data points / 134 findings**. Small datasets amplify weirdness.

My recommendation:
1. Keep **tie = Material** for now if safety-first is the product philosophy.
2. But track:
   - count of unanimous Material
   - majority Material
   - tie→Material
   - unanimous Minor
3. On the website/API, expose or at least internally monitor:
   - weighted score including tie→Material
   - weighted score excluding tie-derived Material

Why?  
Because if a model’s “Material skill” only shows up on ambiguous tie-classified items, that’s a weaker signal than finding unanimously Material issues.

So the rule is okay, but don’t let tie-promoted Material findings silently blend with high-confidence Material findings.

If you want a sharper stance:  
**Unanimous/strong-majority Material is the real signal; tie=Material is a safety overlay.**

---

### 5. Any structural issues with this approach you haven’t considered?
Yes — a few important ones.

## Structural issue 1: You are collapsing two service-eval goals into one number
Weighted score answers:
- “Did the model find more of the important stuff?”

Good.

But users also care about:
- “Does the model spam low-quality findings?”
- “Does debate improve identification of high-severity findings specifically?”
- “Is the model good at severity calibration?”

A single weighted detection rate won’t capture that.

You should report at least:
- **Weighted recall** (your main metric)
- **Unweighted recall**
- **Material-only recall**
- **Minor-only recall**
- **Severity calibration accuracy on matched findings** (secondary)
- ideally some precision-ish proxy if available

Otherwise a model that only finds a couple Material issues can look amazing while being poor overall, or vice versa.

## Structural issue 2: Small sample + 10x weights = unstable leaderboard movement
With 134 findings, if Material findings are relatively few, each one becomes leaderboard-dominant.  
That may be philosophically correct, but it will create:
- volatile rankings
- over-interpretation of small differences
- weird jumps when one or two finding matches change

This is not a reason to avoid weighting.  
It is a reason to:
- show confidence intervals or uncertainty bands if possible
- prominently show raw counts:
  - matched Material findings
  - total Material findings
  - matched Minor findings
  - total Minor findings

Without counts, the percentages will look more precise than they are.

## Structural issue 3: Severity is task-context dependent
A finding’s materiality depends on:
- environment
- system criticality
- exploitability
- business context
- whether it blocks deployment vs is just worth fixing

If your service-eval tasks vary a lot, cross-task severity labels may not be equally comparable.

That’s okay if your golden set process is task-aware.  
But I’d define Material explicitly as:
> consequential to correctness, security, reliability, production risk, or major strategic/architectural outcome in the specific task context

Not just “important sounding.”

## Structural issue 4: Debate may improve severity concentration differently than raw finding count
This is actually one of the most interesting things in your service-eval, and your design should preserve it.

You should expect cases like:
- debate adds few new findings overall
- but disproportionately adds Material findings

That’s much more interesting than total recall improvement.  
Make sure your stats layer supports:
- delta weighted score by tier
- delta Material recall by tier
- not just overall weighted %

## Structural issue 5: Golden set classification by the same models being evaluated
This is the most awkward methodological issue.

You’re using the evaluated models to help define the severity labels. That’s not automatically bad, but it introduces circularity:
- the service-eval population partly defines what counts as Material
- model family priors may shape labels
- future model versions may be judged against labels derived from older model consensus

I wouldn’t block the feature over this. It’s practical.  
But I would mitigate it by:
- preserving vote distributions
- allowing later reclassification/audit
- considering occasional human adjudication on disputed Material items
- versioning the golden severity labels over time

If REQ-BENCH-312 is model-versioning, that matters here too.  
Severity labels should ideally be associated with:
- task version
- golden set version
- classification panel version

Otherwise rescoring gets muddy.

---

### 6. Does 10x feel right, or should it be 5x or 20x?
**10x is aggressive, but probably right if your goal is operational model selection for production review.**

My real answer:
- **5x** = safer statistically, less distortion, more palatable
- **10x** = strong statement that Material dominates value
- **20x** = too extreme unless Minor findings are almost irrelevant to your actual use case

Given your stated rationale — production review panels, fewer models, optimize for consequential findings — I’d choose **10x over 5x**.

Why not 5x?
- 5x often sounds big but in practice still lets a pile of Minor findings compete too much with missing one serious issue.
- If users read “critical vulnerability” and “style suggestion,” they expect a large gap.
- 10x is easy to explain and intuitively matches “order of magnitude more important.”

Why not 20x?
- too sensitive to classification noise
- too punishing in a small service-eval
- makes any mismatch on a few Material findings overwhelm everything else
- turns your service-eval into almost pure Material-hit-rate, at which point you may as well just score Material-only recall

So:
- **Use 10x now**
- but agent-epsilon for configurable weights and re-run comparisons at **1x / 5x / 10x** internally
- if rankings are wildly unstable between 5x and 10x, that tells you your severity labels or sample size are not mature enough

That’s exactly why traceability by finding ID is essential.

---

# My recommended decisions

## Keep
- Separate classification step after golden set confirmation
- Binary scoring by matched finding ID
- Model’s own label irrelevant to main score
- Single scoring function across standalone/aggregation/debate
- Traceability with matched IDs
- 10x default weight, configurable in code

## Change / strengthen
### 1. Don’t use only final majority label; store full vote distribution
For each finding store:
- votes Material
- votes Minor
- final label
- whether label came from tie
- maybe disagreement score

This is cheap and very valuable.

### 2. Add a secondary metric for severity calibration
Not part of the main score, but useful:
- among findings a model matched, how often did its severity label agree with golden classification?

This catches models that find issues but consistently misprioritize them.

### 3. Define strict matching criteria
This is the highest-risk implementation detail.  
Weighted scoring magnifies any sloppiness in matching.

### 4. Ensure findings are atomic
Especially Material findings. No bundled mega-findings.

### 5. Report confidence/uncertainty-oriented breakdowns
At minimum:
- Material recall
- Minor recall
- weighted recall
- number of Material findings in dataset
- number of tie→Material findings

### 6. Consider escalation for disputed classifications
For findings with:
- tie
- or very split votes

Optionally flag for human review later.  
You don’t need this for v1, but you should leave room for it.

---

# Direct answers in short

1. **Classification vote approach?**  
   Yes, but do it **after** golden set confirmation, as a separate step. Don’t mix with debate discovery. Store disagreement data.

2. **Within group or across all models?**  
   **Across all models** for canonical labels. Group-specific splits only as diagnostics.

3. **Does found-it/full-credit break down?**  
   Some edge cases, but it’s still the right main rule. Add a separate severity-calibration metric.

4. **Tie = Material risks?**  
   Yes, it can inflate Material labels. Keep it if safety-first matters, but track tie-derived Material separately.

5. **Structural issues?**  
   Biggest ones: noisy severity voting, matching rigor, atomicity of findings, small-sample instability, and circularity from models helping define severity.

6. **10x weight?**  
   **Yes, 10x is reasonable**. Better than 5x for your stated goal, safer than 20x. Make it configurable.

---

# If I were writing the implementation note
I’d add one sentence like this:

> Severity classification is performed as a distinct post–golden set step across the full model panel. The canonical label is determined by majority vote (ties resolve to Material), while preserving per-finding vote distribution for auditability, uncertainty analysis, and future rescoring.

And one more:

> Weighted score measures detection of service-eval-confirmed findings, not severity-calibration skill; severity agreement is tracked separately as a secondary metric.

That would make the design much harder to misinterpret.

If you want, I can also turn this into a concrete PRD review comment set or an implementation checklist for REQ-BENCH-311.

### gemini-3.1-pro-preview (55.72s)
Here is my direct assessment of your design for REQ-BENCH-311. I am going to challenge several of your foundational assumptions because you are applying a product-engineering mindset (e.g., "safety-first") to service-eval design, which will destroy your signal-to-noise ratio.

### 1. Is the classification vote the right approach? Part of debate or separate?
**Keep it as a separate step, but do not use a democratic vote.** 
*Reasoning:* If you mix severity classification into the validity debate, models will conflate the two. A model might reject a valid finding simply because it disagrees with the proposed severity. Establishing ground truth (the golden set) is a binary question of fact. Severity is a question of impact. 
*Disagreement:* Do not use a 5-model vote for classification. You already know Opus is your best debater (90% accuracy). Use your single best reasoning model (or a strict panel of the top 3) to classify the confirmed golden set. Democratic voting among models of varying quality degrades the ground truth of your service-eval.

### 2. Should classification happen within groups or across all models?
**Across all models (or rather, a curated subset of the absolute best).**
*Reasoning:* The golden set represents the absolute ground truth of the service-eval. Ground truth does not have a "proprietary" or "open-source" version; it is universal. If you segment classification, you risk creating two different standards of truth, making cross-group comparisons mathematically invalid. Use your most capable models to define the standard, then judge all models against that single standard.

### 3. Are there edge cases where "found it = full credit regardless of model label" breaks down?
**Yes, this is a fatal flaw in your design.**
*Reasoning:* Your own PRD states: *"Agents receiving review feedback are more likely to dismiss Minor findings."* If a model finds a critical SQL injection but presents it as a "minor style nitpick," the human/agent will ignore it. If you award that model 10x points, your service-eval is lying about the model's production utility. 
*Recommendation:* If a model finds a Material issue but its own output frames it as Minor/trivial, it should receive 1x points, not 10x. A model must demonstrate an understanding of the severity to get the severity multiplier. Otherwise, you are rewarding "severity blindness."

### 4. The tie = Material rule (safety-first): any risks of systematic over-weighting?
**Yes. You must reverse this rule. Tie must = Minor.**
*Reasoning:* You are building a service-eval, not a production firewall. In production, "safety-first" makes sense. In a service-eval, "safety-first" destroys differentiation. If you default ties to Material, you artificially inflate the denominator (total possible score). This causes score compression. 
Furthermore, models are inherently sycophantic and tend to over-escalate severity. If a finding is so borderline that 5 expert models cannot agree it is Material, *it is not Material*. Reserve the 10x multiplier only for findings with absolute consensus. Ruthlessly protect the exclusivity of the Material tier.

### 5. Any structural issues with this approach we haven't considered?
**Issue A: Blended scoring hides the exact insight you want.**
If Model A finds 1 Material issue (10 pts) and Model B finds 10 Minor typos (10 pts), they have the same score. Are 10 typos worth one critical security flaw? No. A single blended percentage score is useless for routing decisions. 
*Fix:* Do not just output a blended score. Your primary top-line metrics must be split: **Material Recall (%)** and **Minor Recall (%)**. 

**Issue B: Merging `valuable_perspective` into `Material`.**
You are mixing objective facts (critical bugs) with subjective opinions (paradigm-shifting insights) into the same 10x bucket. Models will debate endlessly over whether an architectural suggestion is "Material," introducing massive variance into your golden set. 
*Fix:* Keep `valuable_perspective` as a separate axis, or explicitly define Material *only* as objective, outcome-altering facts (bugs, security, hard performance bottlenecks).

**Issue C: The GPT-5.4 Contrarian Data.**
You noted GPT-5.4 gains 0pp from debate. It is highly likely GPT-5.4 is already ignoring Minor findings and only focusing on Material ones. By forcing it through a debate where other models badger it into accepting Minor findings, you are penalizing a highly efficient model. Tracking "Material Recall" separately will likely prove GPT-5.4 is already operating exactly how you want a production reviewer to act.

### 6. Does the 10x weight ratio feel right?
**10x is mathematically dangerous for a blended score.**
*Reasoning:* In real life, a Material finding is infinitely more valuable than a Minor one. But in service-eval math, if a codebase has 3 Material findings (30 pts) and 40 Minor findings (40 pts), the Minor findings still control the majority of the total score. 
If you insist on a single blended score, the multiplier needs to be dynamic based on the ratio of findings in the golden set, ensuring that Material findings always account for at least 80% of the total possible points. 
*Better approach:* Abandon the blended weighted score entirely. Report **Material Recall** as the primary P0 metric, and **Minor Recall** as a secondary diagnostic metric. This perfectly aligns with your goal of deciding "which models to use in production review panels."

### claude-opus-4-6 (59.2s)
# Review of REQ-BENCH-311: Severity-Weighted Scoring

This is well-designed. The core insight — that finding a critical security vulnerability should count for more than spotting a style issue — is obviously correct, and the requirement is unusually clear about *why* each decision was made. Let me take the questions seriously.

---

## 1. Classification vote: separate step vs. during debate?

**Separate step after golden set confirmation is correct.** You already made this decision and it's the right one. Here's why it matters:

If you fold classification into debate, you introduce a coupling problem. Models will anchor on severity during the debate about whether a finding is *valid*, which contaminates both judgments. "This isn't Material" becomes a rhetorical backdoor for "this shouldn't be in the golden set." Keeping them sequential — first establish truth, then classify importance — preserves the integrity of both steps.

One thing to nail down: which models vote on classification? If it's the same 5 debate panel models, you get consistency but also correlation with the debate itself. If a model fought hard to include a finding, it may be biased toward labeling it Material to justify the fight. This is probably acceptable at your scale (22 data points) but worth monitoring. If you ever see classification votes correlating suspiciously with "which model championed the finding," that's a signal.

## 2. Classification within groups or across all models?

**Across all models together.** This isn't close.

The golden set is already unified — you don't have a "proprietary golden set" and an "open golden set." The classification of a finding's severity is a property of the finding itself, not a property of which models are being scored against it. A critical SQL injection is Material regardless of whether you're evaluating GPT-5.4 or Llama.

Splitting by group would also halve your voter pool, making tie-breaking noisier and classification less stable.

## 3. Edge cases where "found it = full credit regardless of model label" breaks down

Yes, there's one genuine edge case, but I don't think it's worth solving yet.

**The partial detection problem:** A model mentions a finding but for the wrong reasons or with an incorrect characterization that would lead an engineer astray. Example: model flags a race condition (Material finding in golden set), but its explanation describes it as a performance issue and suggests a fix that doesn't actually address the race condition. Binary "found it" gives full credit, but the model's output would be actively unhelpful in production.

At 22 data points, this is noise. At scale, you'd want a "quality of detection" dimension. For now, I'd log these cases when you spot them during matching and revisit when you have 100+ data points. Don't add complexity prematurely.

**What's NOT an edge case:** people will worry about "the model said it was Minor but the golden set says Material." The requirement already handles this correctly — the model's label is irrelevant. The model found the thing. That's what matters. Whether the model appreciated its severity is interesting metadata but shouldn't affect the score, because the *service-eval is measuring detection ability*, not triage ability. If you later want to measure triage ability, that's a separate metric.

## 4. Tie = Material: risks of systematic over-weighting?

The safety-first rationale in the requirement is sound, and the *direction* of the asymmetry is correct. But let me stress-test it.

**Risk scenario:** With a 2-tier system and 5 voters, a tie requires exactly a 2-3 or (in cases of abstention) a 2-2 split. If this happens frequently, you'll have an inflation problem where most borderline findings become Material and the 10x weight dominates your scores, making Minor findings essentially irrelevant to rankings.

**Mitigation that's already built in:** This is actually self-correcting. If too many findings get classified Material, the discriminating power shifts to *within* Material findings, which is exactly where you want discriminating power. A service-eval where Minor findings don't affect rankings much is a *better* service-eval than one where they do, because you're trying to identify models that find what matters.

**The real risk is the opposite direction:** if you had set tie = Minor, a model that's excellent at finding critical issues but mediocre at style nits could be ranked below a model that's great at style nits. That would be a service-eval failure. So: tie = Material is correct.

One thing to track: what percentage of findings end up Material vs Minor. If it's above 70% Material, your classification threshold may be too loose and you should tighten the definition, not change the tie-breaking rule.

## 5. Structural issues not yet considered

**Three things:**

**a) Matching is now your highest-leverage failure point.** The requirement says "the pipeline identifies WHICH specific golden set findings the model's response covers." This matching step is doing enormous work. A false negative on matching a Material finding costs the model 10 points. A false negative on Minor costs 1 point. So matching errors are now 10x more consequential for Material findings.

How are you doing matching today? If it's LLM-based semantic matching, you need to verify that the matching quality is consistent across finding types. Material findings (critical bugs, architectural issues) tend to be described more variably than Minor findings (style issues have more standardized language). I'd expect matching to be *harder* for Material findings, which means your most important scores are built on your least reliable matches. Audit this explicitly.

**b) The golden set size problem compounds.** With unweighted scoring, a golden set of 8 findings gives you reasonable granularity (each finding = 12.5%). With weighted scoring, if 2 of those 8 are Material, those 2 findings represent ~69% of the weighted total (20 out of 29). Missing or finding a single Material finding swings the score massively. This is *correct behavior* — it reflects reality — but it means your per-task scores will be volatile. Report confidence intervals or at minimum note the golden set composition (N Material, M Minor) alongside scores.

**c) Rescoring is mentioned but under-specified.** "Enables rescoring if weights change" — this is good foresight. But also consider: you may want to rescore if *classifications* change. As you accumulate data and refine what Material means, you might reclassify old findings. Store the classification votes and rationales, not just the outcome. This is cheap insurance.

## 6. Is 10x the right weight ratio?

10x is defensible and I'd start there, but here's the actual reasoning:

The weight ratio should reflect how much more you'd *pay* (in time, attention, risk) for a Material finding versus a Minor one in production. If a Material finding prevents a security breach and a Minor finding improves code readability, the real-world value ratio is probably 100x or more. But you're not trying to model economic value — you're trying to build a service-eval with useful discriminating power.

**The constraint is practical:** the ratio needs to be high enough that Material findings dominate rankings (otherwise why bother with weighting) but low enough that Minor findings still contribute *something* (otherwise why track them at all — just score on Material only).

At 10x: A model that finds all Material findings but zero Minor findings will outscore a model that misses one Material finding but finds all Minor findings. This is the correct ranking. Check: if your average task has 2 Material and 6 Minor findings, the weighted total is 26. All Material = 20/26 = 77%. All Minor = 6/26 = 23%. Finding all Material + missing all Minor still wins decisively. Good.

At 5x: The margins get tighter. All Material = 10/16 = 62.5%. All Minor = 6/16 = 37.5%. A model finding all Minor + 1 Material beats a model finding all Material + 0 Minor. Still probably fine but the signal is weaker.

At 20x: Minor findings become almost invisible. All Minor = 6/46 = 13%. At this point, drop the pretense and just score on Material.

**10x is the right ratio.** It makes Material findings dominant while keeping Minor findings worth detecting. You can always adjust later since you're storing the data for rescoring.

---

## Summary

The requirement is solid. The main things to get right in implementation:

1. **Matching quality audit** — your highest-risk component just got 10x more consequential for Material findings
2. **Track Material/Minor ratios** per task — if Material exceeds 70%, tighten the definition
3. **Store classification votes and rationales**, not just outcomes — you'll want to reclassify
4. **Report golden set composition** alongside scores so volatility is interpretable
5. **Start with 1 task, verify matching manually**, then scale — the requirement already says this, which is good

Everything else in the requirement is well-reasoned. Ship it.

### dashscope/qwen3.5-plus (69.79s)
Here is the strategic review of **REQ-BENCH-311**.

### 1. Is the classification vote (Material vs Minor) the right approach? Should it be part of the existing debate rounds or a separate step after?
**Keep it separate, but change the voters.**
A democratic vote among the participating models is structurally weak for severity classification. Models exhibit herd behavior; if the majority are weak at assessing business impact, the "wisdom of the crowd" becomes the "mediocrity of the crowd."
*   **Recommendation:** Do not use the participating models for the classification vote. Use a dedicated **Judge Model** (e.g., the current highest-performing debater, Opus) or a human-in-the-loop for the golden set classification.
*   **Reasoning:** Validity (is this a bug?) and Severity (does this matter?) are distinct cognitive tasks. Your debate process handles validity well. Severity requires context about production risk that general models may lack. A dedicated judge ensures consistency across service-eval runs. If you must vote, do it as a separate step using the debate transcript as context, not as raw findings.

### 2. Should classification happen within each group (proprietary/open separately) or across all models together?
**Across all models together.**
You are building a **universal standard of value**, not a comparative study of model ecosystems.
*   **Reasoning:** If you segregate, proprietary models might define "Material" as "complex logic errors" while open models define it as "security vulnerabilities." This creates incomparable scores. To decide "which models to use in production review panels," you need a single currency of value. A security bug is Material regardless of whether GPT or Llama found it. Unified classification ensures the 10x weight means the same thing for every entity.

### 3. Are there edge cases where 'found it = full credit regardless of model label' breaks down?
**Yes: The "Vague Hint" Edge Case.**
Binary scoring relies entirely on the **matching logic** between model output and golden set ID.
*   **Risk:** A model might say "Check the auth logic here" (vague) vs "Auth bypass possible due to missing token validation" (specific). If your matching algorithm counts the vague hint as a match for the specific golden finding, you inflate the score of models that hallucinate breadth without depth.
*   **Reasoning:** In production, a vague hint requires human investigation time (cost). A specific finding solves the problem (value). They are not equal.
*   **Recommendation:** The matching mechanism must require **semantic equivalence**, not just topic overlap. If the model identifies the risk but not the root cause, it should receive partial credit (e.g., 0.5x) or no credit, depending on your tolerance for noise. Strict binary matching favors models that spray broad warnings.

### 4. The tie = Material rule with the safety-first rationale — any risks of systematic over-weighting?
**Yes. This corrupts service-eval signal integrity.**
I disagree with the `Tie = Material` rule. While "safety-first" is correct for *runtime production alerts*, it is incorrect for *benchmarking model capability*.
*   **Reasoning:** A service-eval's job is **discrimination**, not protection. If you default ties to Material, you incentivize severity inflation. If 40% of findings are labeled Material due to ties, the 10x weight loses its power to distinguish top-tier models. You risk deploying a model that looks great on the service-eval (high Material score) but actually generates many false-positive "critical" alerts in production, causing alert fatigue.
*   **Recommendation:** **Tie = Minor.** Preserve the scarcity of the "Material" label. If the models cannot agree it is Material, it lacks the clear consequential impact required for the 10x tier. Fix the downstream agent's bias (train it to respect Minor findings) rather than corrupting the service-eval's precision.

### 5. Any structural issues with this approach we haven't considered?
**Three critical structural risks:**
1.  **Gaming the Weight:** Once models know Material = 10x, they will optimize their outputs to *claim* findings are Material. They will use alarmist language ("Critical Security Risk") to trigger matching algorithms or influence classification votes.
    *   *Mitigation:* The classification step must be blind to the model's own output label (which you have covered), but the Judge/Voters must be robust against alarmist language.
2.  **The GPT-5.4 Anomaly:** Your data shows GPT-5.4 gains 0pp from debate. Weighted scoring might reveal it finds mostly Minor issues. However, if GPT-5.4 is your baseline for "standard," and it ignores Material findings, your golden set might be biased towards what GPT-5.4 *can* find, not what *exists*.
    *   *Mitigation:* Ensure the golden set generation isn't dominated by models that struggle with Material findings.
3.  **Pipeline Cost:** Re-running the pipeline for weight changes is noted, but re-running for *classification* changes is heavier. If you agent-chi from Model Vote to Judge Model, you invalidate historical data comparability.
    *   *Mitigation:* Version the scoring schema explicitly (e.g., `Score_v1_10x`, `Score_v2_JudgeClassified`). Do not overwrite historical scores.

### 6. Does the 10x weight ratio feel right, or should it be different (5x? 20x?)?
**10x is correct.**
*   **Reasoning:** In production engineering, the cost difference between fixing a style issue (Minor) and a security vulnerability/data loss (Material) is often orders of magnitude. 2x or 5x is too close; it allows a model that finds 10 Minor issues to outweigh a model that finds 1 Material issue. That is the wrong incentive. 20x is too volatile; one finding decides the entire service-eval winner, reducing statistical significance across the 134 findings.
*   **Validation:** Run a simulation on your existing 134 findings. If 10x weighting results in >80% of the total score coming from <20% of the findings, the ratio is working as intended. If the distribution is flat, the classification tiering is failing, not the weight.

### Summary of Strategic Changes
1.  **Reject `Tie = Material`.** agent-chi to `Tie = Minor` to preserve service-eval precision.
2.  **Replace Model Vote with Judge.** Use a single high-capability model (or human) for classification to reduce noise.
3.  **Tighten Matching.** Ensure "found it" requires semantic specificity, not just topic alignment.
4.  **Monitor Inflation.** Track the % of findings classified as Material. If it exceeds 30%, your definition of Material is too loose.

### redpill/moonshotai/kimi-k2.5 (89.16s)
 Direct answers below, followed by critical structural concerns.

**1. Classification vote: Keep it separate, but isolate it from debate contamination.**
Do not use the debate panel for classification. Debate induces polarization and anchoring—models dig into positions. Severity assessment requires neutral, contextual evaluation of impact, not argumentative stance. Run classification as a distinct step with fresh model instances (or at minimum, fresh context windows with no debate history). 

**2. Classification pooling: Across all models, but weighted by calibration.**
Universal standards matter more than tribal knowledge. However, apply inverse-variance weighting: if Anthropic models historically over-index on "Material" compared to OpenAI, weight their votes proportionally less. Do not split by proprietary/open; that creates divergent severity standards and makes your service-eval incomparable across the ecosystem.

**3. Edge case—The "Dismissal Trap":**
"Found it = full credit" collapses if a model mentions a finding only to dismiss it as false/irrelevant. Example: *"Some might think this is a race condition [Material], but it's actually thread-safe due to the guard clause."* Under your matching logic, this model gets 10x credit for "finding" the race condition, when in fact it **denied** it. You must add an "affirmative intent" classifier: the model must endorse the finding's validity, not merely reference its existence. Without this, you will systematically reward contrarian models (like your GPT-5.4 outlier) for refuting critical bugs.

**4. Tie = Material creates guaranteed severity inflation.**
With binary classification and safety-first defaults, your golden set will asymptotically approach 100% Material weighting. This destroys discriminative power. If 60% of findings become Material-weighted, the 10x multiplier becomes noise. You are optimizing for recall at the expense of measurement precision. **Challenge the assumption:** In production, "uncertain severity" does not default to Action Required; it defaults to Triage. Treat ties as "Uncertain/Major" (3x weight), not Material (10x). This preserves the safety signal without destroying the scale.

**5. Structural issues you missed:**

- **Conflict of Interest:** Models voting on severity are competing on weighted scores. A model can game the system by voting rival findings as Minor (reducing their weighted denominator) while voting its own candidates as Material. This is strategic manipulation of the service-eval.
  
- **Sparsity Distortion:** With 134 findings across 22 tasks (~6 per task), a single Material finding carries massive leverage. A model that finds 1 Material bug but misses 5 Minor issues scores 10/15 = 67%. A model finding 0 Material but 5 Minor scores 5/15 = 33%. You are selecting for "lucky lottery ticket" models, not thorough reviewers. Production code review requires **density** of Minor fixes; Material bugs are rare and often caught by compilers. Your weighting inverts this utility.

- **GPT-5.4's Zero-Gain Signals a Deeper Problem:** If debate improves Claude/Opus (+40pp) but not GPT-5.4, GPT-5.4 is either (a) already at ceiling, (b) non-conformist to groupthink, or (c) gaming the current consensus mechanism. If (b), your new system will marginalize it further because debate consensus drives golden set selection, and ties go to Material (majority preference). You risk optimizing your service-eval for agreeable models, not correct ones.

**6. 10x is too high for your n; use 3x or dynamic weighting.**
With 134 findings, a 10x ratio creates unacceptable variance. If Material findings naturally occur at 10% base rate (13 findings), they represent 130/251 = 52% of total score weight. One false positive in Material classification swings aggregate scores by 7-10 percentage points. 

**Recommendation:** Start with 3x. If you must keep 10x, add a third tier (Critical=10x, Major=3x, Minor=1x) to reduce binary cliff effects. Alternatively, use logarithmic scoring: weight = 1 + 9×(severity_score), where severity is a continuous 0-1 voted average, not binary. This eliminates the tie-breaker problem and captures nuance.

---

### Strategic Synthesis

REQ-BENCH-311 as specified will **corrupt your service-eval's ability to select production reviewers**. You are building a system that rewards:
1. Mention-then-dismiss strategies (via edge case #3)
2. Majority-groupthink (via tie-breaking and debate anchoring)
3. High-variance gambling on rare "Material" hits (via 10x weights on sparse data)

**Immediate fixes:**
1. **Add "affirmative intent" detection** before matching findings to golden set IDs.
2. **Change tie rule:** Uncertain = 3x (not 10x) or force human adjudication on ties.
3. **Reduce weight ratio to 3x-5x** until you have >500 findings.
4. **Remove models from severity voting for their own tier** (standalone models don't vote on standalone classification; debate models don't vote on debate classification) to eliminate conflict of interest.
5. **Investigate GPT-5.4's null debate gains.** If it's identifying false consensus (correctly rejecting bad findings that the panel accepts), your golden set is contaminated with false positives. Do not proceed with weighting until you audit whether the "improved" models are actually agreeing on truth or mutually reinforcing hallucinations.

REQ-BENCH-312 (versioning) is critical—ensure GPT-4-0314 and GPT-4-1106 are treated as distinct entities; otherwise your time-series data becomes meaningless as models drift.

Stop calling this "severity-weighted scoring" until you fix the dismissal trap. Right now it's "mention-weighted scoring," which selects for verbose, contrarian models, not accurate ones.

## Aggregated
As your moderator, I have synthesized the perspectives of six expert models regarding **REQ-BENCH-311**. There is a strong consensus on the *strategic necessity* of weighting, but significant disagreement on the *mechanics* of implementation.

### 1. Where Experts Disagree (The Signal)
*   **The "Tie" Rule:** There is a sharp divide. Some models (Grok, Opus) support `Tie = Material` as a necessary safety-first heuristic. Others (Gemini, Kimi) argue this will cause "severity inflation," where the service-eval loses its ability to discriminate because too many findings become "Material."
*   **The "Dismissal Trap":** A critical, creative insight emerged: your current "found it = full credit" rule is vulnerable to models that mention a critical bug only to dismiss it. Kimi and Gemini argue this rewards "mentioning" rather than "understanding," which could lead to selecting models that are verbose but wrong.
*   **The Role of Models in Voting:** There is a consensus that using the debate panel to vote on severity is a conflict of interest. Models may vote to protect their own findings or manipulate the weighted denominator.

### 2. Unique & Creative Insights
*   **Affirmative Intent:** Kimi suggests that a match should only count if the model *endorses* the finding. If a model says "This is a race condition, but it's fine," it should not get 10x credit.
*   **Severity Calibration Metric:** GPT-5.4 and others suggest that while the *main* score should be detection-based, you should track a secondary "calibration" metric: *Does the model's own severity label match the golden set?* This identifies models that find bugs but don't understand their impact.
*   **The "GPT-5.4 Anomaly":** Several models noted that GPT-5.4’s 0pp gain from debate is a red flag. It may be a "contrarian" model that correctly rejects false consensus. If your golden set is built on consensus, you might be penalizing the most accurate model.

### 3. Majority View vs. Minority Insights
*   **Majority:** Keep the classification step separate from the debate; use a 10x weight; apply the classification across all models (no silos).
*   **Minority/Nuanced:** Use a "Judge Model" (Opus) for classification rather than a democratic vote; consider a 3-tier system (Critical/Major/Minor) to avoid the "binary cliff" of 10x vs 1x; track confidence intervals because your sample size (22 tasks) is too small for high-variance weighting.

### 4. Moderator’s Recommendation
To preserve the integrity of your service-eval while achieving your goal of identifying "production-ready" reviewers, I recommend the following adjustments to REQ-BENCH-311:

1.  **Adopt "Affirmative Intent" Matching:** Do not grant 10x credit if the model explicitly dismisses the finding. The model must identify the issue *and* acknowledge its validity.
2.  **Replace Democratic Voting with a "Judge":** Use your highest-performing debater (Opus) as the sole arbiter for severity classification. This eliminates the "herd behavior" and strategic voting risks identified by the panel.
3.  **Refine the Tie Rule:** Instead of `Tie = Material`, use `Tie = Major (3x)`. This prevents the "severity inflation" that would otherwise render your 10x multiplier meaningless, while still erring on the side of caution.
4.  **Add a "Calibration" Diagnostic:** Do not let the model's own label affect the score, but *do* report a "Severity Calibration Score" as a secondary metric. This will help you see if a model is "severity blind."
5.  **Audit the Consensus:** Before finalizing the golden set, have a human or a high-capability model review the findings where GPT-5.4 disagreed with the panel. If GPT-5.4 is right, your golden set is currently biased toward "consensus hallucinations."

**Final Verdict:** Proceed with the 10x weighting, but treat it as a "living" variable. Store the raw vote distributions and the "affirmative intent" metadata so you can re-run the leaderboard if you decide to adjust the weights or the matching logic later.
