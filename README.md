# Code Deslopper — AI Code Cleanup & Refactor

Semantic code cleanup and refactoring assistant that removes AI-generated code smells, unnecessary abstractions, duplication, and framework misuse from Ruby/Rails, JavaScript, TypeScript, and React codebases while preserving observable behavior.

## Overview

Code Deslopper is an **Agent Skill** designed to help developers clean up "code slop" — the verbose, redundant, or non-idiomatic code often produced by AI assistants. It follows a safety-first, two-phase workflow: **Detect** then **Refactor**.

## Key Features

- **Semantic Awareness:** Understands the difference between a necessary Rails callback and a redundant AI-generated wrapper.
- **Safety-First:** Uses a risk-scoring system (1–5) to categorize smells and requires explicit approval for high-risk changes.
- **Framework-Specific:** Includes deep knowledge of Ruby on Rails, React, and TypeScript idioms.
- **Two-Phase Workflow:** Prevents "blind" refactoring by requiring a detection report before any code is touched.

## Installation

### For Gemini CLI / Agent Skills compatible agents
Copy the `SKILL.md` and the `references/` directory into your agent's skills path or use the provider directly.

### For Cursor
Copy `SKILL.md` into `.cursor/rules/code-deslopper.md`.

## Directory Structure

- `SKILL.md`: Core instructions for the agent.
- `references/`: Detailed pattern guides.
    - `ruby-rails-patterns.md`: Rails-specific anti-patterns.
    - `js-ts-patterns.md`: JS/TS/React anti-patterns.
    - `python-patterns.md`: Python-specific anti-patterns.
    - `go-patterns.md`: Go-specific anti-patterns.
    - `safety-checklist.md`: Pre-refactor safety guardrails.
- `scripts/`: Optional tools.
    - `smell-detector.py`: CLI tool for scanning codebases.

## Usage

1. **Activate the skill** (e.g., `activate_skill code-deslopper`).
2. **Phase 1: Detect** - Ask the agent to analyze a file or directory for smells.
3. **Phase 2: Refactor** - Review the report and approve specific refactors.

## License

MIT
