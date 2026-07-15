---
id: task_037
category: general_analysis
char_count: 709
redaction: org-names-agents-pii-strategy-labels-removed
---

---
type: process_directive
agent: agent-sigma
repo: service-web
timestamp: 2026-03-28T18:05:00
context: User mandated the full development process — requirement → confirm → implement → PR → panel review (2 cycles) → merge → deploy
---

## User Directive

The mandatory process for all agents:

1. Create/update requirement based on user input
2. Confirm requirement with user
3. Implement on branch
4. Commit + create PR to main
5. panel review (7-model)
6. Fix findings
7. Second panel review
8. Merge (after 2 clean review cycles, or with --no-verify after 2 attempted cycles)
9. Deploy from main only

No step may be skipped. Today's example: merged without review, panel immediately found critical bugs.
