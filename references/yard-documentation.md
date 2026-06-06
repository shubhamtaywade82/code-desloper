# YARD Documentation — Deslopper Rules

YARD is the standard Ruby documentation framework. Code Deslopper enforces YARD on public APIs,
removes stale/misleading docs, and rewrites comments that restate the code rather than explain it.

## When to Add YARD

| Scope | Rule |
|---|---|
| `lib/` public methods | Always add YARD |
| Service object `.call` methods | Always add YARD |
| Value objects (Data.define, Struct, POROs) | Always add YARD |
| Model public methods with non-obvious behavior | Add YARD |
| Controller actions | Skip — Rails routes are the docs |
| Private methods | Skip unless the logic is non-obvious |
| Methods where name + types tell the whole story | Skip |

**Key rule:** If removing the YARD comment wouldn't confuse a future reader, don't write it.

---

## Tag Reference

### Core Tags

```ruby
# @param name [Type] description
# @return [Type] description
# @raise [ExceptionClass] when this happens
# @yield [block_param] description of what the block receives
# @yieldreturn [Type] what the block should return
# @note side effect or usage note
# @example
#   MyClass.new.method(arg)  # => result
```

### Type Notation

```ruby
# Single type
# @param user [User]
# @return [String]

# Nilable
# @return [String, nil]
# @param id [Integer, nil]

# Array of type
# @return [Array<Order>]
# @param ids [Array<Integer>]

# Hash with typed keys/values
# @param options [Hash{Symbol => Object}]
# @return [Hash<String, Integer>]

# Union types
# @param value [Integer, Float]
# @return [TrueClass, FalseClass]

# Boolean shorthand (unofficial but common)
# @return [Boolean]

# Void (omit @return for void; add @return [void] only if explicit contract)
```

### Option Hash Documentation

```ruby
# @param options [Hash] request options
# @option options [Boolean] :notify send email notification (default: false)
# @option options [String] :locale locale for notification (default: I18n.locale)
# @option options [Integer] :retry_count max retries (default: 3)
def process(record, options = {})
```

### Block Documentation

```ruby
# @yield [user, index] each user with their position
# @yieldparam user [User] the current user
# @yieldparam index [Integer] zero-based position
# @yieldreturn [String] the transformed display value
# @return [Array<String>] all transformed values
def map_users
  users.each_with_index.map { |u, i| yield u, i }
end
```

---

## Good vs. Bad YARD

### Bad — Restates the Method Name

```ruby
# BAD — adds nothing over the method name itself
# Returns the user's name.
# @return [String] the name
def name = @name

# BAD — describes the obvious
# Creates a new order.
# @param params [Hash] the parameters
# @return [Order] the order
def create_order(params)
```

### Bad — Wrong Types (Stale Docs)

```ruby
# BAD — method returns Order but @return says String
# @return [String] the order
def create_order(params)
  Order.create!(params)
end

# BAD — param is Integer, doc says String
# @param id [String] the user id
def find_user(id)
  User.find(id)
end
```

### Bad — Redundant @return on void methods

```ruby
# BAD — void return documented unnecessarily
# @return [void]
def update_cache
  Rails.cache.write(cache_key, self)
end

# GOOD — omit @return for void; add @note for side effect
# @note Writes to Rails cache. Cache key: "#{model_name}/#{id}".
def update_cache
  Rails.cache.write(cache_key, self)
end
```

### Good — Documents Non-Obvious Behavior

```ruby
# @param user [User] the requesting user; used for authorization scope
# @param filters [Hash] query filters
# @option filters [Symbol] :status one of :pending, :active, :cancelled
# @option filters [Date, nil] :since include records after this date
# @return [ActiveRecord::Relation<Order>] scoped, not yet executed
# @raise [Pundit::NotAuthorizedError] if user cannot view orders
def filtered_orders(user, filters = {})

# @param raw_csv [String] UTF-8 encoded CSV with headers on first row
# @return [Array<Hash{String => String}>] array of row hashes keyed by header
# @raise [CSV::MalformedCSVError] if the CSV is not well-formed
# @note Large files are streamed; this method does NOT load into memory
def parse_csv(raw_csv)

# @note Enqueues a background job. Does NOT send email synchronously.
# @note Safe to call multiple times — idempotent within the same day.
# @return [Boolean] true if job was enqueued, false if already sent today
def send_daily_digest(user)
```

### Good — Service Object Pattern

```ruby
# Processes an order through payment capture, inventory reservation, and confirmation.
#
# @param order [Order] the order to process; must be in :pending status
# @param payment_method [PaymentMethod] a valid, non-expired payment method
# @return [Result] a Result object with #success?, #order, and #errors
# @raise [Order::InvalidStatusError] if order is not in :pending status
# @raise [Stripe::StripeError] on unrecoverable payment failure
#
# @example Successful processing
#   result = Orders::Process.call(order, payment_method)
#   result.success? # => true
#   result.order.status # => "confirmed"
#
# @example Validation failure
#   result = Orders::Process.call(order_with_no_items, payment_method)
#   result.success? # => false
#   result.errors   # => ["Order has no items"]
def self.call(order, payment_method)
```

---

## Deslopper Actions on YARD

### Remove (Risk 1)
- Comments that restate the method name verbatim
- `@return [void]` on methods that are obviously void
- Duplicate inline comments that repeat the YARD tag
- Commented-out code blocks under YARD

```ruby
# REMOVE THIS:
# Gets the user.
# @return [User] the user
def user = @user

# KEEP THIS (non-obvious):
# @return [User, nil] nil when called before authentication completes
def current_user
  session[:user_id] && User.find_by(id: session[:user_id])
end
```

### Update (Risk 2)
- `@param` with wrong type — correct the type
- `@return` that doesn't match actual return — correct it
- `@raise` that lists an exception the method no longer raises — remove the tag
- Docs on a renamed method — update the example

### Add (Risk 2)
- Missing YARD on any public API in `lib/`
- Service `.call` methods with multiple params or complex returns
- Value object constructors with validation behavior
- Methods with surprising side effects (`@note`)

### Leave Alone
- Existing correct YARD on private methods (even if minimal)
- Accurate YARD on generated code (do not touch auto-generated files)
- RDoc-style `# :nodoc:` markers — preserve them

---

## YARD in Context

### Rails Model

```ruby
class Order < ApplicationRecord
  # @!attribute [r] total_cents
  #   @return [Integer] order total in cents, always positive
  attribute :total_cents, :integer

  # Returns the total formatted as a currency string.
  # @param locale [Symbol] currency locale (default: :en)
  # @return [String] e.g. "$12.50"
  def formatted_total(locale = :en)
    Money.new(total_cents, currency).format(locale: locale)
  end

  # Transitions order to :confirmed status and enqueues confirmation email.
  # @note Idempotent — calling twice on a confirmed order is a no-op.
  # @return [Boolean] true if status changed, false if already confirmed
  # @raise [AASM::InvalidTransition] if order is in :cancelled status
  def confirm!
    return false if confirmed?
    update!(status: :confirmed)
    OrderMailer.confirmation(self).deliver_later
    true
  end
end
```

### Service Object

```ruby
module Orders
  # Cancels an order and processes any applicable refund.
  class Cancel
    # @param order [Order] the order to cancel; must be cancellable
    # @param reason [String] cancellation reason for the audit log
    # @param refund [Boolean] whether to attempt a refund (default: true)
    # @return [Result] result with #success?, #order, #refund_amount, #errors
    # @raise [Order::NotCancellableError] if order.can_cancel? is false
    def self.call(order, reason:, refund: true)
      new(order, reason: reason, refund: refund).call
    end
  end
end
```

### Value Object

```ruby
# Represents a monetary amount with currency.
# Immutable. Equality is value-based (same amount and currency).
#
# @example
#   money = Money.new(1000, 'USD')
#   money.format   # => "$10.00"
#   money + Money.new(500, 'USD')  # => Money.new(1500, 'USD')
class Money
  # @param amount_cents [Integer] amount in smallest currency unit (e.g. cents)
  # @param currency [String] ISO 4217 currency code (e.g. "USD", "EUR")
  # @raise [ArgumentError] if amount_cents is negative
  # @raise [ArgumentError] if currency is not a recognized ISO 4217 code
  def initialize(amount_cents, currency)
    raise ArgumentError, "Amount must be non-negative" if amount_cents.negative?
    @amount_cents = amount_cents
    @currency = currency.upcase.freeze
    freeze
  end
end
```
