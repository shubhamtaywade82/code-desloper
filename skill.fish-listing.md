# Skill.Fish Listing — Code Deslopper

**Title:** Code Deslopper — AI Code Cleanup & Refactor

**Short Description:** Remove AI-generated code slop, fake abstractions, and duplication from Ruby/Rails, JS, TS, React, Python & Go while preserving behavior.

**Full Description:**
Code Deslopper is a semantic cleanup skill, not a formatter. It removes AI-generated noise from your codebase while keeping your code safe.

### What it cleans
- Trivial one-method Service / Manager / Handler classes
- Fake BaseService inheritance chains with no polymorphism
- Duplicated methods, validations, and utility functions
- Empty wrapper components, redundant useMemo, and derived state
- Nested if-else pyramids and callback hell
- Over-commented obvious code and inconsistent naming clusters
- Redundant TypeScript any types and pointless DTOs
- Unnecessary Rails concerns and scope-vs-service confusion
- Premature abstractions in Go & Python ABC overkill

### What it never touches
- Public APIs, authorization, validations, business rules
- Side effects (DB, network, jobs) — order preserved
- Framework hooks (callbacks, middleware, observers)
- Test coverage boundaries

### How it works
Two-phase workflow:
1. **Smell Detection** — scans files, classifies risks 1–5, produces a report
2. **Refactor Generation** — minimal safe patches with diff output, test impact notes, and risk warnings

### Target stacks
Ruby, Ruby on Rails, JavaScript, TypeScript, React, Node.js, Python, Go

### Output format
Every run produces:
- Cleanup Summary
- Smells Found
- Safe Refactor Plan
- Proposed Patch
- Test Impact
- Risk Notes

**Tags:** `refactoring`, `code-cleanup`, `ruby`, `rails`, `javascript`, `typescript`, `react`, `nodejs`, `python`, `go`, `ai-cleanup`, `deslop`, `code-review`, `dead-code-removal`
