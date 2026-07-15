---
id: task_056
category: code_review
char_count: 2944
redaction: org-names-agents-pii-strategy-labels-removed
---

---
type: code_generation
agent: agent-sigma
repo: service-web
timestamp: 2026-03-28T12:30:00
context: UI implementation — proper file save using File System Access API
---

## User Request

The user wants the Save button in TestRobin's Script Editor to save back to the same file that was imported, not download as a new file. "We know the path. We want to save the same file by default." The user explicitly called the download approach "dumb" and wants proper save/save-as behavior like a real application.

## Context

### Product
TestRobin (service-web repo) — AI-powered test execution automation. Chrome extension + FastAPI backend + React dashboard.

### Component
`dashboard/app.jsx` — ScriptEditorPanel component. The Script Editor lets users write or import test scripts, then execute them.

### Prior State
The Save button used `URL.createObjectURL` + `<a>.click()` which triggers a browser download — does NOT save back to the original file.

### Implementation Approach
Used the File System Access API (`showOpenFilePicker` / `showSaveFilePicker`):
1. Import uses `showOpenFilePicker` to get a persistent `FileSystemFileHandle`
2. Save uses `handle.createWritable()` to write back to the exact same file
3. Button shows "Save" when file handle exists, "Save As" when no file imported
4. Fallback to browser download for browsers without the API

### Key Code Change (dashboard/app.jsx)

```jsx
// Import — gets persistent file handle
const handleImport = async () => {
  if (window.showOpenFilePicker) {
    const [handle] = await window.showOpenFilePicker({
      types: [{ description: "Test scripts", accept: { "text/*": [".txt", ".csv", ".json"] } }],
    });
    setFileHandle(handle);
    const file = await handle.getFile();
    const content = await file.text();
    onTextChange(content);
  }
};

// Save — writes back to same file
const handleSave = async () => {
  if (fileHandle) {
    const writable = await fileHandle.createWritable();
    await writable.write(text);
    await writable.close();
  } else if (window.showSaveFilePicker) {
    const handle = await window.showSaveFilePicker({
      suggestedName: (title || "test_script") + ".txt",
    });
    setFileHandle(handle);
    const writable = await handle.createWritable();
    await writable.write(text);
    await writable.close();
  }
};
```

### Architecture Reference
- Repo: service-web (github.com/example-org/service-web)
- Dashboard: React 18, Babel pre-compiled, served from FastAPI static mount
- No bundler in production — Babel JSX compilation at Docker build time
- File: dashboard/app.jsx (~1340 lines)

### Review Questions
1. Is the File System Access API usage correct? Any edge cases with permissions?
2. Should we handle the case where the user denies write permission after initially granting it?
3. Is the fallback (browser download) sufficient for non-Chrome browsers?
4. Should we show a "saved" confirmation after successful save?
