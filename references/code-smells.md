# Code Smells — Full Taxonomy with Ruby & TypeScript Examples

Sources: Fowler's "Refactoring", Reek gem, RubyCritic, SOLID principles

## The Five Categories

### 1. Bloaters — Code Grown Too Large

#### Long Method (> 10 LOC)
Extract methods until each does one thing with one level of abstraction.

```ruby
# SMELL
def process_order(order)
  # validate
  return false unless order.items.any?
  return false unless order.customer.present?
  # calculate
  total = order.items.sum { |i| i.price * i.quantity }
  total -= order.discount if order.discount
  # charge
  charge = StripeService.charge(order.customer.stripe_id, total)
  return false unless charge.success?
  # notify
  OrderMailer.confirmation(order).deliver_later
  true
end

# REFACTORED
def process_order(order)
  return false unless order_valid?(order)
  total = calculate_total(order)
  return false unless charge_customer(order.customer, total)
  notify_customer(order)
  true
end
```

#### Large Class (> 50 LOC or multiple responsibilities)

```ruby
# SMELL — UserAccount does auth, billing, preferences, notifications
class UserAccount
  def login; end
  def logout; end
  def reset_password; end
  def set_plan; end
  def charge_card; end
  def set_theme; end
  def send_welcome_email; end
end

# REFACTORED — separate concerns
class User; end              # data + core behavior
class AuthService; end       # login/logout/reset
class BillingService; end    # plans + charges
class NotificationService; end
```

#### Long Parameter List (> 3 positional params)

```ruby
# SMELL
def create_order(user, item, quantity, discount, notify, metadata)

# REFACTORED — keyword args or Parameter Object
def create_order(user:, item:, quantity:, discount: 0, notify: true)
# or
OrderRequest = Data.define(:user, :item, :quantity, :discount, :notify)
def create_order(request)
```

#### Data Clumps (same group of variables always together)

```ruby
# SMELL — city, state, zip always travel together
def ship(user, city, state, zip, item)

# REFACTORED — Address value object
Address = Data.define(:city, :state, :zip)
def ship(user, address, item)
```

#### Primitive Obsession (raw primitives for domain concepts)

```ruby
# SMELL — money as float, email as string, id as integer
def create_order(user_id, amount, currency, email)

# REFACTORED — value objects
class Money
  def initialize(amount, currency)
    raise ArgumentError if amount.negative?
    @amount, @currency = amount, currency.upcase.freeze
  end
end

class Email
  def initialize(value)
    raise ArgumentError unless value.match?(/\A[^@]+@[^@]+\.[^@]+\z/)
    @value = value.downcase.freeze
  end
end
```

---

### 2. OO Abusers — Misuse of OO Principles

#### Switch on Type (if/elsif checking `type` or `class`)

```ruby
# SMELL — must modify when adding new types
def calculate_area(shape)
  case shape.type
  when :circle    then Math::PI * shape.radius ** 2
  when :rectangle then shape.width * shape.height
  when :triangle  then 0.5 * shape.base * shape.height
  end
end

# REFACTORED — polymorphism
class Circle
  def area = Math::PI * radius ** 2
end
class Rectangle
  def area = width * height
end
# Adding Triangle: just add a new class — don't touch existing code (OCP)
```

#### Refused Bequest (subclass doesn't use parent methods)

```ruby
# SMELL — AdminUser inherits from User but doesn't use auth methods
class User
  def authenticate(password); end
  def update_profile(attrs); end
end
class AdminUser < User
  def authenticate(password) = raise NotImplementedError  # refuses bequest
end

# REFACTORED — composition over inheritance
class AdminUser
  def initialize(user) = @user = user
  def access_admin_panel; end
end
```

#### Parallel Inheritance Hierarchies

```ruby
# SMELL — every time you add XxxShape you must also add XxxShapeRenderer
class CircleShape; end
class CircleShapeRenderer; end
class RectangleShape; end
class RectangleShapeRenderer; end

# REFACTORED — merge via Strategy pattern
class Shape
  def initialize(renderer:) = @renderer = renderer
  def render = @renderer.render(self)
end
```

---

### 3. Change Preventers — Makes Change Hard

#### Divergent Change (one class changed for many reasons = SRP violation)

```ruby
# SMELL — Order changes when payment logic changes AND when email logic changes
class Order
  def charge_card; end     # payment concern
  def send_email; end      # notification concern
  def calculate_tax; end   # pricing concern
end

# REFACTORED — one class, one reason to change
class Order; end
class PaymentService; end
class OrderMailer; end
class TaxCalculator; end
```

#### Shotgun Surgery (one change touches many files)

Symptom: Adding a new payment provider requires editing `PaymentService`, `InvoiceService`,
`ReceiptMailer`, `WebhookController`, and `AdminReportsController`.

Fix: Move all payment provider logic into one place. Introduce an abstraction boundary.

#### Feature Envy (method uses another class's data more than its own)

```ruby
# SMELL — Order.calculate_shipping uses Customer internals extensively
class Order
  def calculate_shipping(customer)
    if customer.country == 'US'
      customer.state == 'CA' ? 10 : 15
    else
      25
    end
  end
end

# REFACTORED — move method to Customer (it belongs there)
class Customer
  def shipping_cost
    return 10 if country == 'US' && state == 'CA'
    return 15 if country == 'US'
    25
  end
end

class Order
  def calculate_shipping = customer.shipping_cost
end
```

---

### 4. Dispensables — Code That Should Not Exist

#### Duplicate Code — Extract Method / Shared Module

```ruby
# SMELL — same normalization in User and Admin
class User
  def normalize_email = self.email = email.downcase.strip
end
class Admin
  def normalize_email = self.email = email.downcase.strip
end

# REFACTORED
module NormalizesEmail
  def normalize_email = self.email = email.downcase.strip
end
class User; include NormalizesEmail; end
class Admin; include NormalizesEmail; end
```

#### Dead Code — Delete Unconditionally

```ruby
# SMELL — method has no callers
def legacy_process_order_v1(order)
  # ... 50 lines ...
end

# FIX: Delete. Git history is your backup.
```

#### Speculative Generality (YAGNI violations)

```ruby
# SMELL — methods that exist "just in case"
class PaymentProcessor
  def process; end
  def rollback; end          # never called
  def generate_report; end   # never called
  def schedule_recurring; end # never called
end

# FIX: Delete unused methods. Add when actually needed.
```

#### Comments That Explain Bad Code

```ruby
# SMELL — comment compensates for bad naming
# iterate through each user and check if they've logged in recently
users.each do |u|
  check_recent_activity(u)
end

# FIX: rename so comment is unnecessary
users.each { |user| flag_if_inactive(user) }
```

#### Lazy Class (does almost nothing)

```ruby
# SMELL — one delegating method, no real logic
class UserFinder
  def self.find(id) = User.find(id)
end

# FIX: inline. Use User.find directly.
```

---

### 5. Couplers — Excessive Coupling Between Classes

#### Message Chains / Law of Demeter Violation

```ruby
# SMELL
invoice.user.address.city.upcase

# REFACTORED — use delegate
class Invoice
  delegate :city, to: :user, prefix: :user
end
invoice.user_city.upcase
```

#### Middle Man (class only delegates)

```ruby
# SMELL — MessageService does nothing itself
class MessageService
  def send_email(user, msg) = EmailSender.send(user, msg)
  def send_sms(user, msg)   = SmsSender.send(user, msg)
end

# FIX: inline if there's no real logic; or add orchestration if needed
```

#### Inappropriate Intimacy (classes know each other's internals)

```ruby
# SMELL — Order reaches into Inventory's internal hash
class Order
  def reserve(inventory)
    item_ids.each do |id|
      inventory.stock_levels[id] -= 1   # direct internal access
    end
  end
end

# REFACTORED — Inventory manages its own state
class Inventory
  def reserve(item_ids)
    item_ids.each { |id| decrement_stock(id) }
  end
end

class Order
  def reserve(inventory) = inventory.reserve(item_ids)
end
```

---

## RubyCritic / Reek / Flog Metric Reference

### Reek Checks (auto-detected)

| Reek Check | Description | Fix |
|---|---|---|
| `IrresponsibleModule` | Class/module with no description and cryptic name | Add YARD or rename to intent |
| `TooManyMethods` | > 7 public methods | Extract class |
| `TooManyInstanceVariables` | > 4 ivars | Extract value object |
| `TooLongMethod` | > 25 lines | Extract methods |
| `FeatureEnvy` | Uses another object's data > own | Move method |
| `UncommunicativeVariableName` | `x`, `tmp`, `data` | Rename to domain term |
| `DuplicateMethodCall` | Same call twice without memoization | Extract to local var |
| `NestedIterators` | Blocks inside blocks | Extract inner block to method |
| `LongYieldList` | Yield with 3+ args | Parameter object |
| `UtilityFunction` | Method doesn't use instance state | Make module_function or move |
| `DataClump` | Same 3+ params across methods | Extract value object |
| `ManualDispatch` | `respond_to?` + `send` | Polymorphism |
| `SubclassedFromCoreClass` | `class MyString < String` | Use delegation |
| `TooManyStatements` | Method body > 5 statements | Extract methods |

### Flog (Complexity) Scores

| Score | Meaning | Action |
|---|---|---|
| < 10 | Simple | OK |
| 10–25 | Moderate | Review |
| 25–60 | Complex | Extract methods |
| > 60 | Very complex | Rewrite |

Flog score = ABC metric (Assignments + Branches + Calls). High branching (`if`/`case`/`rescue`) and long chains inflate it.

### RubyCritic Hot Spots

**Hot spot = High Churn × High Complexity**

Files that change frequently AND are complex are the highest priority for refactoring. RubyCritic surfaces these as the top candidates. Ask: "Can I lower complexity here so future changes are safe?"

### Flay (Duplication) Detection

Flay finds structural duplication — code that looks different but has the same AST shape. Fix by extracting the shared structure into a method or module.

---

## TypeScript / React Smells

### God Component

```tsx
// SMELL — one component handles data fetching, display, auth, and routing
const Dashboard = () => {
  const user = useAuth();
  const data = useFetch('/api/dashboard');
  // 200 lines of JSX + logic
};

// REFACTORED — composition
const Dashboard = () => (
  <AuthGuard>
    <DashboardData>
      {(data) => <DashboardView data={data} />}
    </DashboardData>
  </AuthGuard>
);
```

### Prop Drilling (3+ levels, no intermediate use)

```tsx
// SMELL — UserBadge passes user through Dashboard → Panel → Header → Badge
<Dashboard user={user} />
  <Panel user={user} />      // doesn't use user
    <Header user={user} />   // doesn't use user
      <UserBadge user={user} />

// FIX — Context or co-location
const UserContext = createContext<User | null>(null);
// UserBadge: const user = useContext(UserContext)
```

### Premature Abstraction (Custom Hook for One Use)

```tsx
// SMELL — custom hook extracted for a single component
function useOrderFormState() { ... }
// used only once, in OrderForm

// FIX — inline unless reused
const OrderForm = () => {
  const [status, setStatus] = useState('pending');
  // direct state in component
};
```
