---
id: task_012
category: code_review
char_count: 1391
redaction: org-names-agents-pii-strategy-labels-removed
---

---
type: ui_feature
agent: agent-sigma
repo: service-web
timestamp: 2026-03-28T16:15:00
context: Screenshot lightbox — click to view full size
---

## User Request

Screenshot thumbnails in the step view are too small to be useful. User wants to click on before/after images and see them full size in a popup/overlay.

## Implementation

Added a lightbox modal to UnifiedStepView in dashboard/app.jsx:
- State: `lightboxSrc` holds the URL of the clicked image
- Before/after `<img>` elements get `cursor: pointer` and `onClick` to set lightboxSrc
- Modal: fixed overlay with dark background (rgba 0,0,0,0.85), image centered with max 95vw/95vh
- Close: click outside image or X button in top-right
- No external dependencies — pure inline React

```jsx
{lightboxSrc && (
  <div onClick={() => setLightboxSrc(null)}
    style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
      background: "rgba(0,0,0,0.85)", display: "flex", alignItems: "center",
      justifyContent: "center", zIndex: 9999, cursor: "pointer" }}>
    <img src={lightboxSrc} style={{ maxWidth: "95vw", maxHeight: "95vh" }} />
    <div style={{ position: "absolute", top: "16px", right: "24px", color: "#fff" }}>x</div>
  </div>
)}
```

## Review Questions
1. Should Escape key also close the lightbox?
2. Should we add zoom/pan for very large screenshots?
3. Should the lightbox show a label (Before/After)?
