# JavaScript / TypeScript / React — AI Slop Patterns & Idiomatic Fixes

## CLASS VS. FUNCTION ANTI-PATTERNS

### 1. One-Method Manager Class → Plain Function
**Smell:** Class with one public method wrapping a single fetch/operation; no internal state.
**Fix:** Replace with a plain async function.
**Safety:** Ensure no internal state, no inheritance, no event listeners, no shared instances.

```typescript
// BEFORE (AI slop)
class ApiManager {
  async fetchUsers() {
    return fetch("/api/users").then(r => r.json());
  }
}
const users = await new ApiManager().fetchUsers();

// AFTER
const fetchUsers = async (): Promise<User[]> => {
  const res = await fetch("/api/users");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
};
```

### 2. Redundant DTOs (Interface Mirrors API Exactly)
**Smell:** TypeScript interface that mirrors an API response with no transformation.
**Fix:** Remove. Use inference or the API type directly.
**Safety:** Check if DTO is used for Zod validation, form handling, or presentation logic.

```typescript
// BEFORE — UserDTO adds nothing; mirrors API exactly
interface UserDTO {
  id: string;
  name: string;
  email: string;
}
const user: UserDTO = await fetchUser(id);

// AFTER — infer the type or use a schema
const user = await fetchUser(id);  // type inferred
// or: z.infer<typeof UserSchema> if validation needed
```

### 3. Pointless Type Alias → Inline or Delete
**Smell:** `type UserId = string` used once, never adds constraints.
**Fix:** Use `string` directly unless the alias prevents primitive obsession across > 2 files.
**Safety:** Check if alias is used for branding or documentation across a large surface area.

```typescript
// BEFORE — used only in one place, adds no validation
type UserId = string;
function findUser(id: UserId): User { ... }

// AFTER — unless you brand it
function findUser(id: string): User { ... }

// KEEP if you have a branded type preventing mix-ups
type UserId = string & { readonly _brand: 'UserId' };
type ProductId = string & { readonly _brand: 'ProductId' };
```

### 4. `any` and `unknown` Wrappers → Strict Domain Types
**Smell:** `any` or wrapper interfaces that re-declare inferred types.
**Fix:** Use strict types; delete unnecessary `any` casts.
**Safety:** Verify no runtime behavior relies on loose typing.

```typescript
// BEFORE
function processData(data: any) {
  return data.items.map((item: any) => item.name);
}

// AFTER
interface ApiResponse {
  items: Array<{ name: string; id: number }>;
}
function processData(data: ApiResponse): string[] {
  return data.items.map(item => item.name);
}
```

---

## REACT ANTI-PATTERNS

### 5. Empty Wrapper Component → Use Directly
**Smell:** Component only renders `{children}` in a container with no logic, no context, no event handling.
**Fix:** Remove. Use the container element directly in the parent.
**Safety:** Check for `data-testid`, event handlers, ref forwarding, or portal usage.

```tsx
// BEFORE
const CardWrapper = ({ children }: { children: React.ReactNode }) => (
  <div className="card">{children}</div>
);

// AFTER — use the div directly in parent
<div className="card">
  {/* content */}
</div>
```

### 6. Redundant `useMemo` → Inline
**Smell:** `useMemo` with static/cheap computation or with deps that change on every render anyway.
**Fix:** Remove. React's re-render is cheaper than memoization overhead for simple values.
**Safety:** Verify the computation is not expensive (> 1ms) and the value isn't used as a `useEffect` dep with reference equality needs.

```tsx
// BEFORE — string concatenation costs nanoseconds; useMemo costs more
const label = useMemo(
  () => `${user.firstName} ${user.lastName}`,
  [user.firstName, user.lastName]
);

// AFTER
const label = `${user.firstName} ${user.lastName}`;
```

### 7. Redundant `useCallback` → Inline or Delete
**Smell:** `useCallback` with no dependency that changes, or on a handler not passed to memoized children.
**Fix:** Remove unless the callback is passed to a `React.memo` component as a prop.
**Safety:** Check if the callback is a dependency of `useEffect` or passed as prop to memoized component.

```tsx
// BEFORE — handleClick is recreated on every render anyway (dep: [count])
const handleClick = useCallback(() => {
  setCount(count + 1);
}, [count]);

// AFTER — count changes every click anyway; useCallback saves nothing
const handleClick = () => setCount(count + 1);
// or: use functional update
const handleClick = () => setCount(c => c + 1);
```

### 8. Derived State → Compute at Render
**Smell:** `useState` for a value that can be computed from props or other state.
**Fix:** Compute at render time. Use `useMemo` only if genuinely expensive.
**Safety:** Ensure the derived value doesn't need to be stable for reference equality.

```tsx
// BEFORE
const [displayName, setDisplayName] = useState(`${user.first} ${user.last}`);
// Now displayName is stale when user changes unless synced with useEffect

// AFTER
const displayName = `${user.first} ${user.last}`;
// Always in sync, no extra state, no sync bugs
```

### 9. Prop Drilling Through 3+ Levels → Context or Co-location
**Smell:** Props passed through components that don't use them.
**Fix:** Context, render props, composition, or move the component closer to the data.
**Safety:** Ensure intermediate components aren't also used in other contexts.

```tsx
// BEFORE — Panel and Header don't use user; they just forward it
<Dashboard user={user} />   // uses user
  <Panel user={user} />     // doesn't use user, forwards it
    <Header user={user} />  // doesn't use user, forwards it
      <UserBadge user={user} />  // actually uses user

// AFTER — Option A: Context
const UserContext = createContext<User | null>(null);
// UserBadge reads: const user = useContext(UserContext)

// AFTER — Option B: Co-locate component
<Dashboard>
  <UserBadge user={user} />  // Dashboard renders UserBadge directly
</Dashboard>
```

### 10. Premature Custom Hook Extraction → Inline
**Smell:** Custom hook used in only one component, wraps trivial state logic.
**Fix:** Inline the state directly in the component.
**Safety:** Check if the hook is used in other components or has complex logic worth isolating.

```tsx
// BEFORE — useOrderFormState used only in OrderForm
function useOrderFormState() {
  const [status, setStatus] = useState('pending');
  const [items, setItems] = useState([]);
  return { status, setStatus, items, setItems };
}

// AFTER — inline unless reused
const OrderForm = () => {
  const [status, setStatus] = useState('pending');
  const [items, setItems] = useState([]);
  // direct, no indirection
};
```

### 11. God Component → Decompose
**Smell:** One component handles data fetching, display, auth, routing, and form logic.
**Fix:** Separate concerns into smaller components and custom hooks.

```tsx
// BEFORE — 200-line component doing everything
const Dashboard = () => {
  const { user } = useAuth();
  const { data } = useFetch('/api/dashboard');
  // 200 lines of JSX + logic
};

// AFTER — composition
const Dashboard = () => (
  <AuthGuard>
    <DashboardData>
      {(data) => <DashboardView data={data} />}
    </DashboardData>
  </AuthGuard>
);
```

---

## CONTROL FLOW ANTI-PATTERNS

### 12. Nested If-Else Pyramid → Early Returns

```typescript
// BEFORE
function process(data) {
  if (data) {
    if (data.items) {
      if (data.items.length > 0) {
        return data.items.map(transform);
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

// AFTER — guard clauses
function process(data) {
  if (!data?.items?.length) return [];
  return data.items.map(transform);
}
```

### 13. `.then()` Chain → `async/await`

```typescript
// BEFORE — callback pyramid
function fetchAndProcess(id: string) {
  return api.getUser(id)
    .then(user => api.getOrders(user.id))
    .then(orders => orders.filter(o => o.active))
    .then(orders => orders.map(transform))
    .catch(err => { console.error(err); return []; });
}

// AFTER — async/await
async function fetchAndProcess(id: string) {
  try {
    const user = await api.getUser(id);
    const orders = await api.getOrders(user.id);
    return orders.filter(o => o.active).map(transform);
  } catch (err) {
    console.error(err);
    return [];
  }
}
```

### 14. Switch on Type → Discriminated Union + Exhaustive Check

```typescript
// BEFORE — switch must be updated whenever type is added
function getIcon(shape: Shape): string {
  switch (shape.type) {
    case 'circle':    return '⬤';
    case 'rectangle': return '▬';
    default:          return '?';
  }
}

// AFTER — discriminated union + type-safe exhaustive handling
type Shape =
  | { kind: 'circle';    radius: number }
  | { kind: 'rectangle'; width: number; height: number };

function getIcon(shape: Shape): string {
  const icons: Record<Shape['kind'], string> = {
    circle: '⬤',
    rectangle: '▬',
  };
  return icons[shape.kind];
}
```

---

## UTILITY ANTI-PATTERNS

### 15. Utility Duplication → Consolidate
**Smell:** `formatDate`, `capitalize`, `slugify` defined in multiple files.
**Fix:** Consolidate into a single `utils/` or `lib/` module.
**Safety:** Verify implementations are identical — not subtly different for locale/format/timezone reasons.

### 16. Vague Naming → Specific Actions
**Smell:** `helpers.ts` with `doThing`, `handleStuff`, `processData`.
**Fix:** Rename to specific actions: `parseCSV`, `validateEmail`, `buildQueryString`.
**Safety:** Update all imports and call sites simultaneously.

### 17. Non-Null Assertion Overuse → Proper Guards
**Smell:** `data!.user!.profile!.name` — chained non-null assertions.
**Fix:** Use optional chaining and provide a fallback, or ensure the data is validated at the entry point.

```typescript
// BEFORE
const name = data!.user!.profile!.name;

// AFTER — validate at boundary, use optional chaining in business logic
const name = data?.user?.profile?.name ?? 'Unknown';
// or: validate with Zod at API boundary so downstream code can trust types
```

---

## CODE SMELL TAXONOMY (JS/TS)

### Feature Envy (method uses another object's data more than its own)

```typescript
// SMELL — Order.calculateShipping uses Customer's internals
class Order {
  calculateShipping(customer: Customer): number {
    if (customer.country === 'US') {
      return customer.state === 'CA' ? 10 : 15;
    }
    return 25;
  }
}

// REFACTORED — move to Customer
class Customer {
  get shippingCost(): number {
    if (this.country === 'US') return this.state === 'CA' ? 10 : 15;
    return 25;
  }
}
class Order {
  calculateShipping(): number { return this.customer.shippingCost; }
}
```

### Primitive Obsession → Value Objects

```typescript
// SMELL
function createUser(email: string, age: number, zip: string) { ... }

// REFACTORED
class Email {
  constructor(private value: string) {
    if (!value.includes('@')) throw new InvalidEmail();
  }
  toString() { return this.value; }
}
class Age {
  constructor(private value: number) {
    if (value < 0 || value > 150) throw new InvalidAge();
  }
}
function createUser(email: Email, age: Age, address: Address) { ... }
```

### Speculative Generality (YAGNI)

```typescript
// SMELL — unused interface methods implemented as stubs
interface PaymentProcessor {
  process(): void;
  rollback(): void;         // never called
  generateReport(): void;   // never called
  scheduleRecurring(): void; // never called
}

// REFACTORED — YAGNI: add methods when actually needed
interface PaymentProcessor {
  process(): void;
}
```

### Data Clumps → Parameter Objects

```typescript
// SMELL — city, state, zip always travel together
function ship(userId: string, city: string, state: string, zip: string, item: Item) { ... }

// REFACTORED
interface Address { city: string; state: string; zip: string; }
function ship(userId: string, address: Address, item: Item) { ... }
```

---

## CLEAN JS/TS GUIDELINES
For comprehensive clean code guidelines on variables, functions, SOLID principles, testing patterns, and async/await usage in JavaScript and TypeScript, refer to:
- [Clean JS-TS Reference Guide](Clean%20JS-TS.md)

