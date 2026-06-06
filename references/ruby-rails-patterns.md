# Ruby / Rails — AI Slop Patterns, Best Practices & Idiomatic Fixes

## SERVICE OBJECTS

### 1. Trivial Single-Method Service → Inline It
**Smell:** `call` delegates to a single AR method with no orchestration.
**Fix:** Move to model method or controller flow.
**Safety:** No transaction, no multi-model coordination, no external call.

```ruby
# BEFORE (AI slop)
class UserRegistrationService
  def self.call(params)
    User.create(params)
  end
end

# AFTER
user = User.create(user_params)  # in controller
```

### 2. Fragmented Orchestration → Merge into One Transaction
**Smell:** `Processor`, `Handler`, `Manager` each doing one step of the same workflow.
**Fix:** One transaction object with explicit steps.
**Safety:** Verify each step's side effects and rollback behavior.

```ruby
# BEFORE
OrderProcessor.new(order).validate
OrderHandler.new(order).charge
OrderManager.new(order).notify

# AFTER
OrderCheckout.new(order).call  # single transaction, explicit steps inside
```

### 3. Fake Inheritance Chain → Delete It
**Smell:** `BaseService → ApplicationService → UserService` with no polymorphism.
**Fix:** Delete the chain. Use modules for shared behavior.
**Safety:** Check `is_a?(BaseService)` and `super` calls.

```ruby
# BEFORE
class BaseService; end
class ApplicationService < BaseService; end
class UserService < ApplicationService
  def call = User.create(params)
end

# AFTER — module for shared behavior only if truly shared
module Callable
  def self.included(base)
    base.extend(ClassMethods)
  end
  module ClassMethods
    def call(*args, **kwargs) = new(*args, **kwargs).call
  end
end
```

### 4. Service That Only Builds a Query → Model Scope
**Smell:** Service returns only an AR relation with `where` chain.
**Fix:** Named model scope.
**Safety:** Check if service adds pagination, auth, or other non-query logic.

```ruby
# BEFORE
class RecentPostsService
  def self.call(user)
    Post.where(user: user).where("created_at > ?", 1.week.ago).order(created_at: :desc)
  end
end

# AFTER — in Post model
scope :recent, -> { where("created_at > ?", 1.week.ago).order(created_at: :desc) }
# Usage: user.posts.recent
```

### 5. Enterprise Suffix Abuse → Rename to Intent
**Smell:** `EmailManager`, `OrderCoordinator`, `UserHandler` for trivial work.
**Fix:** Rename to what it does: `EmailSender`, `PaymentCapture`, `ReportGenerator`.
**Safety:** Check for constant references in strings and metaprogramming.

---

## CONTROLLERS

### 6. Direct AR Load Without Ownership Scoping (IDOR)
**Smell:** Loads record by ID without scoping to current user.
**Fix:** Scope to `current_user.association`.

```ruby
# BEFORE — IDOR vulnerability
def show
  @post = Post.find(params[:id])
  return head :forbidden unless @post.user == current_user
end

# AFTER
def show
  @post = current_user.posts.find(params[:id])  # raises RecordNotFound if not owned
end
```

### 7. Repeated Record Loading → Before Action
**Smell:** Same `find` call in multiple actions.
**Fix:** `before_action`.

```ruby
# BEFORE
def show  = @post = current_user.posts.find(params[:id])
def edit  = @post = current_user.posts.find(params[:id])
def update = @post = current_user.posts.find(params[:id])

# AFTER
before_action :set_post, only: [:show, :edit, :update, :destroy]
private
def set_post = @post = current_user.posts.find(params[:id])
```

### 8. Business Logic in Action → Service or Model
**Smell:** Controller action has > 1 meaningful method call plus conditionals.
**Fix:** Delegate to a service object.

```ruby
# BEFORE
def create
  @order = Order.new(order_params)
  @order.user = current_user
  @order.calculate_total
  if @order.valid? && @order.payment_method.valid?
    @order.save
    OrderMailer.confirmation(@order).deliver_later
    redirect_to @order
  else
    render :new
  end
end

# AFTER
def create
  result = Orders::Create.call(order_params, user: current_user)
  result.success? ? redirect_to(result.order) : render(:new, locals: { order: result.order })
end
```

### 9. Instance Variable in Partial → Pass as Local
**Smell:** Partial implicitly depends on controller `@variable`.
**Fix:** Pass as local.

```ruby
# BEFORE (in view)
render 'post_summary'
# BEFORE (in partial) — _post_summary.html.erb
<%= @post.title %>

# AFTER (in view)
render 'post_summary', post: @post
# AFTER (in partial)
<%= post.title %>
```

### 10. Controller Params Mutation → Don't Touch Params
**Smell:** `params[:user][:role] = 'guest'` — mutating the params hash.
**Fix:** Use `merge` in strong params.

```ruby
# BEFORE
params[:user][:role] = 'guest'
User.create(params[:user])

# AFTER
def user_params
  params.require(:user).permit(:name, :email).merge(role: 'guest')
end
```

---

## MODELS

### 11. `after_save` for Side Effects → `after_commit`
**Smell:** Email, job, or cache bust inside `after_save`.
**Fix:** `after_commit` — fires only when transaction actually commits.

```ruby
# BEFORE — email fires even if outer transaction rolls back
after_save :send_confirmation_email

# AFTER
after_commit :send_confirmation_email, on: :create
```

### 12. `default_scope` → Named Scopes
**Smell:** `default_scope { where(active: true) }`.
**Fix:** Explicit named scope. `default_scope` applies to ALL queries including `update_all`, `delete_all`, joins.

```ruby
# BEFORE (dangerous)
default_scope { where(active: true) }

# AFTER
scope :active, -> { where(active: true) }
```

### 13. Law of Demeter Violation → Delegate
**Smell:** `@invoice.user.address.city` — train wreck navigation.
**Fix:** `delegate` on the model.

```ruby
# BEFORE
@invoice.user.address.city  # LoD violation

# AFTER — in Invoice model
delegate :city, to: :user, prefix: :user, allow_nil: true
# Usage: @invoice.user_city
```

### 14. Unnecessary Concern → Inline
**Smell:** Concern included in exactly one model.
**Fix:** Inline back into the model.
**Safety:** `grep -r "include MyConcern"` across the repo.

### 15. Array Enum → Hash Enum
**Smell:** `enum :status, %i[pending active cancelled]` — order-dependent.
**Fix:** Hash syntax.

```ruby
# BEFORE — inserting before 'active' shifts all integer values
enum :status, %i[pending active cancelled]

# AFTER — explicit, stable
enum :status, { pending: 0, active: 1, cancelled: 2 }
```

### 16. `has_and_belongs_to_many` → `has_many :through`
**Smell:** HABTM — no join model, no callbacks, no extra attributes.
**Fix:** `has_many :through`.

```ruby
# BEFORE
has_and_belongs_to_many :groups

# AFTER
has_many :memberships
has_many :groups, through: :memberships
```

### 17. Missing `dependent:` → Always Set It
**Smell:** `has_many :orders` without `dependent:`.
**Fix:** Choose `dependent: :destroy`, `:nullify`, or `:restrict_with_error`.

### 18. Duplicated Validations → Shared Concern (Only If Complex)
**Smell:** `validates :email, presence: true` copied across `User` and `Admin`.
**Fix:** Simple validations can duplicate. Extract concern only if logic is complex.
**Safety:** Ensure `if:`, `unless:`, and error messages match exactly.

### 19. Model Structure Ordering — Consistent Convention
```ruby
class Order < ApplicationRecord
  # 1. Constants
  STATUSES = %w[pending active cancelled].freeze

  # 2. attr_* macros
  attr_accessor :payment_token

  # 3. Enums
  enum :status, { pending: 0, active: 1, cancelled: 2 }

  # 4. Associations (belongs_to before has_*)
  belongs_to :user
  has_many :line_items, dependent: :destroy

  # 5. Validations
  validates :status, presence: true

  # 6. Callbacks (in execution order)
  before_validation :normalize_attributes
  after_commit :broadcast_change, on: [:create, :update]

  # 7. Scopes
  scope :recent, -> { order(created_at: :desc) }

  # 8. Public methods
  def total = line_items.sum(&:amount)

  private

  # 9. Private methods
  def normalize_attributes
    self.status ||= :pending
  end
end
```

---

## ACTIVE RECORD QUERIES

### 20. N+1 Query → Eager Load
**Smell:** Association accessed in loop without preload.
**Fix:** `includes` / `eager_load`.

```ruby
# BEFORE — N+1
@posts.each { |p| p.user.name }

# AFTER
@posts = Post.includes(:user).all
# Complex join filtering:
@posts = Post.eager_load(:user).where(users: { active: true })
```

### 21. Query Method in Instance Method → Filtered Association
**Smell:** `where` inside an instance method called in a loop breaks `includes`.
**Fix:** Filtered association on the model.

```ruby
# BEFORE — N+1; includes(:comments) doesn't help
class Post
  def active_comments = comments.where(soft_deleted: false)
end

# AFTER — includes works
class Post
  has_many :active_comments, -> { where(soft_deleted: false) }, class_name: 'Comment'
end
# Post.includes(:active_comments)  → 2 queries total
```

### 22. `.count` on Loaded Relation → `.size`
**Smell:** `collection.count` after `each` — fires a SQL COUNT unnecessarily.

```ruby
# BEFORE — two queries
@messages.each { |m| render m }
total = @messages.count  # SQL COUNT

# AFTER — uses in-memory length after each loads
@messages.each { |m| render m }
total = @messages.size   # no extra query
```

### 23. `any?` Before `each` → `present?`
**Smell:** Two queries when one would do.

```ruby
# BEFORE — SELECT 1 then SELECT *
if @comments.any?
  @comments.each { |c| render c }

# AFTER — present? loads + caches; each reuses
if @comments.present?
  @comments.each { |c| render c }
```

### 24. SQL String Interpolation → Placeholders
**Smell:** User input interpolated into SQL string.

```ruby
# BEFORE — SQL injection
User.where("email = '#{params[:email]}'")

# AFTER
User.where(email: params[:email])
User.where("email = ?", params[:email])
```

### 25. `User.all.each` → `find_each`

```ruby
# BEFORE — loads all into memory
Person.all.each(&:process)

# AFTER — batches of 1000
Person.find_each(&:process)
Person.find_in_batches(batch_size: 500) { |batch| batch.each(&:process) }
```

### 26. Memoizing `find_by` with `||=` → `defined?`

```ruby
# BEFORE — fails when result is nil
def current_user
  @current_user ||= User.find_by(id: session[:user_id])
end

# AFTER
def current_user
  return @current_user if defined?(@current_user)
  @current_user = User.find_by(id: session[:user_id])
end
```

### 27. Order by `id` → Order by Timestamp

```ruby
# BEFORE — IDs aren't guaranteed sequential
scope :chronological, -> { order(id: :asc) }

# AFTER
scope :chronological, -> { order(created_at: :asc) }
```

### 28. Missing Index on FK / Query Column
**Smell:** `user_id`, `status`, `created_at` used in WHERE/ORDER without index.
**Fix:** Add index in migration.

```ruby
add_index :orders, :user_id
add_index :orders, :status
add_index :orders, [:user_id, :status]
add_index :orders, :created_at
```

---

## MIGRATIONS

### 29. Seed Data in Migration → `db/seeds.rb`

```ruby
# BEFORE — breaks on db:schema:load
class AddDefaultRoles < ActiveRecord::Migration[7.0]
  def up
    Role.create!(name: 'admin')
  end
end

# AFTER — db/seeds.rb
Role.find_or_create_by!(name: 'admin')
```

### 30. Bare App Model in Migration → Migration Model Class

```ruby
# BEFORE — breaks if User changes
def up
  User.where(old_status: 'inactive').update_all(status: 'archived')
end

# AFTER
class MigrationUser < ActiveRecord::Base
  self.table_name = :users
end
def up
  MigrationUser.where(old_status: 'inactive').update_all(status: 'archived')
end
```

### 31. Multiple Column Changes → `bulk: true`

```ruby
# BEFORE — each add_column is a separate ALTER TABLE (lock per column)
change_table :users do |t|
  t.string :phone
  t.string :country
end

# AFTER — single ALTER TABLE
change_table :users, bulk: true do |t|
  t.string :phone
  t.string :country
end
```

---

## NAMING NOISE

### 32. Verb-Inflation Cluster → Standardize on One Verb
**Smell:** `do_process`, `execute_action`, `perform_task`, `run_operation` for same concept.
**Fix:** One verb per concept: `call` for services, `handle` for events, `process` for pipelines.

### 33. Meaningless Variable Names (Reek: UncommunicativeVariableName)
**Smell:** `x`, `tmp`, `data`, `obj`, `result` with no domain meaning.
**Fix:** Use domain terms: `invoice`, `payment_record`, `parsed_response`.

---

## SECURITY

### 34. `rescue Exception` → `rescue StandardError`

```ruby
# BEFORE — swallows Ctrl+C, SIGTERM, NoMemoryError
rescue Exception => e

# AFTER
rescue StandardError => e
# Better: rescue specific exceptions first
rescue ActiveRecord::RecordNotFound, ArgumentError => e
```

### 35. Silent `save` → `save!` or Check Return Value

```ruby
# BEFORE — silent failure
@order.save

# AFTER
@order.save!  # raises ActiveRecord::RecordInvalid
# or
unless @order.save
  Rails.logger.error(@order.errors.full_messages)
  raise OrderSaveError
end
```

### 36. `Time.now` → `Time.current`

```ruby
Time.now              # Bad — system timezone
Time.parse(str)       # Bad — system timezone
Time.current          # Good — respects Rails time zone config
Time.zone.now         # Good
Time.zone.parse(str)  # Good
```

---

## TIMEOUTS

### 37. HTTP Client Without Timeout

```ruby
# BEFORE — hangs indefinitely
Faraday.new(url)
Net::HTTP.get(url)

# AFTER
Faraday.new(url, request: { open_timeout: 2, timeout: 5 })
Net::HTTP.start(host, port, open_timeout: 2, read_timeout: 5) { |http| ... }
```

### 38. Redis Without Timeout

```ruby
# BEFORE
Redis.new(url: ENV['REDIS_URL'])

# AFTER
Redis.new(url: ENV['REDIS_URL'], connect_timeout: 1, timeout: 1)
```

### 39. `after_save` Email / Job → Background + `after_commit`

```ruby
# BEFORE — fires inside transaction, blocks request thread
after_save :send_email

# AFTER — async, only after commit
after_commit :enqueue_email_job, on: :create

def enqueue_email_job
  ConfirmationMailer.with(user: self).deliver_later
end
```

---

## CLEAN RUBY GUIDELINES
For comprehensive clean code guidelines on naming conventions, classes, logic, method design, and refactoring/TDD in Ruby, refer to:
- [Clean Ruby Reference Guide](Clean%20Ruby.md)

