# AGENTS.md

## Scope

These instructions apply to the entire repository rooted at this directory.

## General

- Prefer concise Chinese when replying to the user, unless the user asks for another language.
- Read only the files needed for the current task. Do not bulk-read the whole repo.
- Before editing code, inspect the relevant files first.
- Prefer `rg` / `rg --files` for search.
- Use non-destructive commands by default.

## Project Notes

- Backend entry: `main.py`
- Frontend workspace: `static/`
- Frontend dev URL is usually `http://localhost:5173/`
- Backend API is usually on port `5000`

## MCP Usage

This workspace is configured with two browser MCPs:

1. `mcp__playwright__*`
2. `mcp__chrome-devtools__*`

Use them with clear division of responsibility instead of mixing them randomly.

## Playwright MCP

Prefer `Playwright MCP` for user-like interaction and functional UI testing.

- Use it for:
  - opening pages
  - clicking buttons, tabs, links
  - typing into forms
  - running short end-to-end UI flows
  - taking interaction-oriented snapshots/screenshots
- Prefer it when the goal is:
  - "test whether the page works"
  - "reproduce the user path"
  - "verify a control can be clicked"

Guidelines:

- Use role/text/ref-based actions when possible.
- Keep flows short and deterministic.
- Avoid repeatedly requesting full-page snapshots if a single action result is enough.
- If token cost matters, do not overuse `browser_snapshot` after every step.

## Chrome DevTools MCP

Prefer `Chrome DevTools MCP` for browser-side debugging and inspection.

- Use it for:
  - console inspection
  - network request inspection
  - page structure snapshots
  - performance or low-level browser debugging
  - request-level investigation
- Prefer it when the goal is:
  - "find frontend errors"
  - "inspect polling / xhr / fetch traffic"
  - "check what the browser is actually loading"
  - "analyze console warnings"

Guidelines:

- Prefer DevTools MCP over Playwright MCP for network-heavy analysis.
- Use filtered request listing where possible instead of dumping everything.
- Use console listing before guessing about frontend failures.

## Recommended Split

Default workflow:

1. Use `Playwright MCP` to perform the interaction.
2. Use `Chrome DevTools MCP` to inspect console/network/performance.
3. Return a combined conclusion to the user.

If token efficiency matters:

- Default to `Chrome DevTools MCP` for inspection.
- Use `Playwright MCP` only for the minimum set of actions needed to trigger the state.

## QA Expectations

When asked to test a page, cover at least:

- page loads successfully
- major interactive controls respond
- console errors are checked
- key network requests are checked when relevant
- one or more screenshots or snapshots are captured when evidence is needed

