# MCP Market Listing: Code Deslopper

**Title:** Code Deslopper — AI Code Cleanup & Refactor Skill

**Category:** Developer Tools

**Description:**
Code Deslopper is a semantic cleanup tool that helps developers maintain clean, idiomatic codebases in the age of AI-assisted development. It identifies and removes common "AI slop" patterns such as:
- Over-engineered service objects in Rails and Python.
- Redundant `useMemo`/`useCallback` hooks in React.
- Premature interface abstractions in Go.
- Fake abstraction layers and placeholder scaffolding.
- Inconsistent naming and duplicated logic.

**Features:**
- **Safety First:** Built-in safety checklist and risk assessment guide.
- **Behavior Preservation:** Focuses on refactoring that maintains identical observable behavior.
- **Automated Scanning:** Includes a python-based smell detector for quick codebase analysis.
- **Structured Reports:** Provides clear, actionable reports before any changes are made.

**Instructions:**
1. Point your agent's Skill Provider to the repository.
2. Activate the skill using `activate_skill code-deslopper`.
3. Run an analysis on your source directory.

**Safety Rules:**
- Never refactors high-risk (Score 3+) items without explicit confirmation.
- Prioritizes existing test coverage as a safety net.
- Preserves all public API contracts.
