# Python Anti-Patterns

This reference guide lists common AI-generated and legacy anti-patterns in Python applications.

## 1. Abstract Base Class (ABC) Overkill
**Smell:** AI creating `abc.ABC` for simple functions or one-off classes to "look architected."
**Idiomatic Fix:** Use plain classes or just functions. Duck typing is often sufficient in Python.

## 2. Redundant Docstrings
**Smell:** Docstrings that provide zero additional value, e.g., `def get_user(id): """Gets the user by ID."""`.
**Idiomatic Fix:** Remove redundant docstrings. Use them only to explain complex logic, side effects, or non-obvious return values.

## 3. Non-Idiomatic Iteration
**Smell:** Using `for i in range(len(items)): item = items[i]` instead of `for item in items:`.
**Idiomatic Fix:** Use direct iteration or `enumerate()` if the index is needed.

## 4. Deeply Nested Try-Except
**Smell:** Large blocks of code wrapped in a single `try` block with generic `except Exception` handling.
**Idiomatic Fix:** Use granular `try` blocks and catch specific exceptions. Prefer "Look Before You Leap" (LBYL) for simple checks.

## 5. Explicit `__init__` Boilerplate (without dataclasses)
**Smell:** Verbose `__init__` methods that only assign parameters to attributes in Python 3.7+.
**Idiomatic Fix:** Use `@dataclass` to reduce boilerplate.

## 6. Type Hinting Mirrors (Boilerplate)
**Smell:** AI-generated types that are overly verbose or add no clarity to simple functions.
**Idiomatic Fix:** Use type hints for public APIs and complex data structures, but avoid cluttering simple internal logic.

## 7. `if x == True:` or `if len(x) > 0:`
**Smell:** Non-idiomatic truthiness checks.
**Idiomatic Fix:** Use `if x:` or `if not x:`.
