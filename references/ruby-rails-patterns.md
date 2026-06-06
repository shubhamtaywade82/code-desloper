# Ruby & Rails Anti-Patterns

This reference guide lists common AI-generated and legacy anti-patterns in Ruby on Rails applications and provides idiomatic refactoring solutions.

## 1. Service Object Overkill
**Smell:** Creating a Service Object (e.g., `UpdateUserBio.call(user, bio)`) for a simple one-line attribute update that belongs in the model.
**Idiomatic Fix:** Move simple logic back to the Model or Controller. Use Service Objects only for complex orchestration involving multiple models, transactions, or external APIs.

## 2. Redundant Concerns
**Smell:** Extracting a `Concern` for logic that is only used by one model or is a collection of unrelated helper methods.
**Idiomatic Fix:** Keep logic in the model until it is actually shared across ≥2 models.

## 3. Callback Hell (AI-Generated Boilerplate)
**Smell:** AI assistants often add `after_create :send_welcome_email` which makes testing difficult and couples models to side effects.
**Idiomatic Fix:** Move side-effect orchestration to a Service Object or the Controller using an explicit workflow.

## 4. Fat Controllers with Placeholder Logic
**Smell:** Large controller actions that contain complex business logic or AI-generated `TODO` comments.
**Idiomatic Fix:** Move business logic to Models (for single-model state) or Service Objects (for orchestration).

## 5. Unnecessary `BaseService` or `BaseManager`
**Smell:** Empty parent classes created by AI to "look enterprise" but providing no real functionality.
**Idiomatic Fix:** Delete the base class and use Plain Old Ruby Objects (POROs).

## 6. Duplicated Validations
**Smell:** Repeating the same `validates :email, presence: true` in multiple models without using a shared validator or common pattern.
**Idiomatic Fix:** Use a custom `EachValidator` or a shared Concern if the models are conceptually related.

## 7. Explicit `return` in every method
**Smell:** AI-generated Ruby often includes explicit `return` statements at the end of methods, which is non-idiomatic.
**Idiomatic Fix:** Remove explicit `return` for the last expression.

## 8. Verbose String Interpolation
**Smell:** `"Hello, " + user.name` instead of `"Hello, #{user.name}"`.
**Idiomatic Fix:** Use standard Ruby interpolation.
