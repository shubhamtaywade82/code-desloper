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

### 1.4 Tell, Don't Ask (Encapsulation)

**Smell:** Reaching into an object's state to make a decision (`if user.admin? && user.active?`).
**Fix:** Move the decision logic into the object itself.
**Safety check:** Ensure the new method doesn't introduce circular dependencies.

```ruby
# BEFORE
if user.status == 'active' && user.subscription_valid?
  # do something
end

# AFTER
# In User model:
def can_access_content?
  status == 'active' && subscription_valid?
end

# Usage:
if user.can_access_content?
  # do something
end
```

### 1.5 `after_commit` vs `after_save`
**Smell:** Triggering background jobs or cache invalidation in `after_save`.
**Fix:** Use `after_commit` (or `after_create_commit`) to ensure the DB transaction has finished before the job starts. This prevents "RecordNotFound" errors in workers.

### 1.6 Complex Creation Factory Method
**Smell:** Complex object instantiation logic inside a controller or service.
**Fix:** Move to a factory method in the model (e.g., `User.register_with_profile(params)`).

## 2. Controller & Routing Anti-Patterns

### 2.1 The "God" Controller (Custom Actions)
**Smell:** Controllers with many custom actions like `publish`, `unpublish`, `archive`, `feature`.
**Fix:** Follow "Boring REST." Create new resources and controllers (e.g., `PublishedPostsController`, `ArchivesController`).
**Safety check:** Ensure routing remains clean and follows standard Rails conventions.

### 2.2 Needless Deep Nesting
**Smell:** Routes nested more than 2 levels deep (e.g., `resources :users do resources :posts do resources :comments`).
**Fix:** Use shallow nesting. Only the collection needs the parent ID; the member actions can stand alone.

```ruby
# BEFORE
resources :users do
  resources :posts do
    resources :comments
  end
end

# AFTER
resources :users do
  resources :posts, shallow: true do
    resources :comments, shallow: true
  end
end
```

### 2.3 Simplify Render in Controllers
**Smell:** Verbose render syntax like `render :action => "new"` or `render :template => "users/show"`.
**Fix:** Use the simplified syntax: `render :new` or `render "users/show"`.

### 2.4 Repeated Param Sanitization
**Smell:** `params[:foo].to_s.strip` repeated across multiple controllers.
**Fix:** Use Strong Parameters effectively or move to a Form Object for complex multi-model inputs.

### 2.5 Implicit Side Effects in Callbacks
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

### 3.5 Law of Demeter Violation
**Smell:** Reaching through multiple associations (e.g., `@invoice.user.profile.address.city`).
**Fix:** Use `delegate` to provide local access to the required data.
**Safety check:** Ensure the delegated method exists on the target association.

```ruby
# BEFORE
@invoice.user.profile.address.city

# AFTER
# In Invoice model:
delegate :city, to: :user, prefix: true
# Usage:
@invoice.user_city
```

### 3.6 Default Scope Is Evil
**Smell:** Using `default_scope` to order or filter records.
**Fix:** Use explicit named scopes. `default_scope` is difficult to override and often causes unexpected issues in background jobs or migrations.

### 3.7 Check Save Return Value
**Smell:** Calling `.save` without checking the boolean return value, potentially swallowing validation errors.
**Fix:** Use `if @model.save` or call `.save!` to raise an exception on failure.

### 3.8 Use `Time.zone.now`
**Smell:** Using `Time.now` or `Date.today`.
**Fix:** Always use `Time.zone.now` or `Date.current` to ensure the application respects the configured Rails time zone.

### 3.9 Batched Finders for Large Collections
**Smell:** Calling `.all.each` on a table with thousands of records.
**Fix:** Use `find_each` to load records in batches and prevent memory bloat.

### 3.10 Virtual Attributes for Complex Forms
**Smell:** Manually updating multiple attributes or related models in a controller.
**Fix:** Use virtual attributes (accessors) in the model and override the setter to distribute data.

### 3.11 Query Attributes (? Methods)
**Smell:** Checking `if user.role == 'admin'` or `if user.admin_flag == true`.
**Fix:** Use Rails query attributes. Rails automatically provides `?` methods for boolean columns and Enums.

### 3.12 Proper Enum Usage
**Smell:** Hand-rolled state management using strings or integers without Rails Enums.
**Fix:** Use `enum` for state/role fields to get automatic scopes and query methods.

### 3.13 Safe SQL & Constantize
**Smell:** Interpolating user input into SQL strings or calling `constantize` on user-provided strings.
**Fix:** Use parameterized queries and whitelist allowed constants.

```ruby
# BEFORE
User.where("name = '#{params[:name]}'")
params[:model].constantize.find(id)

# AFTER
User.where(name: params[:name])
# Or
User.where("name = ?", params[:name])

# For constantize:
ALLOWED_MODELS = %w[Post Comment].freeze
klass = ALLOWED_MODELS.include?(params[:model]) ? params[:model].constantize : Post
```

## 4. View & Mailer Best Practices

### 4.1 Move Code into Helper or Decorator
**Smell:** Complex logical blocks or data transformations inside `.html.erb` or `.html.slim` files.
**Fix:** Move to a Helper or a Decorator (e.g., Draper) if it involves model-view logic.

### 4.2 Use Render Collection
**Smell:** Looping with `@items.each { |item| render partial: 'item', locals: { item: item } }`.
**Fix:** Use the optimized collection renderer: `render @items`.

### 4.3 Instance Variables vs Local Variables in Partials
**Smell:** Using `@user` inside a partial.
**Fix:** Pass the variable as a local: `render 'user', user: @user`. This makes the partial reusable and independent of the controller's instance variables.

### 4.4 Avoid `time_ago_in_words`
**Smell:** Using `time_ago_in_words(post.created_at)` for lists of 50+ items.
**Fix:** This helper is expensive to compute on the server. Use a client-side JS library (e.g., `timeago.js` or `relative-time-element`) or just format the date normally.

### 4.5 Move Mailer Logic into Mailer
**Smell:** Building complex strings or performing lookups in the controller before passing data to the Mailer.
**Fix:** Move the logic into the Mailer class; the controller should only pass the necessary IDs or simple objects.

### 4.6 Restrict Auto-generated Routes
**Smell:** `resources :users` when only `index` and `show` are used.
**Fix:** Use `only:` or `except:` to limit routes: `resources :users, only: [:index, :show]`.

### 4.7 Remove Empty Helpers
**Smell:** Unused helper files generated by `rails generate` commands.
**Fix:** Delete them to reduce noise and confusion.

## 5. Migration & Infrastructure

### 5.1 Always Add Database Indexes
**Smell:** Tables without indexes on foreign keys or frequently queried columns.
**Fix:** Ensure `add_index :table, :column` is present in migrations.

### 5.2 Isolating Seed Data
**Smell:** Using `seeds.rb` for essential configuration data or using migrations for massive data transformation.
**Fix:** Use `db/seeds.rb` only for development/test data. Use dedicated data migrations or tasks for production data updates.

## 6. Modern Rails 8.0+ Best Practices

### 6.1 Redis-less Architecture
**Smell:** Defaulting to Redis for every background job or cache.
**Fix:** Use **Solid Queue**, **Solid Cache**, and **Solid Cable** to reduce infrastructure complexity.

### 6.2 Built-in Authentication
**Smell:** Pulling in `Devise` for a simple app with standard auth needs.
**Fix:** Use the Rails 8 `rails generate authentication` command for a lightweight, built-in solution.

### 6.3 Hotwire over SPAs
**Smell:** Reaching for React/Vue for a feature that can be handled by **Turbo** and **Stimulus**.
**Fix:** Use Hotwire to keep logic in the monolith and maintain "The Rails Way."

## 7. Naming, Syntax & Error Handling

### 7.1 Frozen String Literals
**Smell:** Missing magic comment at the top of new files.
**Fix:** Always include `# frozen_string_literal: true` to prevent string mutation and improve performance.

### 7.2 Squiggly Heredoc (`<<~`)
**Smell:** Using `<<-` or `"` for multi-line strings that require indentation.
**Fix:** Use `<<~` to auto-strip leading whitespace based on the least-indented line.

### 7.3 Idiomatic Hash Syntax
**Smell:** Using `hash = { :key => value }` for symbol keys.
**Fix:** Use the shorthand `hash = { key: value }`. Use the "rocket" `=>` only for non-symbol keys. Do not mix both in one hash.

### 7.4 `unless` vs `if !`
**Smell:** Using `if !condition` or `unless condition ... else ...`.
**Fix:** Use `unless condition` for simple negative checks. If an `else` is needed, use `if`.

### 7.5 Rescue StandardError, not Exception
**Smell:** `rescue Exception => e`.
**Fix:** Always rescue `StandardError`. Rescuing `Exception` catches system signals like `SignalException` and `NoMemoryError`.

### 7.6 Use `presence` for Blank Checks
**Smell:** `name = params[:name].present? ? params[:name] : 'Default'`.
**Fix:** Use `.presence`: `name = params[:name].presence || 'Default'`.

### 7.7 Ruby Truthiness
**Smell:** AI-generated code often uses `if x == true` or `if x != nil`.
**Fix:** Use `if x`. In Ruby, everything except `false` and `nil` is truthy. Conversely, use `if !x` or `unless x` for falsy checks.

## 8. Code Complexity & Smells (RubyCritic / Reek)

### 8.1 Feature Envy
**Smell:** A method or service that refers to another object's attributes or methods more than its own.
**Fix:** Move the method to the object it is "envious" of.

```ruby
# BEFORE (Feature Envy in a Service)
class OrderTaxCalculator
  def calculate(order)
    order.items.sum { |i| i.price * order.user.tax_rate }
  end
end

# AFTER (Moved to Model)
class Order < ApplicationRecord
  def tax_total
    items.sum { |i| i.price * user.tax_rate }
  end
end
```

### 8.2 Data Clump
**Smell:** Passing the same 3-4 variables together across multiple methods (e.g., `start_date`, `end_date`).
**Fix:** Extract them into a small Value Object or Struct.

### 8.3 Control Parameter (Flag Argument)
**Smell:** A method that uses a boolean flag to decide which logic to execute.
**Fix:** Split into two specific methods or use polymorphism.

### 8.4 Utility Function
**Smell:** A method that doesn't depend on any instance state of the class it lives in.
**Fix:** Move to a module as a singleton method, or move it closer to the data it operates on.

### 8.5 ABC Metric & Flog Complexity
**Smell:** High ABC score (Assignments, Branches, Calls). Typically triggered by long methods with many `if/else` or nested loops.
**Fix:** Use **Extract Method** to break complex logic into small, single-purpose private methods (≤ 5 lines).

## 9. Naming Noise & Verbose Patterns

### 9.1 Verb-Inflation Cluster
**Smell:** `do_process`, `execute_action`, `perform_task` for the same concept.
**Fix:** Standardize: `call` for services, `handle` for events, `process` for pipelines.

### 9.2 Enterprise Suffixes
**Smell:** `EmailManager`, `PaymentProcessor`, `NotificationCoordinator` for simple classes that do trivial work.
**Fix:** Use specific, action-oriented names: `EmailSender`, `PaymentCapture`, `NotificationDispatcher`.

### 9.3 Explicit Return
**Smell:** Explicit `return` at the end of every Ruby method.
**Fix:** Rely on implicit returns; use explicit `return` only for early exits (Guard Clauses).

## 10. Architectural Integrity & Method Design (Clean Ruby)

### 10.1 Consistent Return Types
**Smell:** A method returning a `String` in one branch and `nil` or `false` in another.
**Fix:** Use consistent return types. If returning a collection, return an empty `[]` instead of `nil`. Use the **Null Object Pattern** for optional single objects.

### 10.2 Predicate Methods (`?`)
**Smell:** Methods like `is_admin` or `check_validity`.
**Fix:** Use Ruby's idiomatic `?` suffix: `admin?` or `valid?`. Ensure they only return `true` or `false`.

### 10.3 Bang Methods (`!`)
**Smell:** Randomly using `!` on method names to sound "important."
**Fix:** Use `!` only for methods that modify the receiver in place (e.g., `strip!`) or for "dangerous" versions of methods that raise exceptions on failure (e.g., `save!`).

### 10.4 Composition Over Inheritance
**Smell:** Deep inheritance trees (`Admin < PowerUser < User < BaseUser`).
**Fix:** Use **Composition**. Delegate specific responsibilities to specialized objects. "Has-a" is usually more flexible than "Is-a."

### 10.5 Simple Initialization
**Smell:** `initialize` methods that perform complex logic, API calls, or database writes.
**Fix:** Keep `initialize` strictly for assignment. Move orchestration to a factory method or a `call` method.

### 10.6 Parameter Overload
**Smell:** Methods taking more than 3 positional arguments.
**Fix:** Use **Keyword Arguments** for clarity, or pass an options hash/Struct for complex configurations.

