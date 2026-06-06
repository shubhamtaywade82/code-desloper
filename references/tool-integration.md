# Tool Integration — Code Deslopper Phase 1 Pipeline

Code Deslopper sits **on top of** RuboCop, RubyCritic, Reek, Flay, and Solargraph.
These tools are automated Phase 1 amplifiers. The skill provides what they cannot:
semantic reasoning about AI-specific patterns and safe refactoring plans.

---

## Ruby Tool Mapping

| Tool | What It Detects | Gap for Code Deslopper | How to Use It |
|---|---|---|---|
| **RuboCop** | Style violations, ABC complexity, cyclomatic complexity, Rails cops | Doesn't understand semantic slop (fake services, fragmented orchestration, AI naming noise). Style-first, not architecture-first. | Run `rubocop --only Metrics,Style,Layout` as a pre-filter. Flag files with high complexity scores for deeper semantic review. |
| **RubyCritic** (Reek + Flay + Flog) | Reek: Feature Envy, Utility Function, Too Many Statements, Nested Iterators. Flay: structural duplication. Flog: method complexity. | Reek's Feature Envy hints at service objects that should be model methods. Flay finds duplicate logic. But it doesn't know Rails conventions or React patterns. | Use Reek output to seed the smell list. Use Flay to find duplicate functions across files. |
| **Reek** | Code smells: Feature Envy, TooManyMethods, UncommunicativeVariableName, DuplicateMethodCall, NestedIterators | Doesn't catch AI architectural patterns: trivial services, fake inheritance, fragmented orchestration. | Run as secondary scan. Feed JSON output into Code Deslopper as context. |
| **Flay** | Structural duplication (same AST shape, different surface text) | Finds code that looks different but is structurally identical. Doesn't catch semantic duplication across different call signatures. | Use to find duplicate functions across files. |
| **Solargraph** | Type inference, go-to-definition, find references, unused methods/variables | Excellent for safety checks — finding all call sites, proving a method is unused, tracing inheritance. | Use in Phase 1 to prove a method has no callers. Use in Phase 2 to verify no cross-file breakage after refactoring. |
| **Rails Best Practices gem** | Fat model/skinny controller, scope access, virtual attributes, factory methods | Dated, has false positives, doesn't understand modern patterns (service objects, query objects). | Run as secondary scan. Use "use scope access" and "replace complex creation" hints as smell candidates. |
| **Brakeman** | SQL injection, XSS, mass assignment, dangerous redirects, command injection | Security-focused only. No refactoring guidance. | Always run Brakeman first. Any Brakeman finding is Risk 5 — stop and fix before deslopping. |
| **ESLint / typescript-eslint** | JS/TS style, `no-explicit-any`, `react-hooks/exhaustive-deps`, unused vars | Catches missing deps and `any`, not unnecessary memoization, empty wrappers, or derived state. | Run as pre-filter. Feed violations as Phase 1 context. |

---

## What Tools Miss (AI-Specific Slop)

These are the patterns Code Deslopper targets that **no existing tool catches**:

| AI Slop Pattern | Why Standard Tools Miss It |
|---|---|
| Trivial one-method service | RuboCop sees a 3-line class — perfectly valid. Reek sees no smell. No tool flags "this class only proxies `User.create`." |
| Fake `BaseService` inheritance | Solargraph sees the inheritance chain. RuboCop sees valid syntax. No tool says "this chain has zero polymorphism — delete it." |
| Fragmented orchestration | 3 separate classes each doing one step. Reek sees 3 clean classes. Flay sees no duplication. No tool sees they should be one transaction. |
| Verb-inflation naming (`do_process`, `execute_action`) | RuboCop enforces snake_case. It doesn't detect semantic naming noise. |
| Empty React wrapper components | ESLint/React plugins don't flag `<div>{children}</div>` as a pointless wrapper. |
| Redundant `useMemo` / derived state | `react-hooks/exhaustive-deps` catches missing deps, not unnecessary memoization. |
| TypeScript pointless DTOs | `no-explicit-any` catches `any` but not "this DTO mirrors the API exactly and adds nothing." |
| Enterprise suffix abuse | `Manager`/`Coordinator`/`Handler` for trivial classes — all linters accept them. |

---

## Phase 1 Automated Scanning Pipeline

### Ruby / Rails Full Pipeline

```bash
# 1. Brakeman — security (run FIRST; any finding = Risk 5, stop)
bundle exec brakeman --format json --output brakeman.json

# 2. RuboCop — complexity, style, Rails-specific cops
bundle exec rubocop --format json --out rubocop.json app/ lib/ config/

# 3. RubyCritic — combined Reek + Flay + Flog report
bundle exec rubycritic --format json --no-browser app/ lib/ -p rubycritic.json

# 4. Reek — semantic code smells (standalone for detail)
bundle exec reek --format json app/ lib/ > reek.json

# 5. Flay — structural duplication
bundle exec flay app/ lib/ > flay.txt

# 6. Flog — method complexity scores (pain threshold)
bundle exec flog app/ lib/ > flog.txt

# 7. Rails Best Practices
bundle exec rails_best_practices --format json --output-file rbp.json .

# 8. Traceroute — dead routes and controller actions
bundle exec rake traceroute > traceroute.txt

# 9. Solargraph — unused methods, call sites
solargraph scan --unused > solargraph_unused.json

# Feed to Code Deslopper:
# "Here is rubocop.json, reek.json, flay.txt, flog.txt, rbp.json.
#  Run AI-specific smell detection on top and produce a unified smell report."
```

### JS/TS Pipeline

```bash
npx eslint . --ext .js,.jsx,.ts,.tsx --format json -o eslint.json
npx tsc --noEmit --pretty false > tsc-errors.txt
npx jscpd --reporters json --output ./jscpd-report .
npx knip --json > knip.json
npx ts-prune --json > ts-prune.json
npx unimported --json > unimported.json
npx depcheck --json > depcheck.json
```

### Python Pipeline

```bash
ruff check --select E,W,F,I,UP,ANN --output-format json . > ruff.json
pylint --output-format=json app/ > pylint.json
mypy --strict --show-error-codes . 2>&1 > mypy.txt
vulture app/ > vulture.txt
bandit -r app/ -f json > bandit.json
radon cc app/ -s -j > radon.json
```

Then feed all output to Code Deslopper:

> "Here are the RuboCop complexity scores [paste rubocop.json], Reek smell report [paste reek.json],
> Flay duplication hits [paste flay.txt], and Solargraph unused methods [paste solargraph_unused.json].
> Now run AI-specific smell detection on top of this and produce a unified smell report."

---

## How Code Deslopper Uses Tool Output

### Cross-Reference for Higher Confidence

```
Reek: FeatureEnvy in UserRegistrationService#call
  + Solargraph: UserRegistrationService has zero external callers except UsersController
  → Code Deslopper: Trivial service, Risk 2 — safe to inline

Flog: OrderProcessor#call scores 8 (low)
  + Flog: OrderHandler#call scores 7 (low)
  + Code Deslopper: Reads both files, sees they're always called in sequence
  → Code Deslopper: Fragmented orchestration, Risk 3 — merge into OrderCheckout

RuboCop: AbcSize 28 on PaymentService#process
  + Reek: TooManyStatements in PaymentService#process
  + Code Deslopper: Reads method, counts 3 distinct responsibilities
  → Code Deslopper: Long Method + Divergent Change, Risk 3 — extract sub-methods
```

### Filter False Positives

```
RuboCop: AbcSize 35 on TaxCalculation#calculate
  → Code Deslopper reads it: complex business rule, all branches essential
  → Code Deslopper: Skip — this is essential complexity, not a smell

Reek: FeatureEnvy in InvoicePresenter#formatted_total
  → Code Deslopper reads it: presenter pattern — FeatureEnvy is expected
  → Code Deslopper: Skip — pattern is intentional
```

### Add Missing AI Smells

After tool output is processed, Code Deslopper runs its own detection layer:
- Reads all service objects and checks for trivial delegation
- Finds all inheritance chains and verifies polymorphism exists
- Checks for fragmented orchestration patterns across controllers
- Audits React components for wrapper bloat and derived state

---

## Phase 2 Safety Verification with Solargraph

Before emitting a patch, use Solargraph to verify:

```ruby
# 1. No other callers exist
solargraph_unused.json includes UserRegistrationService → safe to delete

# 2. Cross-file references don't break
# After inlining UserRegistrationService: does UsersController still resolve User.create?
solargraph api --method User.create  # verify it's reachable

# 3. is_a? checks won't break
grep -r "is_a?(BaseService)" app/ spec/  # zero hits → safe to delete

# 4. Spec coverage exists
find spec/ -name "*user_registration*"  # ensure spec exists before refactoring
```

---

## Recommended Production Pipeline

```
Layer         | Tool                    | Purpose
──────────────┼─────────────────────────┼────────────────────────────────────
CI gate 1     | Brakeman                | Block PRs with security issues
CI gate 2     | RuboCop                 | Block PRs with style violations
CI gate 3     | RubyCritic (Flog)       | Block PRs with methods scoring > 20
Smell input   | Reek + Flay             | Feed findings into Code Deslopper Phase 1
Safety input  | Solargraph              | Prove unused methods, trace call sites
Semantic layer| Code Deslopper skill    | Catch AI-specific patterns, plan safe patches
```

---

## Example: Tool + Skill Working Together

**Scenario:** AI generated `OrderProcessor`, `OrderHandler`, `OrderManager` in a Rails app.

**RuboCop output:** All 3 classes pass — short, clean, no style violations.

**Reek output:** No smells detected — each class is simple and focused.

**Flay output:** No duplication — each class does something different.

**Code Deslopper:**
- Reads the 3 files. Sees each has one public method.
- Sees they are always called in sequence in `OrdersController#checkout`.
- Cross-references with Solargraph: no other call sites.
- Flags: *"Fragmented orchestration — these 3 classes represent one transaction workflow. Risk 3.
  Merge into `OrderCheckout` transaction object."*
- Proposes the merge patch with transaction boundary preserved.

**Result:** Without the skill, tools say "all good" and the slop stays.
With the skill, the semantic pattern is caught and safely fixed.

---

## JavaScript / TypeScript Tool Mapping

| Tool | What It Detects | AI Slop It Catches | How to Feed Into Deslopper |
|---|---|---|---|
| **ESLint + @typescript-eslint** | Style, complexity, type-aware rules | `any` abuse, `// @ts-ignore` spam, empty catch blocks, `no-unused-vars` | `eslint --format json` → parse for `no-explicit-any`, `no-empty-function`, `no-unused-vars` |
| **Biome** | Ultra-fast linter/formatter (Rust-based) | Complexity, dead code, suspicious code | `biome check --json` → feed complexity scores and diagnostics |
| **tsc** | Type errors, implicit `any`, missing return types | `any` inference, untyped parameters, missing return types | `tsc --noEmit --pretty false` → parse `TS7006` (implicit any), `TS2345` (arg mismatch) |
| **jscpd** | Copy-paste detection | Duplicated functions, duplicated React components, utility logic | `jscpd --reporters json` → direct input for "duplicate functions" smell |
| **eslint-plugin-sonarjs** | Cognitive complexity, duplicate branches | Nested if-else pyramids, duplicated switch cases | `cognitive-complexity` score > 15 → flag for flattening |
| **Knip** | Unused exports, unused deps, unused files | Dead code at module level — exports no one imports | `knip --json` → prove a file/module is safe to delete |
| **ts-prune** | Unused TypeScript exports | Dead exported functions, types, interfaces | `ts-prune --json` → feed into "dead code" smell |
| **unimported** | Files not imported by entry points | Ghost files, orphaned modules | `unimported --json` → direct "dead file" candidates |
| **depcheck** | Unused npm dependencies | AI-installed packages not actually used | `depcheck --json` → remove from `package.json` |

### What JS/TS Tools Miss (AI-Specific Slop)

| AI Slop Pattern | Why ESLint/Biome Doesn't Flag It |
|---|---|
| Empty wrapper component | `<CardWrapper>{children}</CardWrapper>` is valid JSX — no lint rule |
| Redundant `useMemo`/`useCallback` | `exhaustive-deps` checks dep arrays, not whether memoization is needed |
| Derived state in `useState` | `useState(props.x + props.y)` is perfectly valid React |
| One-method "manager" class | Valid OOP — no rule flags a class as unnecessary |
| Pointless DTOs mirroring API | Valid TypeScript interfaces — no structural redundancy check |
| Prop drilling through 3+ layers | Valid React pattern, no lint rule |
| Nested `.then()` chains | Valid Promise code — no complexity violation |

### Phase 1 JS/TS Pipeline

```bash
# Style + type + complexity
npx eslint . --ext .js,.jsx,.ts,.tsx --format json -o eslint.json
npx tsc --noEmit --pretty false > tsc-errors.txt

# Copy-paste detection
npx jscpd --reporters json --output ./jscpd-report .

# Dead code detection
npx knip --json > knip.json
npx ts-prune --json > ts-prune.json
npx unimported --json > unimported.json

# Unused dependencies
npx depcheck --json > depcheck.json
```

### Phase 2 JS/TS Safety Verification

```bash
# After applying a patch:
npx tsc --noEmit                    # No type breakage
npx vitest run --coverage           # Tests pass, paths covered
npx knip --json                     # Deleted export now truly unused
npx playwright test                 # E2E if React components touched
```

### Recommended ESLint Config for AI Slop Detection

```js
// eslint.config.js
import sonarjs from 'eslint-plugin-sonarjs';
import ts from 'typescript-eslint';

export default [
  ...ts.configs.strict,
  sonarjs.configs.recommended,
  {
    rules: {
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      'sonarjs/cognitive-complexity': ['warn', 15],
      'sonarjs/no-duplicate-string': 'warn',
      'react/jsx-no-useless-fragment': 'warn',
      'react-hooks/exhaustive-deps': 'warn',
      'import/no-unused-modules': ['warn', { unusedExports: true }],
      'import/no-cycle': 'error',
    },
  },
];
```

---

## Python Tool Mapping

| Tool | Command | What to Feed Deslopper |
|---|---|---|
| **Ruff** | `ruff check --select E,W,F,I,UP,ANN --output-format json .` | Style + complexity + unused import flags |
| **Pylint** | `pylint --output-format=json app/` | Unreachable code, too-many-args, too-many-branches |
| **mypy** | `mypy --strict --show-error-codes .` | `Any` abuse, missing types, incompatible overrides |
| **Bandit** | `bandit -r app/ -f json` | Security: bare except, eval, hardcoded passwords |
| **Vulture** | `vulture app/` | Dead code: unused functions, classes, variables |
| **Radon** | `radon cc app/ -s -j` | Cyclomatic complexity per function |

### Phase 1 Python Pipeline

```bash
ruff check --select E,W,F,I,UP,ANN --output-format json . > ruff.json
pylint --output-format=json app/ > pylint.json
mypy --strict --show-error-codes . 2>&1 > mypy.txt
vulture app/ > vulture.txt
bandit -r app/ -f json > bandit.json
radon cc app/ -s -j > radon.json
```

---

## Complete Production Pipeline by Stack

### Ruby / Rails
```
CI gate 1     | Brakeman                      | Block PRs with security issues
CI gate 2     | RuboCop + rubocop-rails        | Block PRs with style/complexity violations
CI gate 3     | RuboCop + rubocop-performance  | Block PRs with N+1 / performance patterns
CI gate 4     | RubyCritic (Flog > 20)         | Block PRs with high-complexity methods
Smell input   | Reek + Flay + Rails BP         | Feed findings into Code Deslopper Phase 1
Dead code     | Traceroute + Solargraph        | Find dead routes, unused methods
Safety verify | RSpec + Bullet + Brakeman      | Prove refactor is safe and N+1-free
Semantic      | Code Deslopper skill           | Catch AI-specific patterns, plan safe patches
```

### Recommended `.rubocop.yml` for AI Slop Detection

```yaml
require:
  - rubocop-rails
  - rubocop-performance
  - rubocop-rspec

AllCops:
  TargetRubyVersion: 3.2
  NewCops: enable

Metrics/ClassLength:
  Max: 150
  CountAsOne: ['array', 'heredoc', 'method_call']

Metrics/MethodLength:
  Max: 20
  CountAsOne: ['array', 'heredoc']

Metrics/AbcSize:
  Max: 20

Metrics/CyclomaticComplexity:
  Max: 10

Metrics/ParameterLists:
  Max: 4
  CountKeywordArgs: true

Rails/Delegate:
  Enabled: true

Rails/FindEach:
  Enabled: true

Rails/HasManyOrHasOneDependent:
  Enabled: true

Rails/InverseOf:
  Enabled: true

Rails/SkipsModelValidations:
  Enabled: true

Rails/RedundantActiveRecordAllMethod:
  Enabled: true

Performance/Detect:
  Enabled: true

Performance/Count:
  Enabled: true

RSpec/ExampleLength:
  Max: 15

RSpec/MultipleExpectations:
  Max: 5

RSpec/NestedGroups:
  Max: 4
```

### JavaScript / TypeScript
```
CI gate 1     | ESLint + tsc          | Block PRs with style violations + type errors
CI gate 2     | SonarJS               | Block PRs with cognitive complexity > 15
Dupe gate     | jscpd                 | Find copy-pasted code
Dead code     | Knip + ts-prune       | Find unused exports, files, dependencies
Security      | npm audit             | Block PRs with security issues
Semantic      | Code Deslopper skill  | Catch AI-specific React/TS slop patterns
Safety verify | tsc + Vitest          | Prove refactor is type-safe and behavior-preserved
```

### Python
```
CI gate 1     | Ruff                  | Block PRs with style violations
CI gate 2     | mypy --strict         | Block PRs with type errors / Any abuse
CI gate 3     | Bandit                | Block PRs with security issues
Dead code     | Vulture               | Find unused functions and classes
Complexity    | Radon (CC > 10)       | Flag high-complexity functions
Semantic      | Code Deslopper skill  | Catch AI-specific Python slop patterns
Safety verify | pytest --cov          | Prove behavior preserved
```
