# JavaScript / TypeScript / React — AI Slop Patterns & Idiomatic Fixes

## Function vs Class Anti-Patterns

### 1. One-Method Manager Class
**Smell:** A class with one public method that wraps a single fetch call.
**Fix:** Replace with a plain async function.
**Safety check:** Ensure no internal state, no inheritance, no event listeners attached.

```typescript
// BEFORE (AI slop)
class ApiManager {
  async fetchUsers() {
    return fetch("/api/users").then(r => r.json());
  }
}
const users = await new ApiManager().fetchUsers();

// AFTER (idiomatic)
export const fetchUsers = async () => {
  const res = await fetch("/api/users");
  return res.json();
};
```

### 2. Redundant DTOs
**Smell:** TypeScript interfaces that mirror API responses exactly with no transformation.
**Fix:** Remove unless boundary mapping is needed (different field names, computed fields, validation).
**Safety check:** Check if the DTO is used for zod validation, form handling, or presentation logic.

### 3. Pointless Type Wrappers
**Smell:** `type UserId = string;` used once, or interfaces that only repeat inference.
**Fix:** Delete. Use inline types or inference.
**Safety check:** Ensure the alias is not used for documentation or to prevent primitive obsession across the codebase.

## React Anti-Patterns

### 4. Empty Wrapper Components
**Smell:** Component that only renders children with no logic, no styling, no context.
**Fix:** Remove and pass children directly to the parent.
**Safety check:** Check if the wrapper adds `data-testid`, event handlers, or ref forwarding.

```tsx
// BEFORE
const CardWrapper = ({ children }) => <div>{children}</div>;

// AFTER
// Use <div> directly or the parent component's own container.
```

### 5. Redundant useMemo / useCallback
**Smell:** `useMemo` with empty or static dependencies, or memoizing a value that is cheap to compute.
**Fix:** Remove. React's re-render is often cheaper than memoization overhead.
**Safety check:** Verify the dependency array is actually static and the computation is not expensive.

```tsx
// BEFORE
const label = useMemo(() => `${user.firstName} ${user.lastName}`, [user.firstName, user.lastName]);

// AFTER
const label = `${user.firstName} ${user.lastName}`;
```

### 6. Derived State
**Smell:** `useState` for a value that can be computed from props or other state.
**Fix:** Compute at render time. Use `useMemo` only if the computation is genuinely expensive.
**Safety check:** Ensure the derived value does not need to be stable for reference equality (e.g., as a `useEffect` dependency).

### 7. Prop Drilling Through Abstraction Layers
**Smell:** Props passed through 3+ components to reach a leaf, with no intermediate usage.
**Fix:** Use context, composition, or move the component closer to the data.
**Safety check:** Ensure the intermediate components are not also used in other contexts where the prop matters.

## Control Flow Anti-Patterns

### 8. Nested If-Else Pyramid
**Smell:** Deeply nested conditionals from generated code.
**Fix:** Flatten with early returns, guard clauses, or pattern matching.
**Safety check:** Preserve all edge cases and error handling paths.

```typescript
// BEFORE
function process(data) {
  if (data) {
    if (data.items) {
      if (data.items.length > 0) {
        return data.items.map(...);
      } else {
        return [];
      }
    } else {
      return [];
    }
  } else {
    return [];
  }
}

// AFTER
function process(data) {
  if (!data?.items?.length) return [];
  return data.items.map(...);
}
```

### 9. Callback Pyramid
**Smell:** Nested `.then()` chains or callback hell.
**Fix:** Convert to `async/await` with `try/catch`.
**Safety check:** Ensure error handling and promise rejection paths are preserved.

## Utility Anti-Patterns

### 10. Utility Duplication
**Smell:** `formatDate`, `capitalize`, `slugify` defined in multiple files.
**Fix:** Consolidate into a single `utils/` or `lib/` module.
**Safety check:** Verify implementations are identical (not slightly different for locale/format reasons).

### 11. Vague Naming in Utilities
**Smell:** `helpers.ts` with `doThing`, `handleStuff`, `processData`.
**Fix:** Rename to specific actions: `parseCSV`, `validateEmail`, `buildQueryString`.
**Safety check:** Update all imports and call sites. Use arrow functions, latest syntax, and follow project linting rules.
