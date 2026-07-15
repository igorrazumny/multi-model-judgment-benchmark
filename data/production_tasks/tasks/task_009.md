---
id: task_009
category: architecture
char_count: 3304
redaction: org-names-agents-pii-strategy-labels-removed
---

# service-eval Prompt: Product Subscription Tier Design + Requirements

## User Request

User finalized subscription pricing and flow, then asked to create requirements and send to Link (SM):

### Pricing Tiers (finalized)
| Tier | Full Price | Beta (80% off) | Usage multiplier |
|------|-----------|----------------|-----------------|
| Starter | $29.90/mo | $5.98/mo | 1x (base) |
| Pro | $89.90/mo | $17.98/mo | 6x Starter |
| Power | $179.90/mo | $35.98/mo | 24x Starter (4x Pro) |

### User Flow (finalized)
1. Homepage: 10 free requests without registration
2. After 10: registration/sign-in wall (history must NOT be lost — currently broken)
3. After registration: 1 week free trial with limited usage
4. At trial end: recommend tier based on usage
5. User can subscribe during trial to lock in beta discount
6. After trial without subscription: blocked

### Beta Discount Strategy
- 80% off during early beta — "we're not lying, these are the real prices"
- Security/encryption is production-ready (no discount for that)
- UI still has bugs — that's why the discount
- Users warned in advance before discount changes
- Reserve right to change pricing

### Cost Tracking Simplification
- Remove per-request cost display from UI
- Continue tracking tokens sent/received in background
- Calculate average cost per token across all models
- Track per-model (single-model = bigger allowance)
- Monthly: compare GCP/API spend vs total tokens to calibrate

### Delegation
- Create requirements (REQ-110 through REQ-116)
- Send to Link to rearrange backlog
- agent-psi handles cost-related implementation
- Link assigns UI/Stripe/auth items to other agents

## Context

### Requirements created
- REQ-110 (P0): Subscription billing — 3 tiers, Stripe, weekly limits
- REQ-111 (P0): Anonymous request limit — 10 free, then registration
- REQ-112 (P0): Free trial — 1 week post-registration
- REQ-113 (P1): Session history preserved across sign-in
- REQ-114 (P0): Hide PAYG UI elements
- REQ-115 (P1): Subscription usage meter
- REQ-116 (P2): Simplified cost tracking (gateway tokens only)

### Deprecated requirements
- REQ-100 (PAYG billing) → REQ-110
- REQ-101 (per-request cost) → REQ-116
- REQ-102 (free tier) → REQ-111 + REQ-112
- REQ-103 (Stripe top-up) → REQ-110
- REQ-107 (billing display) → REQ-114 + REQ-115

### Billing code map (from exploration)
```
src/billing/
├── cost_calculator.py    ← 5 calculation modes (single/aggregate/debate/etc)
├── pricing.py            ← YAML-backed pricing
├── usage_tracker.py      ← Balance deduction + auto-refill (PAYG-specific)
├── limit_checker.py      ← Tier-based limit enforcement
├── stripe_provider.py    ← Payment processing
├── period_manager.py     ← Billing cycles
├── invoice_manager.py    ← Monthly invoices
└── user_manager.py       ← User sync + trust levels
src/api/routes/billing.py ← 12+ endpoints
src/ui/web/streaming_handler.py:959-1087 ← Per-request cost calc
src/security/cost_tracker.py ← Free tier enforcement
config/model_settings.yaml ← Pricing + billing config
src/ui/react/src/components/BillingSection.jsx ← UI dashboard
```

### Team context
- agent-psi: RAG engine, backend, billing — will handle REQ-114, REQ-116
- Link: Product SM — will prioritize and assign remaining REQ-110-115
- Product CODE RED: all hands on go-live
