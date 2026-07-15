---
id: task_025
category: general_analysis
char_count: 3122
redaction: org-names-agents-pii-strategy-model-ids-removed
---

# service-eval Prompt: Product Billing Strategy — Initial PAYG Concerns

## User Request

User (CEO, ExampleOrgAI) expressed deep frustration with PAYG billing complexity. Key points:

1. Negative prices appearing in the system — "no sense at all"
2. Tracking all internal calls (Scout, orchestrator, etc.) is too big a task
3. Proposed pivot: subscription-first, PAYG deferred
4. Pricing idea: $39.90 normal, $5/month during early beta (security/encryption is prod-ready, UI still has bugs)
5. Weekly usage limits — if exceeded, pay extra or wait for reset
6. Keep PAYG code implemented but hidden (comment out, don't delete)
7. No more free anonymous usage (parking lot)
8. Simplification insight: measure tokens at gateway (what went in, what came out) instead of tracking every internal call. Use average cost per mode.
9. Extended discussion about API vs subscription economics — observing that Provider A/Provider B subscription models subsidize heavy users with inactive subscribers. one panel model Max overages feel exorbitant compared to Provider B API costs for same work.

## Context

### Current billing architecture (13 files, 5 cost calculation points)
- `src/billing/cost_calculator.py` — Core cost calc (single/aggregate/debate modes)
- `src/billing/pricing.py` — YAML-backed pricing lookup
- `src/billing/usage_tracker.py` — Balance deduction + auto-refill
- `src/billing/limit_checker.py` — Balance check before requests
- `src/billing/stripe_provider.py` — Payment processing
- `src/billing/period_manager.py` — Billing period lifecycle
- `src/billing/invoice_manager.py` — Monthly invoice generation
- `src/api/routes/billing.py` — 12+ billing endpoints
- `src/ui/web/streaming_handler.py:959-1087` — Per-request cost with Scout/orchestrator/aggregator/margin
- `src/security/cost_tracker.py` — Free tier enforcement
- `src/llm/scout.py` — Background tier recommendation (billed)
- `src/ui/react/src/components/BillingSection.jsx` — UI: billing dashboard
- `config/model_settings.yaml` — All pricing + billing config

### Known bugs
- Negative prices appearing in UI
- J4: Model customization ignored (Deep mode calls excluded models)
- J5: Hardcoded fallback chain
- J6: DeepSeek standard call hangs but works as fallback

### Recent billing work (agent-psi, Mar 23)
- C1-C5 billing reliability plan complete
- R22/R23 CRITICALs fixed (connection fail-closed, dead-letter security)
- 23 billing tests passing

### Existing PAYG requirements
- REQ-100: PAYG billing (implemented)
- REQ-101: Cost transparency per request (partial)
- REQ-102: Free tier limits (partial)
- REQ-103: Stripe payment integration (implemented)
- REQ-104-109: Various billing infrastructure (implemented)

### Previous pricing decision (Mar 10, now being reversed)
PAYG replaces subscriptions. Single model = 0% margin. Multi-model = 50% margin. $5 free on registration.

### Product context
- Product: encrypted multi-AI chat (product.example.com), 18+ LLM models
- Production on Confidential VMs (europe-west6)
- CODE RED: goal = user uses Product as daily-driver AI chat
- Team: ~10 agents on Product, agent-psi handles RAG/backend/billing
