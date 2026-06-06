# MCP Market Listing — Code Deslopper

**Title:** Code Deslopper — AI Code Cleanup & Refactor Skill
**Category:** Developer Tools
**Version:** 1.0
**License:** MIT

## Description
A semantic code cleanup skill that removes AI-generated slop, unnecessary abstractions, duplicated logic, and framework misuse from Ruby/Rails, JavaScript, TypeScript, React, Python, and Go codebases — while strictly preserving observable behavior.

## Key Features
- **Behavior-first refactoring:** Never changes behavior without flagging it
- **Two-phase workflow:** Detect smells → Generate safe patches
- **Framework-aware:** Rails/Python conventions respected; JS/TS/Go idioms enforced
- **Risk scoring:** 1–5 scale with clear proceed/ask/stop rules
- **Test impact notes:** Every cleanup includes what to test
- **Structured output:** Summary, smells, plan, patch, tests, risks

## Supported Stacks
- Ruby / Ruby on Rails
- JavaScript / TypeScript
- React / Next.js
- Node.js
- Python / FastAPI / Flask
- Go (Golang)

## What It Removes
- One-method service/manager/handler classes
- Fake BaseService inheritance chains
- Duplicated functions, validations, utilities
- Empty wrapper components & redundant React hooks
- Nested if-else pyramids & callback hell
- Over-commenting & inconsistent naming clusters
- Redundant TypeScript types & pointless DTOs
- Unnecessary Rails concerns & scope confusion
- Premature abstractions in Go & Python ABC overkill

## Safety Guardrails
- Public APIs, auth, validations, and business rules are protected
- Side effects (DB, network, jobs) are preserved in order
- Framework hooks (callbacks, middleware) are never bypassed
- No cleanup without usage proof or test coverage
- Risk-score ≥3 requires explicit approval

## Installation
Compatible with any Agent Skills-compatible client (Claude Code, Cursor, Gemini CLI, Codex, etc.). Install as a skill folder with `SKILL.md` + `references/` + optional `scripts/`.

## Usage
Activate when:
- Cleaning up AI-generated PRs
- Refactoring over-engineered code
- Removing dead code and ghost files
- Consolidating duplicated logic
- Preparing code for production review
