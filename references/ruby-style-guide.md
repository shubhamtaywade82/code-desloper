# Ruby Style Guide — Deslopper Rules

Source: [rubystyle.guide](https://rubystyle.guide/) / RuboCop

## Auto-Fix (Risk 1) — Apply without asking

### Layout
- Two-space indentation. No hard tabs.
- No trailing whitespace. End file with a newline.
- No semicolons to terminate statements.
- One expression per line.
- 80-character line length (120 max with team agreement).
- Spaces around operators: `sum = 1 + 2`. No space after `!`.
- One blank line between method definitions.
- One blank line around `private`/`protected`.

### Naming
- `snake_case` for methods and variables.
- `CamelCase` for classes and modules.
- `SCREAMING_SNAKE_CASE` for constants.
- Predicate methods end with `?` (`empty?`, not `is_empty`).
- Bang methods end with `!` only when a safe counterpart exists.
- Unused variables prefixed with `_` (`_unused`, `|_k, v|`).
- Files in `snake_case`; one class per file; filename mirrors class name.

### Flow of Control
```ruby
# for → each
for elem in arr { ... }       # BAD
arr.each { |elem| ... }       # GOOD

# if ! → unless
if !condition { ... }          # BAD
unless condition { ... }       # GOOD

# Ternary for simple branches
if cond then a else b end      # BAD
cond ? a : b                   # GOOD

# Modifier form for single-line
if condition
  do_something
end                            # BAD (when it fits on one line)
do_something if condition      # GOOD

# Early return — no else when guard clause works
def process(val)
  if val.nil?
    return nil
  else
    val.upcase
  end
end                            # BAD

def process(val)
  return nil if val.nil?
  val.upcase
end                            # GOOD
```

### Methods
```ruby
# Explicit return at end — unnecessary
def full_name
  return "#{first} #{last}"   # BAD — return is implicit
end

def full_name
  "#{first} #{last}"          # GOOD
end

# Explicit self — unnecessary except for writers
def display_name
  self.name.upcase             # BAD — self not needed
end

def display_name
  name.upcase                  # GOOD
end

# Parentheses — omit for zero-param def; use for params
def greet; end                 # GOOD — no parens for zero params
def greet(name); end           # GOOD — parens for params

# keyword args for optional / boolean params
def create(user, send_email, options = {})  # BAD
def create(user, send_email: false)         # GOOD
```

### Strings and Collections
```ruby
# Prefer interpolation with double-quotes
name = 'World'
"Hello #{name}"               # GOOD — interpolation
'Hello ' + name               # BAD — concatenation

# Single-quotes when no interpolation
msg = 'no interpolation'      # GOOD
msg = "no interpolation"      # BAD (minor)

# Symbol arrays
%i[foo bar baz]               # GOOD
[:foo, :bar, :baz]            # BAD — verbose

# Hash key style
{ name: 'Alice', age: 30 }   # GOOD — symbol keys
{ :name => 'Alice' }          # BAD — rocket syntax for symbol keys

# Prefer map/select/find over collect/find_all/detect
arr.map { |x| x * 2 }        # GOOD
arr.collect { |x| x * 2 }    # BAD — non-idiomatic alias

# any?/none? over count
items.any?                    # GOOD
items.count > 0               # BAD

# Hash lookup
hash.key?(:foo)               # GOOD
hash.has_key?(:foo)           # BAD — deprecated alias

# fetch for required keys
config.fetch(:api_key)        # GOOD — raises on missing
config[:api_key]              # BAD — silently returns nil
```

### Classes and Modules
```ruby
# Class structure order (always follow this)
class MyClass
  extend SomeModule
  include AnotherModule
  prepend ThirdModule

  CONSTANT = 42

  attr_reader :name
  attr_accessor :status

  enum :type, { ... }

  belongs_to :user         # AR associations
  has_many :items

  validates :name, presence: true

  before_save :normalize

  scope :active, -> { where(active: true) }

  def initialize(name)
    @name = name
  end

  # Public methods
  def process; end

  protected

  def validate_something; end

  private

  def internal_helper; end
end

# No class variables
@@count = 0                  # BAD — shared across subclasses
@count = 0                   # GOOD — class instance variable

# One mixin per line
include Foo, Bar             # BAD
include Foo                  # GOOD
include Bar                  # GOOD

# Modules for namespaces of class methods
class Utils
  def self.format(str); end  # BAD — use module
end

module Utils
  module_function
  def format(str); end       # GOOD
end

# Struct for simple value holders
User = Struct.new(:name, :email)    # GOOD
User = Data.define(:name, :email)   # GOOD (Ruby 3.2+)
```

### Exceptions
```ruby
# raise over fail
fail 'error'                  # BAD
raise 'error'                 # GOOD

# Two-arg form
raise RuntimeError, 'message' # GOOD
raise 'message'               # OK for RuntimeError shorthand

# Don't rescue Exception
rescue Exception => e          # BAD — catches signals
rescue StandardError => e      # GOOD

# Specific exceptions first
rescue ActiveRecord::RecordNotFound => e  # GOOD (specific)
rescue StandardError => e                  # GOOD (general after)

# Don't suppress
rescue StandardError          # BAD — no handler
rescue StandardError => e     # GOOD — log or re-raise
  Rails.logger.error(e.message)
  raise
```

---

## Flag and Ask (Risk 2–3)

### Method Length
```ruby
# Methods > 10 LOC — extract
def process_order
  # 25 lines of mixed concerns
end

# Fix: extract
def process_order
  validate_order
  charge_payment
  send_confirmation
end
```

### Class Size (> 50 LOC or SRP violation)
Identify the multiple responsibilities and extract classes.

### Long Parameter List (> 3 positional params)
```ruby
# BAD
def create(name, email, role, plan, trial)

# GOOD
def create(name:, email:, role: :user, plan: :basic, trial: false)
# or: introduce a Parameter Object
```

### Nested Blocks (> 2 levels)
```ruby
# BAD
items.each do |item|
  item.variants.each do |v|
    v.prices.each do |p|
      process(p)
    end
  end
end

# GOOD — extract inner block
def process_prices(variant)
  variant.prices.each { |p| process(p) }
end
items.each { |i| i.variants.each { |v| process_prices(v) } }
```

### `and`/`or` in Conditions
```ruby
if a and b    # BAD — low precedence, confusing
if a && b     # GOOD

# and/or ARE ok for control flow only
save or raise  # OK — convention for rare control flow use
```

---

## YARD Documentation

See [yard-documentation.md](yard-documentation.md) for full YARD tag reference and patterns.

### When to Add YARD Docs (Deslopper Rule)
- **Add** for all public API methods in `lib/`, service objects, and value objects.
- **Add** for methods with non-obvious params, return types, or side effects.
- **Remove** YARD comments that only restate the method name (`# Returns name` for `def name`).
- **Keep** all existing YARD docs unless they are actively misleading.
- **Update** stale YARD docs when the method signature changes.

### Minimal Correct YARD
```ruby
# @param user [User] the authenticated user
# @param options [Hash] request options
# @option options [Boolean] :notify send notification (default: false)
# @return [Order] the created order
# @raise [ActiveRecord::RecordInvalid] if validation fails
def create_order(user, options = {})
  ...
end
```

### Common YARD Mistakes to Fix
```ruby
# BAD — restates method name, adds no value
# Returns the user's name.
def name = @name

# BAD — wrong type in @param
# @param id [String]  (but it's an Integer)
def find(id)

# BAD — @return on void method
# @return [void]  (redundant; omit for void methods)
def update_cache

# GOOD — non-obvious return
# @return [Array<Hash>] list of { id:, name:, score: } hashes sorted by score desc
def leaderboard

# GOOD — documents side effect
# @note Enqueues a background job. Does not send email synchronously.
# @return [Boolean] true if job was enqueued
def send_notification
```
