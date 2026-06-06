# Go Anti-Patterns

This reference guide lists common AI-generated anti-patterns in Go (Golang) applications.

## 1. Premature Interface Abstraction
**Smell:** Creating an interface for every struct even if there is only one implementation.
**Idiomatic Fix:** "Accept interfaces, return structs." Do not create an interface until you have at least two implementations or a clear mocking requirement.

## 2. Deeply Nested Error Handling
**Smell:** Using `else` blocks for the main success path instead of early returns for errors.
**Idiomatic Fix:** Use the "Happy Path to the Left" pattern. Handle errors early and return.

## 3. "Manager" or "Service" Structs for Pure Functions
**Smell:** Creating a `struct UserManager {}` with methods that don't hold state, just to call `userManager.Update(user)`.
**Idiomatic Fix:** Use package-level functions. `user.Update(id, data)` or `UpdateUser(id, data)`.

## 4. Redundant Pointers
**Smell:** AI returning `*string` or `*int` for basic types without a clear need for `nil` values.
**Idiomatic Fix:** Return values by value for basic types unless `nil` has specific semantic meaning.

## 5. Unbuffered Channels for Simple Coordination
**Smell:** Using channels and goroutines where a simple function call or `sync.WaitGroup` would suffice.
**Idiomatic Fix:** Keep it simple. Use concurrency only when there is actual parallelism or IO-bound waiting to be done.

## 6. Getter/Setter Boilerplate
**Smell:** AI creating `GetField()` and `SetField()` for every struct field in Go.
**Idiomatic Fix:** Use exported fields if they are simple, or just a direct field name for the getter (e.g., `Field()` instead of `GetField()`).

## 7. Interface Pollution (Large Interfaces)
**Smell:** AI creating interfaces with 10+ methods.
**Idiomatic Fix:** "The bigger the interface, the weaker the abstraction." Keep interfaces small (1-3 methods).
