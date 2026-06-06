# Safety Checklist & Risk Assessment

Before applying any refactor, use this checklist to score the risk and ensure behavior preservation.

## Risk Scoring (1–5)

| Score | Impact | Requirements |
|---|---|---|
| **1** | Low/Trivial | Local change, idiomatic cleanup, no logic change. |
| **2** | Minor | Small logic simplification, no API change. |
| **3** | Moderate | Significant refactor, multiple files, shared utility change. |
| **4** | High | Changes core logic, involves database or network side effects. |
| **5** | Critical | Changes public API contracts or mission-critical auth/security. |

## Pre-Refactor Checklist

- [ ] **Test Coverage:** Are there existing tests for the code? (Run them first).
- [ ] **Public API:** Does this method/class get called from outside the module?
- [ ] **Side Effects:** Does this code touch the DB, File System, or Network?
- [ ] **Framework Hooks:** Is this a Rails callback, React lifecycle hook, or Middleware?
- [ ] **Metaprogramming:** Is the code being refactored called dynamically (e.g., `send(method_name)`)?
- [ ] **Hidden Coupling:** Is this code used in views or external scripts?

## Decision Matrix

- **Score 1-2:** Safe to propose and apply after a quick manual review.
- **Score 3:** Requires detailed "Before & After" explanation and test verification.
- **Score 4:** Requires "Must Ask" flag. Do not proceed without explicit user confirmation of the risk.
- **Score 5:** Do not refactor unless explicitly instructed. Propose an alternative strategy (e.g., "This should be a new feature/PR").

## Rollback Plan

Always ensure you can revert to the previous state.
1. `git stash` or `git checkout` before starting.
2. Run tests immediately after change.
3. Verify the "Observable Behavior" remains identical.
