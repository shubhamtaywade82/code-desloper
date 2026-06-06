# JavaScript / TypeScript / React — AI Slop Patterns & Idiomatic Fixes

## 1. TypeScript & Type Safety

### 1.1 The `any` Crutch
**Smell:** Using `any` to bypass the type system.
**Fix:** Use `unknown` with type narrowing (Zod, Type Guards).
**Safety check:** Ensure runtime validation is present if the data source is external.

```typescript
// BEFORE (AI slop)
function processUser(data: any) {
  console.log(data.id.toUpperCase()); // Runtime error if id is missing or not a string
}

// AFTER (idiomatic)
interface User { id: string; }
function processUser(data: unknown) {
  if (data && typeof data === 'object' && 'id' in data && typeof data.id === 'string') {
    console.log(data.id.toUpperCase());
  }
}
```

### 1.2 "Stringly" Typing
**Smell:** Using `string` for variables with a discrete set of valid values.
**Fix:** Use Union Types or Template Literal Types.

```typescript
// BEFORE
type Status = string; // "loading", "success", "error"

// AFTER
type Status = 'loading' | 'success' | 'error';
```

### 1.3 Discriminated Unions for State
**Smell:** "Boolean Soup" (e.g., `{ isLoading: boolean, error: string | null }`).
**Fix:** Use a discriminated union to represent mutually exclusive states.

```typescript
// BEFORE
interface State { isLoading: boolean; error: string | null; data: any; }

// AFTER
type State<T> = 
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; data: T };
```

### 1.4 Numeric Enums
**Smell:** Standard `enum` which can accept arbitrary numbers.
**Fix:** Use `as const` objects or String Unions.

```typescript
// BEFORE
enum Direction { Up, Down }

// AFTER
const Direction = { Up: 'UP', Down: 'DOWN' } as const;
type Direction = typeof Direction[keyof typeof Direction];
```

## 2. React Anti-Patterns

### 2.1 Redundant useMemo / useCallback
**Smell:** Memoizing trivial values or functions without a performance bottleneck.
**Fix:** Remove. React's re-render is often cheaper than memoization overhead.

### 2.2 Derived State
**Smell:** Syncing props to state using `useEffect`.
**Fix:** Compute at render time.

```tsx
// BEFORE
const [fullName, setFullName] = useState('');
useEffect(() => { setFullName(`${first} ${last}`); }, [first, last]);

// AFTER
const fullName = `${first} ${last}`;
```

### 2.3 Object/Array Props as Dependencies
**Smell:** Passing an inline object `style={{ color: 'red' }}` to a memoized component.
**Fix:** Move outside the component or use `useMemo`.

## 3. AI-Specific Logic Smells

### 3.1 Async Array Callback Trap
**Smell:** Mapping over an array with an async function and forgetting `Promise.all`.
**Fix:** Use `Promise.all`.

```typescript
// BEFORE (Returns array of Promises)
const results = items.map(async (item) => await process(item));

// AFTER
const results = await Promise.all(items.map(item => process(item)));
```

### 3.2 Silent Error Swallowing
**Smell:** Empty `catch (e) {}` blocks.
**Fix:** Always log, report, or handle the error.

### 3.3 Deep Nesting vs. Guard Clauses
**Smell:** Deeply nested `if/else` structures.
**Fix:** Use early returns (Guard Clauses).

```typescript
// BEFORE
function save(data) {
  if (data) {
    if (data.isValid) {
      // Logic...
    }
  }
}

// AFTER
function save(data) {
  if (!data || !data.isValid) return;
  // Logic...
}
```

## 4. Architectural Smells

### 4.1 One-Method Manager Class
**Smell:** A class with one public method that wraps a single fetch call.
**Fix:** Replace with a plain async function.

### 4.2 Utility Duplication
**Smell:** `formatDate` defined in multiple files.
**Fix:** Consolidate into a shared utility module.

### 4.3 Redundant DTOs
**Smell:** Interfaces that mirror API responses exactly with no transformation.
**Fix:** Remove unless mapping is required.

## 5. Output Consistency
**Rules for Cleanup:**
- Use **Arrow Functions** for components and utilities.
- Use **ES6+ features** (optional chaining `?.`, nullish coalescing `??`).
- Trust **Type Inference** for simple assignments.
- Annotate **Public API** return types and parameters.
- **Co-locate** types with logic.
