---
name: browser-testing-with-agent-browser
description: End-to-end browser testing and UI verification using Chiper's native agent-browser CLI (/usr/local/bin/agent-browser). Use when testing web applications, verifying UI components, inspecting DOM accessibility trees, capturing screenshots, debugging console errors, and profiling Core Web Vitals with real runtime data. Runs directly via terminal tool.
---

# Browser Testing with agent-browser

## Overview

Use Chiper's native `agent-browser` CLI to verify web applications in a real headless Chromium browser. This bridges the gap between static code analysis and live browser execution — the agent can see what the user actually sees, click interactive elements, capture console errors, and measure real Web Vitals.

Binary location on host: `/usr/local/bin/agent-browser` (with Chromium 157 runtime).

## When to Use

- Verifying web interfaces, dashboards, or landing pages after implementation or refactoring
- Testing user interaction flows (login, form submissions, navigation, buttons, modals)
- Capturing screenshots as verifiable proof of UI delivery
- Inspecting runtime DOM, JavaScript console logs, or network errors
- Measuring real Core Web Vitals (LCP, CLS, FID/INP, TTFB)
- Verifying accessibility (a11y) tree structure

**When NOT to use:**
- Pure backend APIs or CLI tools with no web interface (use `curl` or `pytest` instead)
- Unit-level component tests that belong in Jest/Vitest/Playwright test suites

---

## The Core Workflow

Every browser testing session follows this disciplined loop:

```text
OPEN ──▶ SNAPSHOT ──▶ INTERACT ──▶ VERIFY ──▶ SCREENSHOT ──▶ CLOSE
```

### 1. Launch & Navigate
Open the target URL via `terminal`:

```bash
agent-browser open "http://localhost:3000"
```

For dark mode or custom viewports:
```bash
agent-browser --color-scheme dark open "http://localhost:3000"
agent-browser set viewport 1280 800
```

### 2. Inspect Accessibility Tree (The AI's Eyes)
Inspect the interactive elements on the page. The `-i` flag returns an interactive tree where every element is assigned an `@ref` handle (e.g. `@e1`, `@e2`):

```bash
agent-browser snapshot -i
```

Example output:
```text
button "Submit" [ref=@e1]
textbox "Email" [ref=@e2]
link "Dashboard" [ref=@e3]
```

### 3. Interact with Elements
Use the `@ref` identifiers from the snapshot to interact safely:

```bash
# Fill input fields
agent-browser fill @e2 "test@example.com"

# Click buttons or links
agent-browser click @e1

# Wait for dynamic network requests to settle
agent-browser wait 2000
```

### 4. Capture Evidence & Check Errors
Never declare a page "working" without checking runtime errors and console logs:

```bash
# Check JavaScript errors
agent-browser errors

# Check console logs
agent-browser console

# Capture full page screenshot
agent-browser screenshot /tmp/ui-verification.png
```

To display the image in chat: include `MEDIA:/tmp/ui-verification.png` or `![UI Verification](/tmp/ui-verification.png)`.

### 5. Measure Core Web Vitals (Zero Guesswork)
Audit actual runtime performance rather than guessing numbers:

```bash
agent-browser vitals "http://localhost:3000" --json
```

### 6. Clean Up
Always close the browser session when testing is complete:

```bash
agent-browser close
```

---

## Anti-Rationalization & Red Flags

| Rationalization (Excuses AI Makes) | Rebuttal (Strict Rule) |
| :--- | :--- |
| *"I read the HTML/JSX code, so I know the UI is fine."* | **REJECTED:** Static JSX does not prove JavaScript ran, styles loaded, or layout rendered without collisions. Run `agent-browser snapshot -i`. |
| *"The HTTP server returned 200 OK, so the frontend works."* | **REJECTED:** 200 OK only proves HTML was served. It misses blank white screens, React hydration errors, and broken CSS. Run `agent-browser errors`. |
| *"I'm in a headless environment so I can't test browser UI."* | **REJECTED:** `agent-browser` runs headless Chromium natively on this VPS with no display server required. |

---

## Verification Checklist

Before reporting completion on a frontend task, verify:
- [ ] Navigated to the page with `agent-browser open`
- [ ] Confirmed UI state with `agent-browser snapshot -i`
- [ ] Executed key interaction (click/fill) and waited for response
- [ ] Verified `agent-browser errors` is empty (no unhandled exceptions)
- [ ] Produced verifiable screenshot via `agent-browser screenshot`
- [ ] Closed browser with `agent-browser close`
