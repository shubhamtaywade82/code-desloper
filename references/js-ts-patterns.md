# JavaScript / TypeScript / React — AI Slop Patterns & Idiomatic Fixes

## 1. Advanced TypeScript & Type Safety

### 1.1 Making Illegal States Unrepresentable
**Smell:** "Boolean Soup" (e.g., `{ isLoading: boolean, error: string | null }`).
**Fix:** Use **Discriminated Unions** (The "Kind" Pattern). This ensures that you can't have `data` and `error` at the same time.

```typescript
// BEFORE (AI slop)
interface State { isLoading: boolean; error: string | null; data: any; }

// AFTER (idiomatic)
type State<T> = 
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; data: T };
```

### 1.2 Type Narrowing (The "Fish" Pattern)
**Smell:** Manually casting with `as` or using `any` when dealing with union types.
**Fix:** Use **Type Predicates** (`arg is T`) or the `in` operator to safely narrow types.

```typescript
// BEFORE
const move = (animal: Fish | Bird) => {
  (animal as Fish).swim(); // Dangerous cast
};

// AFTER
const isFish = (pet: Fish | Bird): pet is Fish => {
  return 'swim' in pet;
};

if (isFish(pet)) {
  pet.swim(); // TS knows pet is Fish here
}
```

### 1.3 Domain Primitives (Branded Types)
**Smell:** Using `string` or `number` for every ID, making it easy to pass a `UserId` where an `OrderId` is expected.
**Fix:** Use **Branded Types** (Opaque types) for critical domain primitives.

```typescript
// AFTER
type UserId = string & { readonly __brand: 'UserId' };
type OrderId = string & { readonly __brand: 'OrderId' };
```

### 1.4 Runtime Validation at Boundaries
**Smell:** Trusting that API responses match your TypeScript interfaces exactly.
**Fix:** Use **Zod** or similar libraries to validate data at the system boundary (API calls, LocalStorage).

```typescript
// AFTER
const UserSchema = z.object({ id: z.string(), email: z.string().email() });
const data = UserSchema.parse(await response.json());
type User = z.infer<typeof UserSchema>;
```

## 2. Modern React Architecture (2025)

### 2.1 Separation of Concerns (Server vs. Client)
**Smell:** Components that handle data fetching, complex business logic, and UI rendering in one file.
**Fix:** Follow the **Layered Approach**:
- **Server Components (Data):** Fetch data and handle security.
- **Client Components (UI):** Handle interactivity and local state.
- **Custom Hooks (Logic):** Encapsulate reusable stateful logic (the "Modern Container").

### 2.2 Compound Components (The "API" Pattern)
**Smell:** "Prop Explosion" where a component takes 20+ props to configure internal parts.
**Fix:** Use **Compound Components** with the Context API to provide a flexible, expressive JSX API.

```tsx
// USAGE
<Tabs defaultValue="home">
  <Tabs.List>
    <Tabs.Trigger value="home">Home</Tabs.Trigger>
  </Tabs.List>
  <Tabs.Content value="home">Content</Tabs.Content>
</Tabs>
```

### 2.3 The "Slot" Pattern
**Smell:** Hardcoding sub-components inside a layout, making it non-reusable.
**Fix:** Use the `children` prop or specific "slot" props (`renderHeader`, `footer`) to inject UI.

### 2.4 Suspense & Error Boundaries
**Smell:** Manually managing `isLoading` and `isError` flags in every component.
**Fix:** Use **React Suspense** for loading states and **Error Boundaries** for failures at the layout level.

## 3. State Management & Performance

### 3.1 Server vs. UI State
**Smell:** Storing API data in `Zustand` or `Redux` and manually managing synchronization.
**Fix:** Use **TanStack Query** (React Query) for server state (caching, retries) and **Zustand** for lightweight global UI state.

### 3.2 Derived State (Render Time)
**Smell:** Syncing props to state using `useEffect`.
**Fix:** Compute derived values during render. Use `useMemo` only for genuine bottlenecks.

### 3.3 Virtualization for Large Data
**Smell:** Rendering lists of >100 items directly, causing lag.
**Fix:** Use **`react-window`** or **`TanStack Virtual`** to render only the visible window.

## 4. AI-Specific "Slop" & Logic Smells

### 4.1 Async Array Callback Trap
**Smell:** `items.map(async ...)` which returns an array of unresolved Promises.
**Fix:** Use `await Promise.all(items.map(...))`.

### 4.2 Silent Error Swallowing
**Smell:** Empty `catch (e) {}` blocks or generic "Something went wrong" without logging.
**Fix:** Always log to a monitoring service (Sentry) and provide actionable user feedback.

### 4.3 Redundant DTOs & Interfaces
**Smell:** Interfaces that repeat API shapes exactly without adding type safety or mapping.
**Fix:** Inline types or use `z.infer` to keep a single source of truth.

## 5. Engineering Standards
- **Contract First:** Define types/schemas before implementation.
- **Immutability:** Use `const` by default; use `readonly` for props and arrays.
- **Named Exports:** Avoid `default` exports to improve refactoring and grep-ability.
- **No Lint Disables:** Fix the type issue; do not use `// @ts-ignore` or `any`.
- **Early Returns:** Use Guard Clauses to flatten functions.
