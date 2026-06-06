# JavaScript / TypeScript / React — AI Slop Patterns & Idiomatic Fixes

This reference guide provides comprehensive best practices, anti-patterns, and idiomatic fixes for modern TypeScript development, React dashboard architectures, type-level programming, clean code, and general code hygiene.

---

## 1. Modern TypeScript Core (TypeScript)
*Writes, configures, and refactors TypeScript code following modern best practices.*

### 1.1 Strict Mode & Compiler Options
- **Smell:** Disabling strict flags or using lax configurations.
- **Fix:** Enable `strict: true` and configure `noImplicitAny`, `strictNullChecks`, `noUnusedLocals`, and `noUnusedParameters` in `tsconfig.json`.
- **Safety check:** When refactoring a legacy codebase, enable strict settings incrementally.

### 1.2 Type Inference vs. Explicit Typing
- **Smell:** Redundant explicit type annotations for simple variables, literals, or immediately initialized values.
- **Fix:** Let TypeScript infer simple types; only annotate function parameters, return types of public APIs, and complex type shapes.
- **Example:**
  ```typescript
  // BEFORE (AI slop)
  const count: number = 0;
  const name: string = "Deslopper";
  
  // AFTER (idiomatic)
  const count = 0;
  const name = "Deslopper";
  ```

---

## 2. Advanced TypeScript Patterns & Strict Type Safety (TypeScript Best Practices & Patterns)
*Implements advanced TypeScript patterns, strict type-safety, and idiomatic fixes.*

### 2.1 The `any` Crutch
- **Smell:** Using `any` to bypass the type system.
- **Fix:** Use `unknown` with runtime type narrowing (Zod, Type Guards).
- **Safety check:** Ensure runtime validation is present if the data source is external.
- **Example:**
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

### 2.2 "Stringly" Typing
- **Smell:** Using `string` for variables with a discrete set of valid values.
- **Fix:** Use Union Types or Template Literal Types.
- **Example:**
  ```typescript
  // BEFORE
  type Status = string; // "loading", "success", "error"

  // AFTER
  type Status = 'loading' | 'success' | 'error';
  ```

### 2.3 Discriminated Unions for State (Making Illegal States Unrepresentable)
- **Smell:** "Boolean Soup" (e.g., `{ isLoading: boolean, error: string | null }`).
- **Fix:** Use a discriminated union to represent mutually exclusive states.
- **Example:**
  ```typescript
  // BEFORE
  interface State { isLoading: boolean; error: string | null; data: any; }

  // AFTER
  type State<T> =
    | { status: 'loading' }
    | { status: 'error'; message: string }
    | { status: 'success'; data: T };
  ```

### 2.4 Domain Primitives (Branded Types)
- **Smell:** Using primitive types (`string`, `number`) for identifiers, making it easy to pass a `UserId` where an `OrderId` is expected.
- **Fix:** Use Branded Types (Opaque types) for critical domain identifiers.
- **Example:**
  ```typescript
  // AFTER
  type UserId = string & { readonly __brand: 'UserId' };
  type OrderId = string & { readonly __brand: 'OrderId' };
  ```

### 2.5 Numeric Enums
- **Smell:** Standard `enum` which can accept arbitrary numbers and compiles to bloated IIFEs.
- **Fix:** Use `as const` objects or String Unions.
- **Example:**
  ```typescript
  // BEFORE
  enum Direction { Up, Down }

  // AFTER
  const Direction = { Up: 'UP', Down: 'DOWN' } as const;
  type Direction = typeof Direction[keyof typeof Direction];
  ```

### 2.6 Exhaustiveness Checking
- **Smell:** Missing cases in switch-statements or conditional blocks when handling union types, leading to runtime bugs when new union members are added.
- **Fix:** Use the `never` type to perform compile-time exhaustiveness checking.
- **Example:**
  ```typescript
  // BEFORE (AI slop)
  type Theme = 'light' | 'dark';
  function getThemeColor(theme: Theme) {
    if (theme === 'light') return '#fff';
    if (theme === 'dark') return '#000';
  }
  
  // AFTER (idiomatic)
  type Theme = 'light' | 'dark' | 'solarized';
  function getThemeColor(theme: Theme): string {
    switch (theme) {
      case 'light': return '#fff';
      case 'dark': return '#000';
      case 'solarized': return '#fdf6e3';
      default: {
        const _exhaustiveCheck: never = theme;
        return _exhaustiveCheck;
      }
    }
  }
  ```

### 2.7 User-Defined Type Guards (Type Narrowing)
- **Smell:** Repetitive type assertions (`as MyType`) or manual type checks.
- **Fix:** Create a custom type guard using the `parameter is Type` syntax.
- **Example:**
  ```typescript
  // BEFORE (AI slop)
  function isUser(obj: any) {
    return obj && typeof obj.name === 'string';
  }
  
  // AFTER (idiomatic)
  interface User { name: string; }
  function isUser(obj: unknown): obj is User {
    return (
      typeof obj === 'object' &&
      obj !== null &&
      'name' in obj &&
      typeof (obj as Record<string, unknown>).name === 'string'
    );
  }
  ```

---

## 3. TypeScript React Dashboard Architect (React Dashboard Architect)
*Standardizes TypeScript and React development for professional dashboards.*

### 3.1 Separation of Concerns (Server vs. Client vs. Logic)
- **Smell:** Components handling data fetching, state management, and layout rendering in a single monolithic block.
- **Fix:** Split responsibilities:
  - **Server Components:** Data fetching and authorization.
  - **Client Components:** Direct user interaction and DOM events.
  - **Custom Hooks:** Stateful logic encapsulation.

### 3.2 Compound Components (The "API" Pattern)
- **Smell:** Passing dozens of props down to configure child elements ("Prop Explosion").
- **Fix:** Use Compound Components sharing context.
- **Example:**
  ```tsx
  <Tabs defaultValue="home">
    <Tabs.List>
      <Tabs.Trigger value="home">Home</Tabs.Trigger>
    </Tabs.List>
    <Tabs.Content value="home">Content</Tabs.Content>
  </Tabs>
  ```

### 3.3 Context Type Safety (Null Avoidance)
- **Smell:** Using non-null assertions (`!`) or returning `undefined` from custom context hooks, leading to silent failures.
- **Fix:** Throw descriptive errors in the custom hook if the Context Provider is missing.
- **Example:**
  ```typescript
  // BEFORE (AI slop)
  const DashboardContext = React.createContext<DashboardData | undefined>(undefined);
  function useDashboard() {
    return useContext(DashboardContext)!; // unsafe non-null assertion
  }
  
  // AFTER (idiomatic)
  const DashboardContext = React.createContext<DashboardData | undefined>(undefined);
  function useDashboard() {
    const context = useContext(DashboardContext);
    if (!context) {
      throw new Error("useDashboard must be used within a DashboardProvider");
    }
    return context;
  }
  ```

### 3.4 Reusable Generic Components
- **Smell:** Re-writing dashboard elements (e.g., tables, dropdowns) for each data type or typing them with `any[]`.
- **Fix:** Build generic components that accept a type parameter `T`.
- **Example:**
  ```tsx
  // BEFORE (AI slop)
  interface TableProps {
    items: any[];
    renderRow: (item: any) => React.ReactNode;
  }
  
  // AFTER (idiomatic)
  interface TableProps<T> {
    items: T[];
    renderRow: (item: T) => React.ReactNode;
  }
  function Table<T>({ items, renderRow }: TableProps<T>) {
    return <table><tbody>{items.map(renderRow)}</tbody></table>;
  }
  ```

---

## 4. TypeScript Type System Master (Type-Level Programming)
*Enables advanced TypeScript type-level programming and strict compile-time checks.*

### 4.1 Conditional Types and the `infer` Keyword
- **Smell:** Complex runtime type checking or duplicated interface definitions to extract nested types.
- **Fix:** Use conditional types and `infer` to dynamically extract types.
- **Example:**
  ```typescript
  // Extracting return type of an async function
  type UnwrapPromise<T> = T extends Promise<infer U> ? U : T;
  ```

### 4.2 Template Literal Types
- **Smell:** Loosely-typed configuration keys or action names.
- **Fix:** Use template literal types to enforce exact string patterns.
- **Example:**
  ```typescript
  type Event = 'click' | 'hover';
  type HandlerName = `on${Capitalize<Event>}`; // "onClick" | "onHover"
  ```

### 4.3 Utility Types & Mapped Types
- **Smell:** Manually duplicating interfaces to create optional, readonly, or sub-selected variations.
- **Fix:** Leverage built-in utility types (`Partial`, `Required`, `Readonly`, `Omit`, `Pick`) and custom mapped types.
- **Example:**
  ```typescript
  // Custom mapped type to make all properties readonly recursively
  type DeepReadonly<T> = {
    readonly [P in keyof T]: T[P] extends object ? DeepReadonly<T[P]> : T[P];
  };
  ```

---

## 5. High-Quality Coding Standards & Robust Type Safety (TypeScript Best Practices)
*Enforces high-quality coding standards and robust type safety for TypeScript.*

### 5.1 Safe API boundaries with Schema Validation
- **Smell:** Trusting external network API responses using `as MyType` assertions.
- **Fix:** Validate incoming payloads at the API boundary using Zod.
- **Example:**
  ```typescript
  // BEFORE (AI slop)
  const user = (await response.json()) as User; // Unsafe cast
  
  // AFTER (idiomatic)
  import { z } from 'zod';
  const UserSchema = z.object({ id: z.string(), email: z.string().email() });
  const user = UserSchema.parse(await response.json()); // Fully runtime-validated & typed
  ```

### 5.2 Catching `unknown` Errors
- **Smell:** Typing caught errors in catch blocks as `any`.
- **Fix:** Keep the default `unknown` error type and use type guards or utility functions to narrow it safely.
- **Example:**
  ```typescript
  // BEFORE (AI slop)
  try { ... } catch (err: any) {
    console.error(err.message);
  }
  
  // AFTER (idiomatic)
  try { ... } catch (err) {
    if (err instanceof Error) {
      console.error(err.message);
    } else {
      console.error("An unknown error occurred", err);
    }
  }
  ```

### 5.3 Avoiding Object Index Signatures
- **Smell:** Using `[key: string]: any` for general dictionary objects.
- **Fix:** Use `Record<string, unknown>` or a more specific key type to prevent index access issues.

---

## 6. AI-Specific Logic & Architectural Smells

### 6.1 Async Array Callback Trap
- **Smell:** Mapping over an array with an async function and forgetting `Promise.all`.
- **Fix:** Use `Promise.all`.
- **Example:**
  ```typescript
  // BEFORE (Returns array of Promises)
  const results = items.map(async (item) => await process(item));

  // AFTER
  const results = await Promise.all(items.map(item => process(item)));
  ```

### 6.2 Silent Error Swallowing
- **Smell:** Empty `catch (e) {}` blocks.
- **Fix:** Always log, report, or handle the error.

### 6.3 Deep Nesting vs. Guard Clauses
- **Smell:** Deeply nested `if/else` structures.
- **Fix:** Use early returns (Guard Clauses).
- **Example:**
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

### 6.4 One-Method Manager Class
- **Smell:** A class with one public method that wraps a single fetch call or operation.
- **Fix:** Replace with a plain async function.

### 6.5 Utility Duplication
- **Smell:** Utility functions defined in multiple files.
- **Fix:** Consolidate into a shared utility module.

### 6.6 Redundant DTOs
- **Smell:** Interfaces that mirror API responses exactly with no transformation.
- **Fix:** Remove unless mapping is required.

---

## 7. Clean JS/TS Architecture Guidelines
For comprehensive guidelines on variable naming, single-responsibility functions, object encapsulation, method chaining, class design, SOLID principles, testing patterns, and async/await usage, refer to:
*   [Clean JS-TS Reference Guide](Clean%20JS-TS.md)

---

## 8. Output Consistency

**Rules for Cleanup:**
- Use **Arrow Functions** for components and utilities.
- Use **ES6+ features** (optional chaining `?.`, nullish coalescing `??`).
- Trust **Type Inference** for simple assignments.
- Annotate **Public API** return types and parameters.
- **Co-locate** types with logic.
