# Jest / Vitest Anti-Patterns Reference

Reference for the Code Deslopper skill. Covers AI-generated test code patterns that degrade
reliability, maintainability, and signal-to-noise ratio. Each pattern includes a risk score
(1 = minor style issue, 5 = silently broken tests), before/after TypeScript examples, and
safety notes for automated transformation.

---

## Quick Risk Index

| # | Pattern | Risk |
|---|---------|------|
| 1 | Mocking the module under test | 5 |
| 2 | Snapshot tests for every component | 3 |
| 3 | Testing implementation details | 4 |
| 4 | Missing `afterEach` cleanup | 4 |
| 5 | `beforeAll` with mutable shared state | 4 |
| 6 | `expect.anything()` instead of specific values | 3 |
| 7 | Missing async handling | 5 |
| 8 | `describe` with a single `it` | 1 |
| 9 | Enzyme `instance()` / component internals | 4 |
| 10 | Over-use of `waitFor` | 3 |
| 11 | `fireEvent` instead of `userEvent` | 3 |
| 12 | Missing error path tests | 4 |
| 13 | `it.only` / `describe.only` left in | 5 |
| 14 | Mock factories without realistic data | 2 |
| 15 | Testing third-party library behaviour | 2 |
| 16 | Giant test files with no organisation | 2 |
| 17 | No integration / e2e layer | 3 |
| 18 | `console.log` left in tests | 1 |
| 19 | Hardcoded `setTimeout` delays | 4 |
| 20 | Missing `expect.assertions(n)` in async error tests | 5 |

---

## 1. Mocking the Module Under Test

**Risk: 5 / 5**

AI frequently mocks the very file being tested, producing a test suite that never exercises
real code. The test passes regardless of implementation correctness.

### Before

```typescript
// user.service.test.ts
import { UserService } from './user.service';

jest.mock('./user.service'); // mocks the thing being tested

describe('UserService', () => {
  it('should return a user', () => {
    const mockGetUser = jest.fn().mockResolvedValue({ id: 1, name: 'Alice' });
    (UserService as jest.MockedClass<typeof UserService>).prototype.getUser =
      mockGetUser;

    const svc = new UserService();
    // This calls the mock, not the real implementation
    expect(svc.getUser(1)).resolves.toEqual({ id: 1, name: 'Alice' });
  });
});
```

### After

```typescript
// user.service.test.ts
import { UserService } from './user.service';
import { UserRepository } from './user.repository'; // mock the *dependency*, not the SUT

jest.mock('./user.repository');

describe('UserService', () => {
  let svc: UserService;
  let repoMock: jest.Mocked<UserRepository>;

  beforeEach(() => {
    repoMock = new UserRepository() as jest.Mocked<UserRepository>;
    repoMock.findById.mockResolvedValue({ id: 1, name: 'Alice' });
    svc = new UserService(repoMock);
  });

  it('returns a user by id', async () => {
    const user = await svc.getUser(1);
    expect(user).toEqual({ id: 1, name: 'Alice' });
  });
});
```

**Safety notes**
- Safe to flag automatically: if the mocked path matches the test file path (minus `.test`),
  this is almost certainly wrong.
- Do not auto-fix: the correct mock target is context-dependent. Surface as a warning.

---

## 2. Snapshot Tests for Every Component

**Risk: 3 / 5**

AI defaults to snapshot tests because they require zero domain knowledge. Over time snapshots
accumulate, fail for trivial markup changes (a class rename, a whitespace diff), and developers
update them without reading the diff.

### Before

```typescript
import { render } from '@testing-library/react';
import { Button } from './Button';

it('renders correctly', () => {
  const { container } = render(<Button label="Click me" />);
  expect(container).toMatchSnapshot(); // meaningless without intent
});

it('renders disabled correctly', () => {
  const { container } = render(<Button label="Click me" disabled />);
  expect(container).toMatchSnapshot();
});
```

### After

```typescript
import { render, screen } from '@testing-library/react';
import { Button } from './Button';

describe('Button', () => {
  it('renders the label text', () => {
    render(<Button label="Click me" />);
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument();
  });

  it('is disabled when the disabled prop is set', () => {
    render(<Button label="Click me" disabled />);
    expect(screen.getByRole('button', { name: 'Click me' })).toBeDisabled();
  });
});
```

**Acceptable snapshot uses**
- Serialised data structures (API response shapes, config objects) where the shape is the
  contract.
- Inline snapshots (`toMatchInlineSnapshot`) that are small enough to review in a diff.

**Safety notes**
- Flag any snapshot test that targets a React component's `container` or root element.
- Do not flag serialiser / AST snapshot tests — those are intentional.

---

## 3. Testing Implementation Details

**Risk: 4 / 5**

Spying on private methods, reading `component.state()`, or asserting on internal variable
names couples tests to the implementation. Refactoring without changing behaviour breaks
these tests.

### Before

```typescript
import { CartService } from './cart.service';

it('calls _calculateDiscount internally', () => {
  const svc = new CartService();
  const spy = jest.spyOn(svc as any, '_calculateDiscount');

  svc.addItem({ id: 1, price: 100 });

  expect(spy).toHaveBeenCalledWith(100); // testing private internals
});
```

### After

```typescript
import { CartService } from './cart.service';

it('applies a 10% discount for orders over $50', () => {
  const svc = new CartService();
  svc.addItem({ id: 1, price: 100 });

  // Assert on observable output, not internal method calls
  expect(svc.getTotal()).toBe(90);
});
```

**React component state example**

```typescript
// Before (Enzyme)
const wrapper = mount(<Counter />);
wrapper.find('button').simulate('click');
expect(wrapper.state('count')).toBe(1); // internal state

// After (RTL)
render(<Counter />);
userEvent.click(screen.getByRole('button', { name: /increment/i }));
expect(screen.getByText('Count: 1')).toBeInTheDocument(); // visible output
```

**Safety notes**
- `jest.spyOn(obj as any, '_privateMethod')` is a reliable flag pattern.
- Enzyme `.state()` / `.instance()` calls are always a flag.
- Some legitimate uses exist: spy on a collaborator's public method to verify integration.

---

## 4. Missing `afterEach` Cleanup

**Risk: 4 / 5**

Without cleanup, mocks, timers, and DOM nodes accumulate across tests. The failure manifests
in a different test than the one that caused the pollution, making it extremely hard to debug.

### Before

```typescript
describe('NotificationService', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    document.body.innerHTML = '<div id="root"></div>';
  });
  // No afterEach — fake timers and DOM persist into the next suite

  it('shows a notification', () => {
    const svc = new NotificationService();
    svc.show('Hello');
    expect(document.getElementById('notification')).toBeTruthy();
  });
});
```

### After

```typescript
describe('NotificationService', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    document.body.innerHTML = '<div id="root"></div>';
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.clearAllMocks();
    document.body.innerHTML = '';
  });

  it('shows a notification', () => {
    const svc = new NotificationService();
    svc.show('Hello');
    expect(document.getElementById('notification')).toBeTruthy();
  });
});
```

**Common items that always need cleanup**

| Setup | Cleanup |
|-------|---------|
| `jest.useFakeTimers()` | `jest.useRealTimers()` |
| `jest.spyOn(...)` | `jest.restoreAllMocks()` |
| `server.listen()` (MSW) | `server.resetHandlers()` / `server.close()` |
| `render(...)` (RTL) | automatic via `cleanup` if configured, else `cleanup()` |
| Event listeners on `window` | explicit `removeEventListener` |

**Safety notes**
- If `beforeEach` sets up mocks or DOM and no `afterEach` exists, flag it.
- In Vitest, `afterEach` / `beforeEach` are imported from `vitest`, not globals by default
  unless `globals: true` is set in `vitest.config.ts`.

---

## 5. `beforeAll` with Mutable Shared State

**Risk: 4 / 5**

`beforeAll` runs once per describe block. If tests mutate the shared object, later tests
observe a different state than intended, making test order matter.

### Before

```typescript
describe('UserStore', () => {
  let store: UserStore;

  beforeAll(() => {
    store = new UserStore(); // one instance shared across all tests
  });

  it('adds a user', () => {
    store.add({ id: 1, name: 'Alice' });
    expect(store.count()).toBe(1);
  });

  it('removes a user', () => {
    store.remove(1);
    expect(store.count()).toBe(0); // passes only if previous test ran first
  });
});
```

### After

```typescript
describe('UserStore', () => {
  let store: UserStore;

  beforeEach(() => {
    store = new UserStore(); // fresh instance per test
  });

  it('adds a user', () => {
    store.add({ id: 1, name: 'Alice' });
    expect(store.count()).toBe(1);
  });

  it('removes a previously added user', () => {
    store.add({ id: 1, name: 'Alice' });
    store.remove(1);
    expect(store.count()).toBe(0);
  });
});
```

**Legitimate `beforeAll` uses**
- Starting a real server / database connection where creation is expensive.
- Loading a large static fixture from disk that tests only read.
- Setting up an MSW server: `beforeAll(() => server.listen())`.

**Safety notes**
- `let x; beforeAll(() => { x = new ... })` where `x` is later mutated is the pattern to flag.
- `const` bindings initialised in `beforeAll` and never reassigned are lower risk.

---

## 6. `expect.anything()` / `expect.any()` Instead of Specific Values

**Risk: 3 / 5**

AI reaches for loose matchers to make tests pass quickly. They provide almost no regression
protection because any truthy value, any string, or any number satisfies them.

### Before

```typescript
it('calls the analytics service with event data', () => {
  const analytics = { track: jest.fn() };
  const svc = new CheckoutService(analytics);

  svc.completePurchase({ items: [{ id: 1 }], total: 99 });

  expect(analytics.track).toHaveBeenCalledWith(
    expect.any(String),          // event name — could be anything
    expect.objectContaining({
      total: expect.anything(),  // total — could be null, undefined, wrong number
    })
  );
});
```

### After

```typescript
it('tracks a purchase_completed event with the correct total', () => {
  const analytics = { track: jest.fn() };
  const svc = new CheckoutService(analytics);

  svc.completePurchase({ items: [{ id: 1 }], total: 99 });

  expect(analytics.track).toHaveBeenCalledWith('purchase_completed', {
    total: 99,
    itemCount: 1,
  });
});
```

**When loose matchers are acceptable**
- UUIDs, timestamps, or values genuinely unknown at test-write time.
- `expect.objectContaining` when asserting a subset of a large payload and the other fields
  are irrelevant to the test's intent — but still use specific values for the fields you do
  assert.

**Safety notes**
- `expect.anything()` is nearly always a flag.
- `expect.any(String)` on fields that have known fixed values is a flag.

---

## 7. Missing Async Handling

**Risk: 5 / 5**

A test that returns a rejected promise without `await` passes. The assertion never runs, and
the unhandled rejection may be silently swallowed or surface in the wrong test.

### Before

```typescript
it('fetches user data', () => {
  // Missing await — the promise is ignored
  expect(fetchUser(1)).resolves.toEqual({ id: 1, name: 'Alice' });
});

it('throws on invalid id', () => {
  // Missing await — the rejection is never caught here
  expect(fetchUser(-1)).rejects.toThrow('Invalid ID');
});
```

### After

```typescript
it('fetches user data', async () => {
  await expect(fetchUser(1)).resolves.toEqual({ id: 1, name: 'Alice' });
});

it('throws on invalid id', async () => {
  await expect(fetchUser(-1)).rejects.toThrow('Invalid ID');
});

// Alternative for rejection tests
it('throws on invalid id (try/catch style)', async () => {
  expect.assertions(1);
  try {
    await fetchUser(-1);
  } catch (err) {
    expect(err).toBeInstanceOf(InvalidIdError);
  }
});
```

**Common floating promise patterns**

```typescript
// Floating: missing return or await
it('test', () => {
  someAsyncFn();           // no await, no return
});

it('test', () => {
  return someAsyncFn();    // OK — returning the promise lets Jest catch rejection
});

it('test', async () => {
  await someAsyncFn();     // OK — explicit await
});
```

**Safety notes**
- Statically detectable: `it('...', () => { ... expect(...).resolves` without `async`/`return`.
- Vitest's `--reporter=verbose` will surface unhandled promise rejections but not missing
  assertions.

---

## 8. `describe` Block with a Single `it`

**Risk: 1 / 5**

A `describe` containing exactly one `it` adds indentation without grouping benefit. AI
generates this when wrapping every test in its own describe.

### Before

```typescript
describe('formatCurrency', () => {
  it('formats USD', () => {
    expect(formatCurrency(1000, 'USD')).toBe('$1,000.00');
  });
});

describe('formatCurrency negative', () => {
  it('formats negative USD', () => {
    expect(formatCurrency(-1000, 'USD')).toBe('-$1,000.00');
  });
});
```

### After

```typescript
describe('formatCurrency', () => {
  it('formats positive USD amounts', () => {
    expect(formatCurrency(1000, 'USD')).toBe('$1,000.00');
  });

  it('formats negative USD amounts with a leading minus', () => {
    expect(formatCurrency(-1000, 'USD')).toBe('-$1,000.00');
  });
});
```

**Safety notes**
- Safe to flag; consolidation is a style improvement.
- Do not auto-merge if the two describes have different `beforeEach`/`afterEach` hooks.

---

## 9. Enzyme `instance()` and Component Internal Access

**Risk: 4 / 5**

Enzyme's `instance()` returns the class component instance, exposing private methods and
state. This pattern is incompatible with hooks, function components, and the "test from the
user's perspective" philosophy.

### Before

```typescript
import { mount } from 'enzyme';
import { LoginForm } from './LoginForm';

it('validates email on blur', () => {
  const wrapper = mount(<LoginForm />);
  const instance = wrapper.instance() as LoginForm;

  // Directly calling an internal method
  instance.validateEmail('not-an-email');

  expect(wrapper.state('emailError')).toBe('Invalid email address');
});
```

### After

```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginForm } from './LoginForm';

it('shows a validation error when the email is invalid', async () => {
  const user = userEvent.setup();
  render(<LoginForm />);

  await user.click(screen.getByLabelText(/email/i));
  await user.type(screen.getByLabelText(/email/i), 'not-an-email');
  await user.tab(); // blur

  expect(screen.getByRole('alert')).toHaveTextContent('Invalid email address');
});
```

**Safety notes**
- `wrapper.instance()` and `wrapper.state()` are Enzyme-specific and always flaggable.
- `shallow()` rendering is lower risk but still couples tests to component tree shape.
- Enzyme is unmaintained for React 18+; flag any Enzyme import in a React 18+ project.

---

## 10. Over-use of `waitFor` in React Testing Library

**Risk: 3 / 5**

AI wraps synchronous assertions in `waitFor` to silence "act()" warnings rather than fixing
the underlying cause. This slows tests and masks timing issues.

### Before

```typescript
it('displays the submitted form data', async () => {
  render(<StaticForm name="Alice" />);

  // waitFor is unnecessary — nothing async is happening
  await waitFor(() => {
    expect(screen.getByText('Alice')).toBeInTheDocument();
  });
});
```

### After

```typescript
it('displays the submitted form data', () => {
  render(<StaticForm name="Alice" />);
  expect(screen.getByText('Alice')).toBeInTheDocument();
});
```

**Correct `waitFor` usage**

```typescript
it('shows the user list after data loads', async () => {
  server.use(
    rest.get('/api/users', (req, res, ctx) =>
      res(ctx.json([{ id: 1, name: 'Alice' }]))
    )
  );

  render(<UserList />);

  // Correct: waiting for an async network response to render
  await waitFor(() => {
    expect(screen.getByText('Alice')).toBeInTheDocument();
  });
});
```

**Prefer `findBy` over `waitFor` + `getBy`**

```typescript
// Instead of:
await waitFor(() => expect(screen.getByText('Alice')).toBeInTheDocument());

// Use:
expect(await screen.findByText('Alice')).toBeInTheDocument();
```

**Safety notes**
- `waitFor` wrapping a synchronous render assertion with no preceding async operation is
  always a flag.
- `waitFor` that wraps multiple assertions can hide which assertion is the one actually
  waiting — split into separate `findBy` or `waitFor` calls.

---

## 11. `fireEvent` Instead of `@testing-library/user-event`

**Risk: 3 / 5**

`fireEvent` dispatches a single synthetic DOM event. Real users trigger sequences: focus,
keydown, input, keyup, change, blur. `userEvent` simulates this full sequence, catching bugs
that `fireEvent` misses (e.g., validation that fires on `blur` or `keyup`).

### Before

```typescript
import { fireEvent, render, screen } from '@testing-library/react';
import { SearchBar } from './SearchBar';

it('filters results on input', () => {
  const onSearch = jest.fn();
  render(<SearchBar onSearch={onSearch} />);

  fireEvent.change(screen.getByRole('searchbox'), {
    target: { value: 'react' },
  });

  expect(onSearch).toHaveBeenCalledWith('react');
});
```

### After

```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SearchBar } from './SearchBar';

it('filters results as the user types', async () => {
  const user = userEvent.setup();
  const onSearch = jest.fn();
  render(<SearchBar onSearch={onSearch} />);

  await user.type(screen.getByRole('searchbox'), 'react');

  expect(onSearch).toHaveBeenLastCalledWith('react');
});
```

**When `fireEvent` is acceptable**
- Unit tests of pure event handler functions outside React.
- Simulating events not yet supported by `userEvent` (e.g., drag-and-drop in older versions).
- Performance-critical test suites where the overhead of `userEvent` is measurable.

**Safety notes**
- `fireEvent.change` / `fireEvent.click` in any RTL test is a flag for replacement.
- `userEvent` v14+ requires `userEvent.setup()` before `render` and all interactions must
  be awaited.

---

## 12. Missing Error Path Tests

**Risk: 4 / 5**

AI generates happy-path tests almost exclusively. Error branches (network failure, invalid
input, permission denied) are the paths most likely to cause production incidents.

### Before

```typescript
describe('createUser', () => {
  it('creates a user successfully', async () => {
    const user = await createUser({ name: 'Alice', email: 'alice@example.com' });
    expect(user.id).toBeDefined();
  });
  // No tests for: duplicate email, missing required fields, DB error, rate limiting
});
```

### After

```typescript
describe('createUser', () => {
  it('creates a user and returns the new id', async () => {
    const user = await createUser({ name: 'Alice', email: 'alice@example.com' });
    expect(user.id).toBeDefined();
    expect(user.name).toBe('Alice');
  });

  it('throws DuplicateEmailError when the email already exists', async () => {
    await createUser({ name: 'Alice', email: 'alice@example.com' });
    await expect(
      createUser({ name: 'Bob', email: 'alice@example.com' })
    ).rejects.toThrow(DuplicateEmailError);
  });

  it('throws ValidationError when required fields are missing', async () => {
    await expect(createUser({ name: '' } as any)).rejects.toThrow(ValidationError);
  });

  it('surfaces database errors without leaking internal details', async () => {
    jest.spyOn(db, 'insert').mockRejectedValue(new Error('Connection refused'));
    await expect(
      createUser({ name: 'Alice', email: 'alice@example.com' })
    ).rejects.toThrow('Unable to create user');
  });
});
```

**Safety notes**
- Cannot be auto-fixed; requires domain knowledge about possible failure modes.
- Flag any `describe` block with zero tests that call `rejects` or test error branches.

---

## 13. `it.only` / `describe.only` / `fdescribe` Left In

**Risk: 5 / 5**

Focus modifiers make the test runner execute only those tests. When committed, the entire
rest of the test suite is silently skipped. CI may still pass because the focused tests pass.

### Before

```typescript
describe('PaymentService', () => {
  it.only('processes a Stripe payment', async () => {  // ALL other tests skipped
    // ...
  });

  it('handles a declined card', async () => {
    // never runs
  });
});

fdescribe('refund flow', () => {  // Jasmine-style, also skips everything else
  // ...
});
```

### After

```typescript
describe('PaymentService', () => {
  it('processes a Stripe payment', async () => {
    // ...
  });

  it('handles a declined card', async () => {
    // ...
  });
});

describe('refund flow', () => {
  // ...
});
```

**Detection patterns**

```
it.only(
describe.only(
test.only(
fit(
fdescribe(
xit(           // also a flag — skipped tests should be deleted or tracked
xdescribe(
it.skip(       // lower urgency but still worth flagging
```

**Safety notes**
- This is one of the safest automatic fixes: remove `.only` / `f` prefix.
- Preserve `it.skip` / `xit` as a warning rather than auto-removing — the author may have
  intentionally skipped a known-failing test with a ticket reference.
- Add a CI lint rule: `eslint-plugin-jest` rule `no-focused-tests`.

---

## 14. Mock Factories Without Realistic Data

**Risk: 2 / 5**

`{ name: "test", email: "test", id: 1 }` everywhere. When business logic depends on data
shape (e.g., email validation, id format, date parsing), these placeholders produce false
positives.

### Before

```typescript
const mockUser = { id: 1, name: 'test', email: 'test', createdAt: 'test' };
const mockOrder = { id: 1, userId: 1, items: [], total: 0, status: 'test' };
```

### After — use a factory with realistic defaults

```typescript
// test/factories/user.factory.ts
import { faker } from '@faker-js/faker';
import type { User } from '../../src/types';

export function buildUser(overrides: Partial<User> = {}): User {
  return {
    id: faker.string.uuid(),
    name: faker.person.fullName(),
    email: faker.internet.email(),
    createdAt: faker.date.past().toISOString(),
    ...overrides,
  };
}

// In tests
const alice = buildUser({ name: 'Alice', email: 'alice@example.com' });
const adminUser = buildUser({ role: 'admin' });
```

**Realistic data catches real bugs**
- Email validation that rejects `"test"` as an invalid address.
- UUID parsers that fail on integer `1`.
- Date arithmetic that breaks on the string `"test"`.

**Safety notes**
- `@faker-js/faker` is the standard replacement for the deprecated `faker` package.
- Seed faker in `beforeEach` for reproducible failures: `faker.seed(12345)`.
- Do not add randomness to snapshot tests — use fixed overrides.

---

## 15. Testing Third-Party Library Behaviour

**Risk: 2 / 5**

AI writes tests that assert what a library does rather than what the application does with
the library's output. If the library changes, the test breaks even if the application is
unaffected; if the library has a bug, the test hides it.

### Before

```typescript
it('sorts an array in ascending order', () => {
  // Testing lodash, not the application
  const result = _.sortBy([3, 1, 2]);
  expect(result).toEqual([1, 2, 3]);
});

it('formats a date', () => {
  // Testing date-fns, not the application
  expect(format(new Date('2024-01-15'), 'yyyy-MM-dd')).toBe('2024-01-15');
});
```

### After

```typescript
it('returns products ordered by price ascending', () => {
  const products = [
    buildProduct({ price: 30 }),
    buildProduct({ price: 10 }),
    buildProduct({ price: 20 }),
  ];

  const sorted = sortProductsByPrice(products);

  expect(sorted.map((p) => p.price)).toEqual([10, 20, 30]);
});

it('formats an invoice date for display', () => {
  const invoice = buildInvoice({ date: new Date('2024-01-15') });
  expect(formatInvoiceDate(invoice)).toBe('January 15, 2024');
});
```

**Safety notes**
- Cannot be auto-detected reliably; requires human review.
- Flag tests that import from `lodash`, `date-fns`, `axios`, etc. and assert on their
  return values directly without going through application code.

---

## 16. Giant Test Files with No Organisation

**Risk: 2 / 5**

AI appends tests to a single file until it exceeds 500 lines. Unrelated concerns share a
file, `beforeEach` hooks become overly broad, and `describe` nesting becomes 4+ levels deep.

### Before

```
user.test.ts  (800 lines)
  describe('UserService') {
    describe('auth') {
      describe('login') {
        describe('with valid credentials') {
          it(...)
          it(...)
        }
      }
    }
    describe('profile') { ... }
    describe('billing') { ... }     // billing logic in a user test file
    describe('notifications') { ... }
  }
```

### After

```
user/
  user.service.test.ts          (auth + profile — core user concerns)
  user-billing.service.test.ts  (billing, owns its own mocks)
  user-notifications.test.ts    (notification triggers)
```

**Heuristics for splitting**

- Each top-level `describe` in a file should map to one exported class or function.
- If a `beforeEach` sets up more than 3 unrelated mocks, the file probably covers too many
  concerns.
- 4+ levels of `describe` nesting is a reliable smell.

**Safety notes**
- Splitting requires understanding import graphs; cannot be auto-fixed safely.
- Flag files over 400 lines as a warning with suggested split points.

---

## 17. No Integration or E2E Layer

**Risk: 3 / 5**

AI generates unit tests with every collaborator mocked. The application may pass all unit
tests and still fail when real services connect because the integration assumptions are wrong.

### Symptoms

- 100% unit test coverage but frequent production regressions on API contract changes.
- Every external call mocked with `jest.mock('axios')` or `jest.mock('node-fetch')`.
- No test exercises a real database query, even against SQLite.

### Recommended test pyramid

```
                    [E2E]          < 10 tests — critical user journeys
               [Integration]      50–100 tests — real DB, real HTTP (MSW or test server)
          [Unit]                  majority — pure functions, business logic
```

### Integration test example with a real DB

```typescript
// user.integration.test.ts
import { createPool } from '../src/db';
import { UserRepository } from '../src/user.repository';

describe('UserRepository (integration)', () => {
  let pool: Pool;
  let repo: UserRepository;

  beforeAll(async () => {
    pool = createPool({ connectionString: process.env.TEST_DATABASE_URL });
    await pool.query('BEGIN');
    repo = new UserRepository(pool);
  });

  afterAll(async () => {
    await pool.query('ROLLBACK');
    await pool.end();
  });

  it('persists and retrieves a user', async () => {
    const created = await repo.create({ name: 'Alice', email: 'alice@example.com' });
    const found = await repo.findById(created.id);
    expect(found).toMatchObject({ name: 'Alice', email: 'alice@example.com' });
  });
});
```

**Safety notes**
- This cannot be auto-fixed; it requires architecture decisions.
- Flag test suites where every network/DB call is mocked with no integration counterpart.

---

## 18. `console.log` Left in Tests

**Risk: 1 / 5**

AI adds `console.log` during generation for debugging context. Left in, it pollutes CI
output, hides real errors in noise, and signals the test was never properly reviewed.

### Before

```typescript
it('calculates the correct tax', () => {
  const result = calculateTax(100, 'CA');
  console.log('result:', result);         // debugging artifact
  console.log('expected:', 8.25);
  expect(result).toBe(8.25);
});
```

### After

```typescript
it('calculates California sales tax on $100', () => {
  expect(calculateTax(100, 'CA')).toBe(8.25);
});
```

**Enforce via lint**

```json
// eslint config
{
  "rules": {
    "no-console": ["error", { "allow": ["warn", "error"] }]
  }
}
```

**Safety notes**
- Safe to auto-remove standalone `console.log` / `console.dir` / `console.table` lines.
- Do not remove `console.error` or `console.warn` calls that are part of the assertion
  (e.g., testing that a component logs a warning).

---

## 19. Hardcoded `setTimeout` Delays in Tests

**Risk: 4 / 5**

`await new Promise(r => setTimeout(r, 1000))` is the most common cause of flaky tests.
The delay is arbitrarily chosen and fails on slow CI runners or passes too quickly on fast
ones.

### Before

```typescript
it('debounces the search input', async () => {
  const onSearch = jest.fn();
  render(<SearchBar onSearch={onSearch} debounceMs={300} />);

  userEvent.type(screen.getByRole('searchbox'), 'react');

  // Arbitrary sleep — flaky on slow CI
  await new Promise((r) => setTimeout(r, 500));

  expect(onSearch).toHaveBeenCalledTimes(1);
});
```

### After — use fake timers

```typescript
it('debounces the search input', async () => {
  jest.useFakeTimers();
  const onSearch = jest.fn();
  render(<SearchBar onSearch={onSearch} debounceMs={300} />);

  await userEvent.type(screen.getByRole('searchbox'), 'react');
  expect(onSearch).not.toHaveBeenCalled(); // still debouncing

  jest.advanceTimersByTime(300);

  expect(onSearch).toHaveBeenCalledWith('react');
  jest.useRealTimers();
});
```

### After — use RTL `waitFor` with a condition (for real async)

```typescript
it('shows a success toast after saving', async () => {
  render(<ProfileForm />);
  await userEvent.click(screen.getByRole('button', { name: /save/i }));

  // waitFor polls until condition is met or times out
  await waitFor(() =>
    expect(screen.getByRole('status')).toHaveTextContent('Saved!')
  );
});
```

**Safety notes**
- `setTimeout(r, N)` / `sleep(N)` inside a test body is always a flag.
- `jest.useFakeTimers()` must be paired with `jest.useRealTimers()` in `afterEach`.
- In Vitest, use `vi.useFakeTimers()` / `vi.useRealTimers()`.

---

## 20. Missing `expect.assertions(n)` in Async Error Tests

**Risk: 5 / 5**

If an async function resolves instead of rejecting (e.g., because the error was swallowed),
a `catch` block with an `expect` inside it is never reached. The test passes with zero
assertions — a false positive.

### Before

```typescript
it('rejects when the API returns 401', async () => {
  fetchMock.mockRejectOnce(new UnauthorizedError());

  try {
    await fetchUser(1);
  } catch (err) {
    // If fetchUser() resolves instead of rejecting, this block never runs.
    // The test passes silently with 0 assertions.
    expect(err).toBeInstanceOf(UnauthorizedError);
  }
});
```

### After — option A: `expect.assertions`

```typescript
it('rejects when the API returns 401', async () => {
  expect.assertions(1); // MUST reach exactly 1 assertion or the test fails

  fetchMock.mockRejectOnce(new UnauthorizedError());

  try {
    await fetchUser(1);
  } catch (err) {
    expect(err).toBeInstanceOf(UnauthorizedError);
  }
});
```

### After — option B: `rejects` (preferred for simple cases)

```typescript
it('rejects when the API returns 401', async () => {
  fetchMock.mockRejectOnce(new UnauthorizedError());

  await expect(fetchUser(1)).rejects.toBeInstanceOf(UnauthorizedError);
});
```

**Safety notes**
- `expect.assertions(n)` is mandatory in any `try/catch` async test.
- Prefer `rejects` matchers — they are shorter and automatically fail if the promise resolves.
- In Vitest, `expect.assertions` works identically.

---

## React Testing Library Best Practices

### Query priority (highest to lowest confidence)

Prefer queries in this order — higher queries are more resilient to implementation changes
and better reflect how users perceive the UI.

| Priority | Query | Use when |
|----------|-------|----------|
| 1 | `getByRole` | Most elements have an implicit ARIA role |
| 2 | `getByLabelText` | Form fields associated with a label |
| 3 | `getByPlaceholderText` | Input without a label (last resort) |
| 4 | `getByText` | Non-interactive elements, buttons without roles |
| 5 | `getByDisplayValue` | Selected form values |
| 6 | `getByAltText` | Images |
| 7 | `getByTitle` | Tooltip-like elements |
| 8 | `getByTestId` | Only when no semantic query is possible |

### `getBy` vs `queryBy` vs `findBy`

```typescript
// getBy — throws if not found. Use for elements that must be present.
const button = screen.getByRole('button', { name: /submit/i });

// queryBy — returns null if not found. Use for asserting absence.
expect(screen.queryByRole('alert')).not.toBeInTheDocument();

// findBy — async, returns a promise. Use when element appears after async work.
const alert = await screen.findByRole('alert');
```

### Accessible queries with roles

```typescript
// Roles are implicit in HTML semantics
screen.getByRole('button')       // <button>, <input type="button">
screen.getByRole('textbox')      // <input type="text">, <textarea>
screen.getByRole('checkbox')     // <input type="checkbox">
screen.getByRole('heading')      // <h1>–<h6>
screen.getByRole('list')         // <ul>, <ol>
screen.getByRole('listitem')     // <li>
screen.getByRole('link')         // <a href>
screen.getByRole('img')          // <img>
screen.getByRole('dialog')       // <dialog> or role="dialog"

// Name filter for disambiguation
screen.getByRole('button', { name: /submit order/i })
```

### Setting up `userEvent` correctly

```typescript
import userEvent from '@testing-library/user-event';

describe('LoginForm', () => {
  // userEvent.setup() must be called OUTSIDE beforeEach if you need to share
  // the instance, or inside if each test needs a clean pointer state.
  it('submits with valid credentials', async () => {
    const user = userEvent.setup(); // v14+ API
    render(<LoginForm onSubmit={jest.fn()} />);

    await user.type(screen.getByLabelText(/email/i), 'alice@example.com');
    await user.type(screen.getByLabelText(/password/i), 'hunter2');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    expect(screen.getByRole('status')).toHaveTextContent('Welcome back');
  });
});
```

### Avoid leaking renders between tests

RTL's `@testing-library/react` auto-calls `cleanup` after each test if you use a compatible
test framework configuration. Verify this is set up:

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
  },
});

// src/test/setup.ts
import '@testing-library/jest-dom';
// cleanup is automatic when using vitest with jsdom
```

---

## MSW vs Fetch Mocking

### Why MSW is preferred

`jest.mock('node-fetch')` or `global.fetch = jest.fn()` patches at the JavaScript module
level. MSW intercepts at the network level, meaning:

- The real HTTP client code runs (headers, error handling, retry logic).
- Integration tests and browser tests can share the same handlers.
- No module system coupling — works with any fetch implementation.

### `fetch` mock (avoid for anything beyond unit tests)

```typescript
// Brittle: couples to the exact fetch call site
global.fetch = jest.fn().mockResolvedValue({
  ok: true,
  json: async () => ({ id: 1, name: 'Alice' }),
});

const user = await fetchUser(1);
expect(user.name).toBe('Alice');

// Does not test: request URL correctness, headers, error status handling
```

### MSW setup (preferred)

```typescript
// src/test/server.ts
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

export const server = setupServer(
  http.get('https://api.example.com/users/:id', ({ params }) => {
    return HttpResponse.json({ id: params.id, name: 'Alice' });
  })
);

// src/test/setup.ts
import { server } from './server';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

```typescript
// In a test — override a handler for a specific scenario
import { http, HttpResponse } from 'msw';
import { server } from '../test/server';

it('shows an error when the user is not found', async () => {
  server.use(
    http.get('https://api.example.com/users/:id', () => {
      return HttpResponse.json({ message: 'Not found' }, { status: 404 });
    })
  );

  render(<UserProfile userId="999" />);

  await waitFor(() =>
    expect(screen.getByRole('alert')).toHaveTextContent('User not found')
  );
});
```

### Comparison

| Concern | `fetch` mock | MSW |
|---------|-------------|-----|
| Tests real HTTP client code | No | Yes |
| Tests request URL | No | Yes |
| Tests request headers | Partial | Yes |
| Works in browser tests | No | Yes |
| Handles streaming / SSE | No | Yes |
| Setup overhead | Low | Medium |
| Recommended for unit tests | Acceptable | Preferred |
| Recommended for integration | No | Yes |

---

## Vitest-Specific Gotchas

### `vi.mock()` hoisting

Vitest (like Jest) hoists `vi.mock()` calls to the top of the file via a Babel/Vite
transform. This means code written after `vi.mock()` in source order actually executes before
it. Variables defined in the test file scope are not yet initialised when the factory runs.

```typescript
// BROKEN — factory runs before mockFn is defined
const mockFn = vi.fn();

vi.mock('./service', () => ({
  doSomething: mockFn, // undefined at hoist time
}));
```

### `vi.hoisted` — the correct pattern

```typescript
import { vi } from 'vitest';

// vi.hoisted runs at hoist time, so the result is available to vi.mock factories
const { mockFn } = vi.hoisted(() => ({
  mockFn: vi.fn(),
}));

vi.mock('./service', () => ({
  doSomething: mockFn,
}));

it('calls the service', () => {
  mockFn.mockReturnValue(42);
  // ...
});
```

### `vi.mock` factory must be synchronous

```typescript
// BROKEN — async factory
vi.mock('./db', async () => {
  const actual = await import('./db');  // this causes issues
  return { ...actual, query: vi.fn() };
});

// CORRECT — use importActual inside a synchronous factory
vi.mock('./db', async (importActual) => {
  const actual = await importActual<typeof import('./db')>();
  return { ...actual, query: vi.fn() };
});
```

### Module resolution differences from Jest

```typescript
// Jest uses CommonJS by default; Vitest uses ESM
// In Vitest, default exports from mocked modules must be explicit:

vi.mock('./logger', () => ({
  default: { log: vi.fn(), error: vi.fn() }, // must include `default` key
}));
```

### `vi.spyOn` restoring behaviour

```typescript
// Vitest does NOT automatically restore spies after each test unless configured
// Add to vitest.config.ts:
export default defineConfig({
  test: {
    restoreMocks: true,   // equivalent to jest.restoreAllMocks() after each test
    clearMocks: true,     // clears call history
    resetMocks: false,    // does not reset implementation
  },
});
```

### Fake timers in Vitest

```typescript
import { vi, beforeEach, afterEach, it, expect } from 'vitest';

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

it('fires the callback after the delay', () => {
  const callback = vi.fn();
  setTimeout(callback, 1000);

  vi.advanceTimersByTime(1000);

  expect(callback).toHaveBeenCalledTimes(1);
});
```

### `expect.soft` — Vitest-only

Vitest's `expect.soft` collects assertion failures without stopping the test, useful for
validating multiple fields of an object in one pass:

```typescript
it('returns a correctly shaped user object', async () => {
  const user = await fetchUser(1);

  expect.soft(user.id).toBeDefined();
  expect.soft(user.name).toBe('Alice');
  expect.soft(user.email).toMatch(/@/);
  // All three failures reported in one test run, not just the first
});
```

### `test.concurrent` — parallelism gotcha

```typescript
// Concurrent tests share module-level state — avoid mutable module-level state
// or use test.each with isolated fixtures

describe.concurrent('parallel-safe tests', () => {
  it('test A', async ({ expect }) => {
    // Use the injected `expect` in concurrent tests, not the global one
    expect(1 + 1).toBe(2);
  });
});
```

---

## Deslopper Decision Reference

| Signal | Action |
|--------|--------|
| `jest.mock('./same-file-as-sut')` | Error — remove mock, mock dependency instead |
| `it.only` / `fit` / `fdescribe` in committed code | Error — remove focus modifier |
| `expect(promise).resolves` without `await` | Error — add `await` |
| `wrapper.instance()` / `wrapper.state()` | Error — rewrite with RTL |
| `expect.assertions` missing in `try/catch` async test | Error — add `expect.assertions(1)` |
| `setTimeout(r, N)` in test body | Warning — replace with fake timers |
| `fireEvent` in RTL test | Warning — consider `userEvent` |
| `toMatchSnapshot()` on a React component | Warning — replace with semantic assertions |
| `expect.anything()` on a known-value field | Warning — use specific value |
| `console.log` in test body | Info — remove |
| `describe` with a single `it` | Info — flatten |
| `beforeAll` with mutable `let` variable | Warning — move to `beforeEach` |
| No `afterEach` cleanup after `beforeEach` setup | Warning — add cleanup |
| Mock factory with `{ name: "test" }` | Info — use a factory function |
