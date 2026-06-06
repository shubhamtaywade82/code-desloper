# JS, TS & React Anti-Patterns

This reference guide lists common AI-generated anti-patterns in JavaScript, TypeScript, and React ecosystems.

## 1. Wrapper Class Syndrome
**Smell:** AI creating classes for everything, e.g., `class ApiHelper { fetch(url) { return fetch(url); } }`.
**Idiomatic Fix:** Use exported functions. `export const fetchData = (url) => fetch(url);`.

## 2. Excessive `useMemo` and `useCallback`
**Smell:** AI-generated React often wraps *every* function and variable in these hooks "just in case."
**Idiomatic Fix:** Remove them unless there is a proven performance bottleneck or the value is a dependency for another hook.

## 3. Prop Drilling with Empty Wrappers
**Smell:** Components that exist only to pass props down to children without adding any logic or UI.
**Idiomatic Fix:** Use React Context for global state or "Component Composition" to pass elements instead of data.

## 4. Redundant State
**Smell:** Storing data in `useState` that can be derived from existing props or other state.
**Idiomatic Fix:** Compute derived values during render.

## 5. `any` and `unknown` Overuse
**Smell:** AI-generated TypeScript using `any` to avoid complex typing or creating redundant interfaces that mirror API responses exactly.
**Idiomatic Fix:** Use strict types. Use `Pick`, `Omit`, or `Partial` for variations of types.

## 6. Deeply Nested Callback Chains
**Smell:** `then().then().catch()` or deeply nested `if/else` within async functions.
**Idiomatic Fix:** Use `async/await` with early returns for errors.

## 7. Placeholder Component Scaffolding
**Smell:** Components filled with `// TODO: Implement UI` or overly verbose comments explaining basic React concepts.
**Idiomatic Fix:** Strip out comments that don't explain the "why."

## 8. Inconsistent Naming (Casing)
**Smell:** Mixing camelCase, PascalCase, and snake_case in JS files (common when AI tries to match a Python/Ruby backend).
**Idiomatic Fix:** Enforce camelCase for variables/functions and PascalCase for React components.
