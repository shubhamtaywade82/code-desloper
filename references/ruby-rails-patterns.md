# Ruby & Rails — AI Slop Patterns & Idiomatic Fixes

## 1. Service Object Anti-Patterns

### 1.1 Trivial Single-Method Service
**Smell:** `UserRegistrationService` with only a `call` method that delegates to `User.create`.
**Fix:** Collapse into model method or controller flow if no orchestration is needed.
**Safety check:** Ensure no transaction wrapping, no multi-model coordination, no external API calls.

```ruby
# BEFORE (AI slop)
class UserRegistrationService
  def self.call(params)
    User.create(params)
  end
end

# AFTER (idiomatic)
# In controller:
user = User.create(user_params)
```

### 1.2 Fragmented Orchestration
**Smell:** `OrderProcessor`, `OrderHandler`, `OrderManager` each doing one step of a single logical process.
**Fix:** Merge into a single Service Object (PORO) that handles the transaction and sequence explicitly.
**Safety check:** Verify each step's side effects and ensure proper rollback behavior within a transaction.

### 1.3 Fake Inheritance Chain
**Smell:** `BaseService` → `ApplicationService` → `UserService` with no actual polymorphism or shared logic.
**Fix:** Delete the chain. Use Plain Old Ruby Objects (POROs) and modules for shared concerns.

## 2. Controller & Routing Anti-Patterns

### 2.1 The "God" Controller (Custom Actions)
**Smell:** Controllers with many custom actions like `publish`, `unpublish`, `archive`, `feature`.
**Fix:** Follow "Boring REST." Create new resources and controllers (e.g., `PublishedPostsController`, `ArchivesController`).
**Safety check:** Ensure routing remains clean and follows standard Rails conventions.

### 2.2 Repeated Param Sanitization
**Smell:** `params[:foo].to_s.strip` repeated across multiple controllers.
**Fix:** Use Strong Parameters effectively or move to a Form Object for complex multi-model inputs.

### 2.3 Implicit Side Effects in Callbacks
**Smell:** Using `after_save` or `after_commit` to send emails, sync to external APIs, or trigger heavy background jobs.
**Fix:** Move these side effects to a Service Object or an explicit workflow step. Callbacks should be reserved for data integrity and internal state consistency.

## 3. Model & Query Anti-Patterns

### 3.1 Fat Model Syndrome
**Smell:** 1000+ line models containing business logic, query logic, and formatting helpers.
**Fix:** 
- Move query logic to **Query Objects**.
- Move business orchestration to **Service Objects**.
- Move presentation logic to **ViewComponents** or **Decorators**.
- Move complex multi-model validation to **Form Objects**.

### 3.2 Unnecessary Concerns
**Smell:** A `Concern` used in only one model, or one that is just a dumping ground for unrelated methods.
**Fix:** Inline back into the model until reuse is actually required across ≥2 models.

### 3.3 Scope vs. Service Confusion
**Smell:** Service object that only builds a `where` chain.
**Fix:** Convert to a model `scope`.

```ruby
# BEFORE
class RecentPostsService
  def self.call(user)
    Post.where(user: user).where("created_at > ?", 1.week.ago).order(created_at: :desc)
  end
end

# AFTER
# In Post model:
scope :recent, -> { where("created_at > ?", 1.week.ago).order(created_at: :desc) }
# In controller:
user.posts.recent
```

### 3.4 The N+1 Performance Killer
**Smell:** Iterating over a collection and calling an association method on each item without `includes`.
**Fix:** Use `includes`, `preload`, or `eager_load`. Enable `strict_loading` in development to catch these early.

## 4. Modern Rails 8.0+ Best Practices

### 4.1 Redis-less Architecture
**Smell:** Defaulting to Redis for every background job or cache.
**Fix:** Use **Solid Queue**, **Solid Cache**, and **Solid Cable** to reduce infrastructure complexity.

### 4.2 Built-in Authentication
**Smell:** Pulling in `Devise` for a simple app with standard auth needs.
**Fix:** Use the Rails 8 `rails generate authentication` command for a lightweight, built-in solution.

### 4.3 Hotwire over SPAs
**Smell:** Reaching for React/Vue for a feature that can be handled by **Turbo** and **Stimulus**.
**Fix:** Use Hotwire to keep logic in the monolith and maintain "The Rails Way."

## 5. Naming & Syntax Noise

### 5.1 Verb-Inflation Cluster
**Smell:** `do_process`, `execute_action`, `perform_task` for the same concept.
**Fix:** Standardize: `call` for services, `handle` for events, `process` for pipelines.

### 5.2 Enterprise Suffixes
**Smell:** `EmailManager`, `PaymentProcessor`, `NotificationCoordinator` for simple classes.
**Fix:** Use specific, action-oriented names: `EmailSender`, `PaymentCapture`, `NotificationDispatcher`.

### 5.3 Explicit Return
**Smell:** Explicit `return` at the end of every Ruby method.
**Fix:** Rely on implicit returns; use explicit `return` only for early exits (Guard Clauses).
