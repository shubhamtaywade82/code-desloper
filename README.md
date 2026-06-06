# Code Deslopper

A semantic code cleanup and refactoring skill for AI agents. Removes AI-generated slop while preserving behavior.

## What is this?
Code Deslopper is an Agent Skill that turns your AI coding agent into a conservative, framework-aware refactoring expert. It detects and removes:
- Unnecessary abstractions (one-method services, fake inheritance chains)
- Duplicated logic across files
- Verbose "enterprise" patterns (Manager/Processor/Handler/Coordinator)
- Dead code, unused parameters, placeholder TODOs
- Confusing naming clusters (do_process, execute_action, perform_task)
- Framework misuse (Rails concerns used once, redundant React hooks, pointless TypeScript wrappers, premature Go interfaces, Python ABC overkill)

## Why "Deslopper"?
Because AI-generated code often comes with slop: boilerplate, fake layers, and over-engineering that a human would never write. This skill cleans it up — semantically, not just stylistically.

## Target Stacks
- Ruby / Ruby on Rails
- JavaScript / TypeScript
- React / Next.js
- Node.js
- Python / FastAPI / Flask
- Go (Golang)

## Core Principles
- **Preserve behavior** — If it changes behavior, flag it. Never silently edit.
- **Prove safety** — Usage analysis, test coverage, or dependency proof required.
- **Framework-aware** — Rails rules ≠ JS rules. Each stack has its own cleanup logic.
- **Test-backed** — Every cleanup includes test impact notes.

## How It Works

### Phase 1: Smell Detection
- Scan file tree / changed files
- Parse AST-level patterns
- Classify smells with risk scores (1–5)
- Skip ambiguous or untested code

### Phase 2: Refactor Generation
- Plan minimal safe transformations
- Output structured patch/diff
- Assess regression risks
- Advise on test targets

## Skill Structure
```plain
code-deslopper/
├── SKILL.md                          # Main instructions (loads on activation)
├── references/
│   ├── ruby-rails-patterns.md        # Rails-specific anti-patterns
│   ├── js-ts-patterns.md             # JS/TS/React anti-patterns
│   ├── python-patterns.md            # Python-specific anti-patterns
│   ├── go-patterns.md                # Go-specific anti-patterns
│   └── safety-checklist.md           # Pre-refactor guardrails
└── scripts/
    └── smell-detector.py             # Optional CLI smell scanner
```

## Installation

### Claude Code
```bash
/plugin marketplace add your-org/code-deslopper
```

### Cursor
Copy `SKILL.md` content into `.cursor/rules/code-deslopper.md`.

### Generic Agent Skills Client
```bash
git clone https://github.com/your-org/code-deslopper.git
# Point your agent's skills provider to this directory
```

## Usage Example
**User:** "Clean up this AI-generated Rails code."

**Agent (using Code Deslopper):**
1. Scans the repo and detects:
   - `UserRegistrationService` (trivial, risk 2)
   - `OrderProcessor` + `OrderHandler` (fragmented, risk 3)
   - `BaseService` inheritance chain (fake, risk 3)
2. Presents smell report with risk scores.
3. After approval, generates patches:
   - Collapses `UserRegistrationService` into model method
   - Merges order classes into single transaction object
   - Removes `BaseService` chain, inlines shared logic
4. Outputs test impact and risk notes.

## Output Format
Every response follows this structure:
- **## Cleanup Summary**
- **## Smells Found**
- **## Safe Refactor Plan**
- **## Proposed Patch**
- **## Test Impact**
- **## Risk Notes**

## Safety Rules

| Action | Rule |
|---|---|
| **Proceed** | Risk ≤2, tests exist, local change, no API/hook touched |
| **Ask** | Risk 3, cross-file, partial tests, callbacks involved |
| **Stop** | Risk ≥4, no tests, touches auth/payment/billing, public API change |

## License
MIT
