# Python / Django / FastAPI — AI Slop Patterns & Idiomatic Fixes

## CLASS ANTI-PATTERNS

### 1. Trivial Dataclass → TypedDict or Plain Dict
**Smell:** `@dataclass` with only field declarations; no methods, no validation, no default factories.
**Fix:** Use `TypedDict` for type annotations without runtime overhead, or a plain dict.
**Safety:** Check for `isinstance(obj, MyClass)` checks and `__eq__`/`__hash__` reliance.

```python
# BEFORE (AI slop)
@dataclass
class UserData:
    id: int
    name: str
    email: str

# AFTER — if only used for typing
class UserData(TypedDict):
    id: int
    name: str
    email: str

# AFTER — if used as a plain dict (simple cases)
# Just use dict[str, Any] with Pydantic/TypedDict for the API boundary
```

### 2. Fake Abstract Base Class → Delete the ABC
**Smell:** `ABC` with one abstract method and only one concrete subclass. No polymorphism.
**Fix:** Delete the ABC. Use the concrete class directly.
**Safety:** Check for `register()` calls, `isinstance(obj, BaseClass)` checks, or public typing contracts.

```python
# BEFORE — fake abstraction, only EmailProcessor exists
class BaseProcessor(ABC):
    @abstractmethod
    def process(self, data: dict) -> dict:
        ...

class EmailProcessor(BaseProcessor):
    def process(self, data: dict) -> dict:
        return send_email(data['to'], data['body'])

# AFTER
class EmailProcessor:
    def process(self, data: dict) -> dict:
        return send_email(data['to'], data['body'])
```

### 3. One-Method Manager Class → Module Function
**Smell:** Class with a single public method, no internal state, no inheritance.
**Fix:** Replace with a module-level function.
**Safety:** No shared state, no dependency injection via `__init__`, no subclassing.

```python
# BEFORE
class EmailManager:
    def send_email(self, to: str, subject: str, body: str) -> bool:
        return smtp_client.send(to, subject, body)

manager = EmailManager()
manager.send_email(user.email, "Welcome", body)

# AFTER
def send_email(to: str, subject: str, body: str) -> bool:
    return smtp_client.send(to, subject, body)

send_email(user.email, "Welcome", body)
```

### 4. Unnecessary `@staticmethod` → Module Function
**Smell:** `@staticmethod` on a method that doesn't use `cls` or `self` and is called via instance.
**Fix:** Move to module level.
**Safety:** Check if callers use `ClassName.method()` for namespacing intentionally.

```python
# BEFORE
class Utils:
    @staticmethod
    def format_date(dt: datetime) -> str:
        return dt.strftime('%Y-%m-%d')

Utils.format_date(now)

# AFTER
def format_date(dt: datetime) -> str:
    return dt.strftime('%Y-%m-%d')

format_date(now)
```

---

## EXCEPTION HANDLING

### 5. Bare `except` or `except Exception: pass` → Specific Exception
**Smell:** Swallows all exceptions including `KeyboardInterrupt`, `SystemExit`, `MemoryError`.
**Fix:** Catch only the specific exception(s) you can handle.

```python
# BEFORE — Risk 4 (swallows critical signals)
try:
    result = process(data)
except:
    pass

# BEFORE — still bad (too broad, silent)
try:
    result = process(data)
except Exception:
    pass

# AFTER
try:
    result = process(data)
except (ValueError, KeyError) as e:
    logger.warning("Invalid data: %s", e)
    result = default_value
```

### 6. Nested Function Pyramid → Flat Module Functions
**Smell:** Functions nested 3+ levels deep; inner functions could be module-level.
**Fix:** Extract inner functions to module level if they don't need closure.
**Safety:** Check if inner functions capture outer variables via closure.

```python
# BEFORE
def process_order(order):
    def validate():
        def check_items():
            return len(order.items) > 0
        return check_items() and order.customer is not None
    def charge():
        return payment.charge(order.total)
    if validate():
        return charge()

# AFTER
def _order_has_items(order) -> bool:
    return len(order.items) > 0

def _order_is_valid(order) -> bool:
    return _order_has_items(order) and order.customer is not None

def process_order(order):
    if _order_is_valid(order):
        return payment.charge(order.total)
```

---

## TYPE HINTS ANTI-PATTERNS

### 7. `*args, **kwargs` Abuse → Explicit Parameters
**Smell:** Public methods using `*args, **kwargs` when the signature is known.
**Fix:** Explicit keyword arguments with types.
**Safety:** Check if dynamic dispatch or decorators depend on `*args/**kwargs`.

```python
# BEFORE
def create_user(*args, **kwargs):
    name = kwargs.get('name')
    email = kwargs.get('email')
    role = kwargs.get('role', 'user')
    return User(name=name, email=email, role=role)

# AFTER
def create_user(name: str, email: str, role: str = 'user') -> User:
    return User(name=name, email=email, role=role)
```

### 8. Over-Engineered Type Aliases → Delete or Inline
**Smell:** `UserId = str` used in only one place, adds no runtime validation.
**Fix:** Delete the alias; use `str` directly.
**Safety:** Keep if used across > 2 files to prevent primitive obsession.

```python
# BEFORE — used once
UserId = str
def find_user(user_id: UserId) -> User: ...

# AFTER
def find_user(user_id: str) -> User: ...

# KEEP if branded (NewType prevents mixing up int IDs)
from typing import NewType
UserId = NewType('UserId', int)
ProductId = NewType('ProductId', int)
# Now: find_user(ProductId(42))  → type error — correct
```

### 9. Redundant `Optional` / `Union` Syntax (Python 3.10+)
**Smell:** `Optional[X]` instead of `X | None`; `Union[X, Y]` instead of `X | Y`.
**Fix:** Use modern union syntax.
**Safety:** Only if project requires Python ≥ 3.10.

```python
# BEFORE (Python 3.9 style)
from typing import Optional, Union
def find_user(id: int) -> Optional[User]: ...
def process(value: Union[int, str]) -> str: ...

# AFTER (Python 3.10+)
def find_user(id: int) -> User | None: ...
def process(value: int | str) -> str: ...
```

### 10. `Any` Everywhere → Concrete Types
**Smell:** `def process(data: Any) -> Any:` — no type safety at all.
**Fix:** Use concrete types, TypedDict, Pydantic models, or generics.

```python
# BEFORE
def process_response(data: Any) -> Any:
    return data['items']

# AFTER
class ApiResponse(TypedDict):
    items: list[dict[str, str]]

def process_response(data: ApiResponse) -> list[dict[str, str]]:
    return data['items']
```

---

## DJANGO ANTI-PATTERNS

### 11. Trivial Class-Based View → Function View
**Smell:** CBV that only calls `Model.objects.create`; no `get_queryset`, no mixin, no permission class.
**Fix:** Convert to function-based view.
**Safety:** Check for DRF viewset inheritance, mixin usage, or `as_view()` with kwargs.

```python
# BEFORE
class CreateUserView(View):
    def post(self, request):
        data = json.loads(request.body)
        user = User.objects.create(**data)
        return JsonResponse({'id': user.id})

# AFTER
def create_user(request):
    data = json.loads(request.body)
    user = User.objects.create(**data)
    return JsonResponse({'id': user.id})
```

### 12. DRF Serializer Proxying Model Fields → ModelSerializer
**Smell:** Serializer manually declares every field that could use `Meta.fields`.
**Fix:** Use `ModelSerializer` with `fields = '__all__'` or explicit `fields` list.
**Safety:** Check for `SerializerMethodField`, custom `validate_*`, and `to_representation` overrides.

```python
# BEFORE — manually mirrors the model
class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    created_at = serializers.DateTimeField(read_only=True)

# AFTER
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'created_at']
        read_only_fields = ['id', 'created_at']
```

### 13. Empty Middleware / Decorator → Delete
**Smell:** Middleware or decorator class with `TODO` body and no real logic.
**Fix:** Delete. Middleware is not a placeholder.
**Safety:** Check if class is registered in `MIDDLEWARE` settings or used as `@decorator`.

```python
# BEFORE — registered in MIDDLEWARE but does nothing
class LoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # TODO: add logging
        return self.get_response(request)

# AFTER — delete until logging is actually implemented
```

---

## ASYNC ANTI-PATTERNS

### 14. `async` on CPU-Bound or I/O-Free Functions → `def`
**Smell:** `async def` on a function that does no I/O, no `await`, no coroutine.
**Fix:** Remove `async`. CPU-bound functions in async frameworks should use `run_in_executor`.

```python
# BEFORE — no await, no I/O; async adds overhead without benefit
async def calculate_total(items: list[Item]) -> Decimal:
    return sum(item.price * item.quantity for item in items)

# AFTER
def calculate_total(items: list[Item]) -> Decimal:
    return sum(item.price * item.quantity for item in items)
```

### 15. Unnecessary `asyncio.gather` for Single Coroutine → Direct `await`

```python
# BEFORE — gather with one task is just noise
results = await asyncio.gather(fetch_user(user_id))
user = results[0]

# AFTER
user = await fetch_user(user_id)
```

---

## MODULE / PACKAGE ANTI-PATTERNS

### 16. `utils.py` Blob → Split by Domain
**Smell:** Single `utils.py` with 20+ unrelated functions spanning formatting, validation, HTTP, file I/O.
**Fix:** Split into focused modules: `formatting.py`, `validators.py`, `http_utils.py`.
**Safety:** Update all import paths across the codebase simultaneously.

```python
# BEFORE — utils.py with everything
def format_date(dt): ...
def validate_email(email): ...
def make_request(url): ...
def read_csv(path): ...

# AFTER
# formatting.py: format_date
# validators.py: validate_email
# http_client.py: make_request
# file_utils.py: read_csv
```

### 17. `__init__.py` Re-Export Bloat → Explicit `__all__`
**Smell:** `__init__.py` wildcard-imports everything, exposing internal modules.
**Fix:** Use explicit `__all__` with only the public API.

```python
# BEFORE — __init__.py
from .models import *
from .services import *
from .utils import *

# AFTER
__all__ = ['User', 'Order', 'create_order', 'cancel_order']
from .models import User, Order
from .services import create_order, cancel_order
```

---

## DATA / COMPREHENSION ANTI-PATTERNS

### 18. Nested List Comprehension Abuse → Explicit Generator or Loop
**Smell:** 3-level nested comprehension; unreadable in one line.
**Fix:** Use an explicit `for` loop or named generator.

```python
# BEFORE — impenetrable
result = [x for row in matrix for x in row if x > 0 and x % 2 == 0]

# AFTER — readable
def positive_evens(matrix):
    for row in matrix:
        for x in row:
            if x > 0 and x % 2 == 0:
                yield x

result = list(positive_evens(matrix))
```

### 19. Pandas for Simple List Operations → Plain Python
**Smell:** `pd.DataFrame` created only to use `.apply` or `.iterrows` on a small list.
**Fix:** Use built-in list comprehensions, `map`, or `itertools`.
**Safety:** Keep Pandas when vectorization, groupby, or large data is involved.

```python
# BEFORE — Pandas for a 10-item list
import pandas as pd
df = pd.DataFrame(users)
names = df['name'].apply(str.upper).tolist()

# AFTER
names = [user['name'].upper() for user in users]
```

---

## TESTING ANTI-PATTERNS

### 20. `mock.patch` on Everything → Refactor for Testability
**Smell:** Test with 5+ `@mock.patch` decorators — sign that dependencies are not injected.
**Fix:** Refactor the production code to accept dependencies via constructor or function args.
**Safety:** Risk 3 — refactoring for testability changes the production interface.

```python
# BEFORE — test is a patch maze
@mock.patch('app.services.email.smtp_client')
@mock.patch('app.services.email.logger')
@mock.patch('app.models.user.User.objects.get')
@mock.patch('app.services.email.render_template')
@mock.patch('app.services.email.validate_address')
def test_send_welcome(self, mock_validate, mock_render, mock_get, mock_logger, mock_smtp):
    ...

# AFTER — inject dependencies
class EmailService:
    def __init__(self, smtp_client, template_engine, logger):
        self.smtp = smtp_client
        self.templates = template_engine
        self.logger = logger

# Test with real fakes, not patches:
def test_send_welcome():
    service = EmailService(
        smtp_client=FakeSMTP(),
        template_engine=FakeTemplates(),
        logger=logging.getLogger('test')
    )
    service.send_welcome(user)
```

---

## Python Tool Integration

| Tool | Command | What to Feed Deslopper |
|---|---|---|
| **Ruff** | `ruff check --select E,W,F,I,UP,ANN --output-format json .` | Style + complexity + unused import flags |
| **Pylint** | `pylint --output-format=json app/` | Unreachable code, too-many-args, too-many-branches |
| **mypy** | `mypy --strict --show-error-codes .` | `Any` abuse, missing types, incompatible overrides |
| **Bandit** | `bandit -r app/ -f json` | Security: bare except, eval, hardcoded passwords |
| **Vulture** | `vulture app/` | Dead code: unused functions, classes, variables |
| **Radon** | `radon cc app/ -s -j` | Cyclomatic complexity per function |

### Phase 1 Pipeline

```bash
ruff check --select E,W,F,I,UP,ANN --output-format json . > ruff.json
pylint --output-format=json app/ > pylint.json
mypy --strict --show-error-codes . 2>&1 > mypy.txt
vulture app/ > vulture.txt
bandit -r app/ -f json > bandit.json
radon cc app/ -s -j > radon.json
```

---

## Python Safety Rules

- Never remove a `@dataclass` if code uses `isinstance(obj, MyClass)` or relies on `__eq__`/`__hash__`.
- Never delete an ABC if `register()` is used or if it's part of a public typing contract in a library.
- Never flatten `async` functions that are part of an async API boundary (FastAPI route handlers, aiohttp views).
- Never remove `@staticmethod` if callers use `ClassName.method()` for explicit namespacing.
- Never inline a Django/FastAPI view if DRF viewsets, permissions, or throttles depend on CBV structure.
- Never change `*args, **kwargs` if dynamic dispatch or decorators wrap the function.
- Never modernize `Optional[X]` → `X | None` if the project requires Python < 3.10.
- Never remove a `__init__.py` export without checking all import paths in the codebase.
