# RSpec — AI Slop Patterns, Best Practices & Idiomatic Fixes

Sources: [betterspecs.org](https://www.betterspecs.org/), RuboCop RSpec, RSpec documentation, Thoughtbot guides

## Quick Anti-Pattern Checklist

Run this first on any spec file:

- [ ] `let!` on helpers that are not actually used in every example → convert to `let`
- [ ] `before` block > 5 lines → extract helpers or split into nested `context`
- [ ] `allow_any_instance_of` anywhere → sign of missing dependency injection
- [ ] `create` in factories where `build` or `build_stubbed` would do → remove DB hit
- [ ] Multiple `expect(obj.attribute).to eq(...)` in one example → `have_attributes` or `aggregate_failures`
- [ ] `it "works"` / `it "should work"` / `it "is correct"` → write what behaviour is expected
- [ ] `describe "#internal_helper"` on private methods → test via public interface
- [ ] `before(:all)` with any state mutation → `before(:each)`
- [ ] Nested `context` more than 3 levels deep → flatten or extract shared context
- [ ] Identical `let` blocks in 3+ describe/context groups → `shared_context`
- [ ] Identical `it` structures across 3+ groups → `shared_examples`
- [ ] Stubbing the class under test's own methods → testing mocks, not behaviour
- [ ] `stub_const` on production constants to control code flow → design smell
- [ ] No request/integration spec for a non-trivial controller or service → add one
- [ ] Happy-path only, no nil / empty / boundary cases → add edge cases

---

## PATTERN 1 — `let!` Everywhere Instead of `let`

**Risk: 2**
**RuboCop:** `RSpec/LetSetup`

**Smell:** AI defaults to `let!` (eager evaluation) for every helper, causing every example to
pay the setup cost even when the variable is never referenced. For DB-backed factories this
means unnecessary `INSERT` statements on every single example in the group.

`let!` is correct only when a side effect must happen regardless of whether the variable is
referenced (e.g., a record that must exist so a `has_many` association is non-empty).

```ruby
# BEFORE — every example in this group inserts a User row, even specs that only test status
RSpec.describe Order do
  let!(:user)    { create(:user) }
  let!(:product) { create(:product) }
  let!(:order)   { create(:order, user: user, product: product) }

  it "calculates total" do
    expect(order.total).to eq(9.99)
  end

  it "returns pending status by default" do
    expect(Order.new.status).to eq("pending")  # never uses user, product, or order
  end
end

# AFTER — lazy let; records created only for examples that reference them
RSpec.describe Order do
  let(:user)    { create(:user) }
  let(:product) { create(:product) }
  let(:order)   { create(:order, user: user, product: product) }

  it "calculates total" do
    expect(order.total).to eq(9.99)
  end

  it "returns pending status by default" do
    expect(Order.new.status).to eq("pending")  # no DB hit; user/product never evaluated
  end
end
```

**Safety:** Before converting, confirm the side effect (DB record) is not needed by every
example implicitly (e.g., via a `before` that queries the table). If the record must pre-exist
for callbacks or associations to be valid, keep `let!`.

---

## PATTERN 2 — Giant `before` Blocks Doing Too Much Setup

**Risk: 3**
**RuboCop:** `RSpec/BeforeAfterAll`, `RSpec/ExampleLength`

**Smell:** A single `before` block that creates records, stubs external services, sets config
flags, signs in a user, and populates session state is a maintenance trap. When an example
fails it is hard to tell which setup step caused it.

```ruby
# BEFORE — wall of setup that every example inherits regardless of need
RSpec.describe ReportsController do
  before do
    @admin = create(:user, :admin)
    @org   = create(:organization, owner: @admin)
    3.times { create(:report, organization: @org) }
    @deleted_report = create(:report, :deleted, organization: @org)
    sign_in @admin
    allow(FeatureFlags).to receive(:enabled?).and_return(true)
    allow(ReportExporter).to receive(:generate).and_return("pdf_bytes")
    allow(Analytics).to receive(:track)
    Timecop.freeze(Time.zone.parse("2024-01-15"))
  end

  after { Timecop.return }

  it "lists reports" do ... end
  it "excludes deleted" do ... end
end

# AFTER — extract helpers, compose via let, scope setup to context
RSpec.describe ReportsController do
  let(:admin)  { create(:user, :admin) }
  let(:org)    { create(:organization, owner: admin) }
  let(:reports) { create_list(:report, 3, organization: org) }

  before { sign_in admin }

  describe "GET #index" do
    before { reports }  # explicit: this group needs the records

    it "lists active reports" do
      get :index
      expect(assigns(:reports)).to match_array(reports)
    end

    context "with deleted reports" do
      let!(:deleted) { create(:report, :deleted, organization: org) }

      it "excludes deleted reports" do
        get :index
        expect(assigns(:reports)).not_to include(deleted)
      end
    end
  end

  describe "GET #export" do
    before { allow(ReportExporter).to receive(:generate).and_return("pdf_bytes") }

    it "streams a PDF" do
      get :export, params: { id: reports.first.id }
      expect(response.content_type).to eq("application/pdf")
    end
  end
end
```

**Safety:** Splitting setup can surface order dependencies. Run the full suite after each
extraction to confirm no example relies on a side effect you moved.

---

## PATTERN 3 — Over-Mocking / Stubbing the Unit Under Test

**Risk: 4**
**RuboCop:** `RSpec/AnyInstance`, `RSpec/MessageSpies`

**Smell:** Stubbing methods on the object being tested means you are testing your mocks, not
the real code. The spec passes even if the implementation is completely broken. AI often does
this when the system under test touches collaborators it does not know how to instantiate.

```ruby
# BEFORE — OrderProcessor is the SUT; stubbing its own method is circular
RSpec.describe OrderProcessor do
  let(:processor) { described_class.new(order) }

  before do
    allow(processor).to receive(:calculate_tax).and_return(9.99)
    allow(processor).to receive(:apply_discount).and_return(90.0)
  end

  it "processes the order" do
    expect(processor.process).to be_truthy
  end
end

# AFTER — stub only external collaborators; let the SUT's own methods run
RSpec.describe OrderProcessor do
  let(:order)     { build_stubbed(:order, subtotal: 100.0) }
  let(:tax_api)   { instance_double(TaxService, calculate: 9.99) }
  let(:processor) { described_class.new(order, tax_service: tax_api) }

  it "returns a processed result with correct total" do
    result = processor.process
    expect(result.total).to eq(109.99)
  end

  it "delegates tax calculation to the tax service" do
    processor.process
    expect(tax_api).to have_received(:calculate).with(order)
  end
end
```

**Safety:** Over-mocking specs may need to be rewritten from scratch. Verify intent by reading
the `it` description — if the description names a behaviour but the body only exercises mocks,
the spec is almost certainly wrong.

---

## PATTERN 4 — Missing `shared_examples` / `shared_context` for Repeated Setup

**Risk: 2**
**RuboCop:** `RSpec/DuplicateExampleGroupDescription`

**Smell:** Copy-pasted `let` blocks and `it` examples across `describe` groups. When the
shared behaviour changes, every copy must be updated — AI spreads this pattern widely.

```ruby
# BEFORE — identical authorization check copied into every controller spec
RSpec.describe PostsController do
  context "when user is not authenticated" do
    before { sign_out :user }

    it "redirects to login" do
      get :index
      expect(response).to redirect_to(new_user_session_path)
    end
  end
end

RSpec.describe CommentsController do
  context "when user is not authenticated" do
    before { sign_out :user }

    it "redirects to login" do
      get :index
      expect(response).to redirect_to(new_user_session_path)
    end
  end
end

# AFTER — shared examples and shared contexts
# spec/support/shared_examples/requires_authentication.rb
RSpec.shared_examples "requires authentication" do
  context "when user is not authenticated" do
    before { sign_out :user }

    it "redirects to the login page" do
      action.call
      expect(response).to redirect_to(new_user_session_path)
    end
  end
end

RSpec.shared_context "with authenticated user" do
  let(:user) { create(:user) }
  before { sign_in user }
end

# In each controller spec:
RSpec.describe PostsController do
  include_context "with authenticated user"
  it_behaves_like "requires authentication" do
    let(:action) { -> { get :index } }
  end
end

RSpec.describe CommentsController do
  include_context "with authenticated user"
  it_behaves_like "requires authentication" do
    let(:action) { -> { get :index } }
  end
end
```

**Safety:** Shared examples increase indirection. Add a comment naming the file where the
shared example lives. Ensure `shared_examples` files are loaded via `spec/support`.

---

## PATTERN 5 — Testing Implementation Not Behaviour (Private Methods, Internal State)

**Risk: 3**
**RuboCop:** `RSpec/DescribedClass`

**Smell:** Testing private methods directly breaks the spec whenever the implementation
changes, even when behaviour is preserved. It also encourages poor encapsulation — the test
becomes a secondary caller of private code.

```ruby
# BEFORE — spec reaches into private method via send
RSpec.describe PaymentProcessor do
  describe "#normalize_card_number" do
    it "strips spaces and dashes" do
      processor = described_class.new
      result = processor.send(:normalize_card_number, "4111 1111-1111 1111")
      expect(result).to eq("4111111111111111")
    end
  end

  describe "@retry_count" do
    it "starts at zero" do
      processor = described_class.new
      expect(processor.instance_variable_get(:@retry_count)).to eq(0)
    end
  end
end

# AFTER — test the public behaviour that relies on the private logic
RSpec.describe PaymentProcessor do
  let(:gateway) { instance_double(PaymentGateway, charge: true) }
  let(:processor) { described_class.new(gateway: gateway) }

  describe "#charge" do
    it "accepts card numbers with spaces and dashes" do
      expect(processor.charge("4111 1111-1111 1111", amount: 100)).to be_truthy
    end

    it "retries on gateway timeout and eventually succeeds" do
      allow(gateway).to receive(:charge).and_raise(Gateway::Timeout).once
      allow(gateway).to receive(:charge).and_return(true)
      expect(processor.charge("4111111111111111", amount: 100)).to be_truthy
    end
  end
end
```

**Safety:** If the private method is genuinely complex enough to warrant isolated testing,
extract it to a dedicated collaborator class and test that class publicly.

---

## PATTERN 6 — Brittle `subject` Definitions That Couple to Constructor

**Risk: 2**
**RuboCop:** `RSpec/ImplicitSubject`, `RSpec/SubjectDeclaration`

**Smell:** `subject { described_class.new(arg1, arg2, arg3, arg4) }` breaks every example
in the group when the constructor signature changes. AI often generates a literal constructor
call instead of delegating through `let` helpers.

```ruby
# BEFORE — positional args hard-coded; breaks on signature refactor
RSpec.describe InvoiceGenerator do
  subject { described_class.new("monthly", Date.today, true, "USD", nil) }

  it { is_expected.to be_a(InvoiceGenerator) }
  it { is_expected.to respond_to(:generate) }
end

# AFTER — keyword args via let; one place to update
RSpec.describe InvoiceGenerator do
  let(:frequency)   { :monthly }
  let(:issued_on)   { Date.current }
  let(:send_email)  { true }
  let(:currency)    { "USD" }

  subject(:generator) do
    described_class.new(
      frequency: frequency,
      issued_on: issued_on,
      send_email: send_email,
      currency: currency
    )
  end

  it "generates an invoice with the correct currency" do
    expect(generator.generate.currency).to eq("USD")
  end

  context "when currency is EUR" do
    let(:currency) { "EUR" }

    it "generates a EUR invoice" do
      expect(generator.generate.currency).to eq("EUR")
    end
  end
end
```

**Safety:** Named `subject` (e.g., `subject(:generator)`) is always preferred over anonymous
`subject { ... }` because it reads as plain English inside `it` blocks.

---

## PATTERN 7 — Nested `context` Blocks 4+ Levels Deep

**Risk: 3**
**RuboCop:** `RSpec/NestedGroups` (max: 3)

**Smell:** Deep nesting makes the full test description impossible to read at a glance and
causes every example to carry the compounding weight of every parent `before` block. AI
generates this by mirroring nested conditionals in the source code directly.

```ruby
# BEFORE — reading any example requires mentally climbing 5 levels
RSpec.describe Order do
  context "when authenticated" do
    context "when order exists" do
      context "when order belongs to user" do
        context "when order is in pending state" do
          context "when payment method is valid" do
            it "processes the payment" do
              # ...
            end
          end
        end
      end
    end
  end
end

# AFTER — flatten using explicit context labels and shared setup
RSpec.describe Order, "#process_payment" do
  let(:user)  { create(:user) }
  let(:order) { create(:order, :pending, user: user, payment_method: valid_card) }
  let(:valid_card) { build(:payment_method, :visa) }

  before { sign_in user }

  it "processes the payment when all conditions are met" do
    expect(order.process_payment).to be_success
  end

  context "when the payment method is expired" do
    let(:valid_card) { build(:payment_method, :expired) }

    it "returns a failure result" do
      expect(order.process_payment).to be_failure
    end
  end

  context "when the order is already completed" do
    let(:order) { create(:order, :completed, user: user) }

    it "raises InvalidStateError" do
      expect { order.process_payment }.to raise_error(Order::InvalidStateError)
    end
  end
end
```

**Safety:** When collapsing nesting, carry all conditions into the example's `it` description
so the intent is not lost.

---

## PATTERN 8 — `create` When `build` or `build_stubbed` Would Do

**Risk: 2**
**RuboCop:** `FactoryBot/CreateList` (prefers `build_list` for non-DB specs)

**Smell:** `create` hits the database. Unit specs for POROs, service objects, and model
methods that don't touch the DB should use `build` or `build_stubbed`. AI defaults to
`create` everywhere because it "always works".

| Factory method | DB hit | Associations | Use when |
|---|---|---|---|
| `build_stubbed` | None | Stubbed IDs | Pure unit tests; fastest |
| `build` | None | In-memory only | Validations; no persistence needed |
| `create` | Yes | Persisted | Integration, DB queries, callbacks |

```ruby
# BEFORE — unnecessary DB writes for a pure value-object test
RSpec.describe Invoice do
  let(:user)    { create(:user) }
  let(:invoice) { create(:invoice, user: user, amount_cents: 10_000) }

  it "formats the amount as dollars" do
    expect(invoice.formatted_amount).to eq("$100.00")
  end
end

# AFTER — no DB; test runs ~50× faster
RSpec.describe Invoice do
  let(:user)    { build_stubbed(:user) }
  let(:invoice) { build_stubbed(:invoice, user: user, amount_cents: 10_000) }

  it "formats the amount as dollars" do
    expect(invoice.formatted_amount).to eq("$100.00")
  end
end

# create is appropriate when testing a DB-level concern
RSpec.describe Invoice, "scopes" do
  let!(:paid)    { create(:invoice, :paid) }
  let!(:overdue) { create(:invoice, :overdue) }

  it "returns only paid invoices" do
    expect(Invoice.paid).to contain_exactly(paid)
  end
end
```

**Safety:** `build_stubbed` does not run `after_create` callbacks. If the object under test
relies on state set by those callbacks, use `create` or call the callback explicitly.

---

## PATTERN 9 — `expect(obj).to eq(...)` on Every Attribute

**Risk: 1**
**RuboCop:** `RSpec/MultipleExpectations`, `RSpec/HaveAttributes`

**Smell:** Separately asserting every attribute in individual `expect` calls produces verbose
specs where a single failure obscures all others. `have_attributes` and `aggregate_failures`
are the idiomatic fixes.

```ruby
# BEFORE — ten separate assertions; first failure hides the rest
it "builds a complete user from the params" do
  user = UserBuilder.call(valid_params)
  expect(user.first_name).to eq("Jane")
  expect(user.last_name).to eq("Doe")
  expect(user.email).to eq("jane@example.com")
  expect(user.role).to eq("admin")
  expect(user.active).to eq(true)
  expect(user.locale).to eq("en")
end

# AFTER (option A) — have_attributes reads like a contract
it "builds a complete user from the params" do
  expect(UserBuilder.call(valid_params)).to have_attributes(
    first_name: "Jane",
    last_name:  "Doe",
    email:      "jane@example.com",
    role:       "admin",
    active:     true,
    locale:     "en"
  )
end

# AFTER (option B) — aggregate_failures when mixing matcher types
it "builds a complete user from the params", :aggregate_failures do
  user = UserBuilder.call(valid_params)
  expect(user.first_name).to eq("Jane")
  expect(user.email).to match(/@example\.com\z/)
  expect(user.role).to eq("admin")
  expect(user).to be_active
end
```

**Safety:** `have_attributes` calls the public attribute methods — if the attribute is a
method with side effects, it will be called. Use `aggregate_failures` when different matcher
types are needed on the same object.

---

## PATTERN 10 — Missing Request Spec / Integration Coverage

**Risk: 4**
**RuboCop:** (no direct rule; enforce via coverage gates)

**Smell:** AI generates exhaustive unit specs for models and service objects but leaves
controllers completely uncovered. Request specs (preferred over controller specs in Rails 5+)
verify the full stack: routing, middleware, authentication, serialisation, and response codes.

```ruby
# MISSING — no integration test means a routing change or auth regression is invisible

# AFTER — request spec for the full controller flow
RSpec.describe "POST /api/v1/orders", type: :request do
  let(:user) { create(:user) }
  let(:headers) { auth_headers_for(user) }
  let(:valid_params) { { order: { product_id: create(:product).id, quantity: 2 } } }

  context "with valid params" do
    it "creates an order and returns 201" do
      post api_v1_orders_path, params: valid_params, headers: headers
      expect(response).to have_http_status(:created)
      expect(response.parsed_body["status"]).to eq("pending")
    end
  end

  context "with missing product" do
    it "returns 422 with error details" do
      post api_v1_orders_path,
           params: { order: { product_id: nil } },
           headers: headers
      expect(response).to have_http_status(:unprocessable_entity)
      expect(response.parsed_body["errors"]).to include("Product can't be blank")
    end
  end

  context "when unauthenticated" do
    it "returns 401" do
      post api_v1_orders_path, params: valid_params
      expect(response).to have_http_status(:unauthorized)
    end
  end
end
```

**Safety:** Request specs require a running Rails stack. Add `type: :request` or place specs
in `spec/requests/`. Ensure `spec/support/request_helpers.rb` provides auth helpers.

---

## PATTERN 11 — `allow_any_instance_of` — Sign of Bad Dependency Injection

**Risk: 4**
**RuboCop:** `RSpec/AnyInstance`

**Smell:** `allow_any_instance_of(Mailer).to receive(:deliver_now)` is a last resort for
code that instantiates collaborators internally and provides no injection point. It patches
all instances globally, can conflict across threads, and makes the test order-dependent.
It almost always signals a design problem: the SUT constructs its own dependencies.

```ruby
# BEFORE — SUT news up its own mailer with no injection point
class OrderService
  def complete(order)
    order.update!(status: :completed)
    OrderMailer.new(order).deliver_now  # hard dependency
  end
end

RSpec.describe OrderService do
  it "sends a confirmation email" do
    allow_any_instance_of(OrderMailer).to receive(:deliver_now)
    described_class.new.complete(create(:order))
    expect_any_instance_of(OrderMailer).to have_received(:deliver_now)
  end
end

# AFTER — inject the mailer; stub the injected double
class OrderService
  def initialize(mailer: OrderMailer)
    @mailer = mailer
  end

  def complete(order)
    order.update!(status: :completed)
    @mailer.new(order).deliver_now
  end
end

RSpec.describe OrderService do
  let(:mailer_class) { class_double(OrderMailer) }
  let(:mailer)       { instance_double(OrderMailer, deliver_now: true) }
  let(:service)      { described_class.new(mailer: mailer_class) }

  before { allow(mailer_class).to receive(:new).and_return(mailer) }

  it "sends a confirmation email on completion" do
    service.complete(create(:order))
    expect(mailer).to have_received(:deliver_now)
  end
end
```

**Safety:** If refactoring the production code is out of scope, `allow_any_instance_of` is
acceptable as a temporary measure — add a `# TODO: remove after DI refactor` comment.

---

## PATTERN 12 — Hardcoded Fixture Data Instead of FactoryBot Traits

**Risk: 2**
**RuboCop:** `FactoryBot/AttributeDefinedStatically`

**Smell:** AI hard-codes magic strings and integers inline, or creates multiple factories
(`create(:admin_user)`, `create(:suspended_user)`) when traits would express the same intent
more clearly and DRYly.

```ruby
# BEFORE — duplicated factory definitions, magic values sprinkled everywhere
create(:user, role: "admin", active: true, confirmed_at: Time.current)
create(:user, role: "guest", active: false, suspended_at: 1.day.ago)
create(:user, role: "guest", active: true, email: "test+unique@example.com")

# AFTER — traits in the factory definition
# spec/factories/users.rb
FactoryBot.define do
  factory :user do
    sequence(:email) { |n| "user#{n}@example.com" }
    first_name { "Alice" }
    role       { "guest" }
    active     { true }

    trait :admin do
      role { "admin" }
    end

    trait :suspended do
      active       { false }
      suspended_at { 1.day.ago }
    end

    trait :unconfirmed do
      confirmed_at { nil }
    end
  end
end

# In specs — clear, composable, no magic values
let(:admin)     { create(:user, :admin) }
let(:suspended) { create(:user, :suspended) }
let(:pending)   { create(:user, :unconfirmed) }
let(:super_admin) { create(:user, :admin, :unconfirmed) }  # traits compose
```

**Safety:** Check that trait overrides do not conflict. Two traits that set the same attribute
will use the last one listed — document this in the factory with a comment if it matters.

---

## PATTERN 13 — Describing Implementation Not Contract (`describe "#internal_helper"`)

**Risk: 2**
**RuboCop:** `RSpec/DescribeClass`

**Smell:** Using `describe "#method_name"` for private methods, or naming examples after
internal implementation details rather than observable outcomes. The test spec should read
as the class's public contract, not as a mirror of its source code.

```ruby
# BEFORE — describes internal methods and implementation steps
RSpec.describe ReportGenerator do
  describe "#build_sql_query" do ... end
  describe "#serialize_rows_to_csv" do ... end
  describe "#upload_to_s3_bucket" do ... end
end

# AFTER — describes observable outcomes from the public interface
RSpec.describe ReportGenerator do
  describe "#generate" do
    context "when data is present" do
      it "returns a report with CSV content" do
        report = described_class.new(data: sample_data).generate
        expect(report.content_type).to eq("text/csv")
        expect(report.rows.count).to eq(sample_data.size)
      end
    end

    context "when storage upload fails" do
      before { allow(Storage).to receive(:upload).and_raise(Storage::Error) }

      it "raises ReportGenerator::UploadError" do
        expect {
          described_class.new(data: sample_data).generate
        }.to raise_error(ReportGenerator::UploadError)
      end
    end
  end
end
```

**Safety:** `describe ".class_method"` (dot prefix) and `describe "#instance_method"` (hash
prefix) are fine RSpec conventions for *public* methods. The smell is describing private
methods or labelling examples with implementation rather than outcome.

---

## PATTERN 14 — `it "works"` / `it "should work"` — Vague Test Names

**Risk: 1**
**RuboCop:** `RSpec/ExampleWording`

**Smell:** Vague test names produce meaningless failure output. When `it "works"` fails, the
error message gives no indication of what behaviour broke or why it mattered.

```ruby
# BEFORE — tells you nothing when it fails
it "works" do ... end
it "should work" do ... end
it "is correct" do ... end
it "handles it" do ... end
it "processes" do ... end

# AFTER — failure message is self-documenting
it "applies a 10% discount when a SUMMER promo code is used" do ... end
it "raises ArgumentError when quantity is zero" do ... end
it "does not send an email when the user has opted out" do ... end
it "returns an empty array when no records match the filter" do ... end
it "persists the order and enqueues a confirmation job" do ... end
```

**Convention:**
- Do not start with "should" (RuboCop `RSpec/ExampleWording` flags this)
- Use present tense: "returns", "raises", "enqueues", "persists"
- Include the condition in the `context` label, not re-stated in `it`
- Full sentence: `context "when promo code is expired"` + `it "returns an error"`

**Safety:** Rename-only change. Zero behaviour impact. Low risk, high value.

---

## PATTERN 15 — Missing `aggregate_failures` When Checking Multiple Attributes

**Risk: 1**
**RuboCop:** `RSpec/MultipleExpectations`

**Smell:** Without `aggregate_failures`, the first failing `expect` aborts the example. You
see one failure, fix it, re-run, and discover the next. `aggregate_failures` runs all
assertions and reports every failure in one pass.

```ruby
# BEFORE — stops at first failure; masks subsequent problems
it "returns a well-formed API response" do
  result = Api::OrderSerializer.new(order).as_json
  expect(result[:id]).to eq(order.id)
  expect(result[:status]).to eq("pending")       # if this fails, next two are not checked
  expect(result[:total]).to eq("100.00")
  expect(result[:created_at]).to be_present
end

# AFTER (option A) — tag the example
it "returns a well-formed API response", :aggregate_failures do
  result = Api::OrderSerializer.new(order).as_json
  expect(result[:id]).to eq(order.id)
  expect(result[:status]).to eq("pending")
  expect(result[:total]).to eq("100.00")
  expect(result[:created_at]).to be_present
end

# AFTER (option B) — global in spec_helper (recommended for most projects)
# spec/spec_helper.rb
RSpec.configure do |config|
  config.define_derived_metadata do |meta|
    meta[:aggregate_failures] = true
  end
end

# AFTER (option C) — have_attributes for attribute sets
it "returns a well-formed API response" do
  expect(Api::OrderSerializer.new(order).as_json).to include(
    id:         order.id,
    status:     "pending",
    total:      "100.00"
  )
end
```

**Safety:** `aggregate_failures` changes example semantics — a later assertion may reference
state mutated by a failed earlier one. Review carefully when assertions have dependencies.

---

## PATTERN 16 — `before(:all)` / `before(:suite)` for Mutable State

**Risk: 5**
**RuboCop:** `RSpec/BeforeAfterAll`

**Smell:** `before(:all)` runs once per example group, not once per example. Any state it
creates is shared across all examples in the group and is *not* rolled back between examples.
This breaks test isolation, causes order-dependent failures, and is nearly impossible to
debug.

```ruby
# BEFORE — user created once and mutated across examples
RSpec.describe UserDashboard do
  before(:all) do
    @user = create(:user, score: 0)
  end

  it "shows zero score" do
    expect(@user.score).to eq(0)
  end

  it "shows updated score after activity" do
    @user.update!(score: 100)  # mutates shared state
    expect(@user.score).to eq(100)
  end

  it "shows zero score again" do  # fails — @user.score is now 100
    expect(@user.score).to eq(0)
  end
end

# AFTER — each example gets a fresh, isolated record
RSpec.describe UserDashboard do
  let(:user) { create(:user, score: 0) }

  it "shows zero score initially" do
    expect(user.score).to eq(0)
  end

  it "shows updated score after activity" do
    user.update!(score: 100)
    expect(user.score).to eq(100)
  end

  it "shows zero score for a new user" do
    # fresh user from let — score is 0
    expect(user.score).to eq(0)
  end
end
```

**Legitimate use of `before(:all)`:** Read-only setup of truly immutable, expensive fixtures
(e.g., loading a large fixture file once). Never use it for AR records that will be
touched by any example.

**Safety:** Risk 5 — `before(:all)` with mutable AR state has caused production-data-
corruption bugs in CI environments. Always replace. If the setup is genuinely expensive,
use `DatabaseCleaner` with `strategy: :truncation` and `before(:suite)` for *read-only*
seed data only.

---

## PATTERN 17 — Testing Rails Internals (Validating That `save` Calls `validate`)

**Risk: 3**
**RuboCop:** `RSpec/Rails/AvoidSetupHook`

**Smell:** Specs that verify Rails framework behaviour (that `save` invokes `validate`, that
`belongs_to` raises on missing record, that `presence: true` sets an error) are testing
Rails, not your application. They break on Rails upgrades and give zero application insight.

```ruby
# BEFORE — testing that Rails validates (it does; trust it)
RSpec.describe User do
  it "calls validate on save" do
    user = User.new
    expect(user).to receive(:valid?)
    user.save
  end

  it "has presence validation on email" do
    user = User.new
    user.valid?
    expect(user.errors[:email]).to include("can't be blank")
  end
end

# AFTER — test the business rule that the validation enforces
RSpec.describe User do
  it "is invalid without an email" do
    expect(build(:user, email: nil)).not_to be_valid
  end

  it "is invalid when email is not unique" do
    create(:user, email: "taken@example.com")
    expect(build(:user, email: "taken@example.com")).not_to be_valid
  end

  it "is invalid when email format is malformed" do
    expect(build(:user, email: "not-an-email")).not_to be_valid
  end

  it "is valid with all required fields" do
    expect(build(:user)).to be_valid
  end
end
```

**Safety:** If you are specifying a custom validator class (`EmailValidator`, etc.), testing
its logic directly is correct — test the validator's `#validate` method, not Rails glue.

---

## PATTERN 18 — Giant Single `it` Block — Multiple Assertions, No Structure

**Risk: 3**
**RuboCop:** `RSpec/ExampleLength` (default max: 5 lines), `RSpec/MultipleExpectations`

**Smell:** One massive `it` block that sets up state, triggers multiple operations, and asserts
many outcomes is an integration test masquerading as a unit spec. When it fails, the failure
message does not tell you which of the 12 things went wrong.

```ruby
# BEFORE — everything in one block; 30+ lines; multiple concerns
it "handles the full order lifecycle" do
  user = create(:user)
  product = create(:product, price: 100)
  order = create(:order, user: user)
  order.add_item(product, quantity: 2)
  expect(order.total).to eq(200)
  expect(order.status).to eq("pending")
  order.submit!
  expect(order.status).to eq("submitted")
  expect(OrderMailer.deliveries.count).to eq(1)
  order.pay!(amount: 200)
  expect(order.status).to eq("paid")
  expect(order.paid_at).to be_within(1.second).of(Time.current)
  expect(user.reload.total_spent).to eq(200)
end

# AFTER — each behaviour in its own example; shared state via let
RSpec.describe Order, "lifecycle" do
  let(:user)    { create(:user) }
  let(:product) { create(:product, price: 100) }
  let(:order)   { create(:order, user: user) }

  before { order.add_item(product, quantity: 2) }

  describe "#total" do
    it "sums item prices times quantities" do
      expect(order.total).to eq(200)
    end
  end

  describe "#submit!" do
    before { order.submit! }

    it "transitions status to submitted" do
      expect(order.status).to eq("submitted")
    end

    it "sends a confirmation email" do
      expect(OrderMailer.deliveries.count).to eq(1)
    end
  end

  describe "#pay!" do
    before { order.submit!; order.pay!(amount: 200) }

    it "transitions status to paid" do
      expect(order.status).to eq("paid")
    end

    it "records the payment timestamp" do
      expect(order.paid_at).to be_within(1.second).of(Time.current)
    end

    it "updates the user's total spent" do
      expect(user.reload.total_spent).to eq(200)
    end
  end
end
```

**Safety:** Splitting one example into many makes ordering assumptions visible. If example B
relies on side effects from example A, extract those into `before` or `let`. Never rely on
example ordering — RSpec randomises by default.

---

## PATTERN 19 — Missing Edge Cases — Happy Path Only

**Risk: 4**
**RuboCop:** (no direct rule; enforce via mutation testing)

**Smell:** AI writes one `it "returns the correct result"` for the golden path and stops.
Real bugs live at boundaries: nil inputs, empty collections, zero quantities, expired dates,
duplicate submissions, concurrent writes. A spec suite without edge cases gives false
confidence.

```ruby
# BEFORE — only the happy path
RSpec.describe Discount do
  it "applies 10% discount" do
    expect(Discount.apply(100, code: "SAVE10")).to eq(90)
  end
end

# AFTER — happy path + boundaries + errors
RSpec.describe Discount do
  describe ".apply" do
    context "with a valid 10% promo code" do
      it "deducts 10% from the total" do
        expect(described_class.apply(100, code: "SAVE10")).to eq(90)
      end
    end

    context "with a nil amount" do
      it "raises ArgumentError" do
        expect { described_class.apply(nil, code: "SAVE10") }.to raise_error(ArgumentError)
      end
    end

    context "with a zero amount" do
      it "returns zero without error" do
        expect(described_class.apply(0, code: "SAVE10")).to eq(0)
      end
    end

    context "with an expired promo code" do
      let(:expired_code) { create(:promo_code, :expired) }

      it "returns the original amount unchanged" do
        expect(described_class.apply(100, code: expired_code.value)).to eq(100)
      end
    end

    context "with an unknown promo code" do
      it "raises Discount::InvalidCode" do
        expect {
          described_class.apply(100, code: "FAKE")
        }.to raise_error(Discount::InvalidCode)
      end
    end

    context "when the discount would produce a negative total" do
      it "returns zero (floor at zero)" do
        expect(described_class.apply(5, code: "FLAT50")).to eq(0)
      end
    end
  end
end
```

**Edge case checklist to run against every method:**
- [ ] `nil` / missing input
- [ ] Empty string / empty array / empty hash
- [ ] Zero / negative numerics
- [ ] Boundary values (exactly at limit, one above, one below)
- [ ] Duplicate / idempotent calls
- [ ] Expired / inactive records
- [ ] Concurrent access (if the method modifies shared state)
- [ ] Encoding / encoding edge cases for string methods

---

## PATTERN 20 — `stub_const` Overuse / Metaprogramming in Specs

**Risk: 4**
**RuboCop:** `RSpec/StubConst` (via rubocop-rspec custom rules)

**Smell:** `stub_const` patches a constant for the duration of one example. Overuse signals
that the production code hard-codes constants (feature flags, URLs, limits) that should be
injectable configuration. Heavy metaprogramming in specs (`define_method`, `class_eval`,
reopening classes) is always a design smell in the SUT.

```ruby
# BEFORE — test patches the constant because SUT has no injection point
RSpec.describe RateLimiter do
  it "blocks requests above the limit" do
    stub_const("RateLimiter::MAX_REQUESTS", 3)
    limiter = RateLimiter.new("user:1")
    4.times { limiter.increment }
    expect(limiter).to be_blocked
  end
end

# BEFORE — reopening production class in spec (extremely fragile)
RSpec.describe PaymentGateway do
  before do
    PaymentGateway.class_eval do
      def charge(_amount) = { status: "ok" }  # monkeypatching in a spec
    end
  end
end

# AFTER — inject the limit; no constant patching needed
class RateLimiter
  def initialize(key, max_requests: MAX_REQUESTS)
    @key          = key
    @max_requests = max_requests
  end
  # ...
end

RSpec.describe RateLimiter do
  it "blocks requests above the configured limit" do
    limiter = RateLimiter.new("user:1", max_requests: 3)
    4.times { limiter.increment }
    expect(limiter).to be_blocked
  end
end

# AFTER — use instance_double for gateway; no class_eval
RSpec.describe PaymentGateway do
  let(:gateway) { instance_double(PaymentGateway, charge: { status: "ok" }) }

  it "returns ok status" do
    expect(gateway.charge(100)).to include(status: "ok")
  end
end
```

**Legitimate use of `stub_const`:** Testing code that branches on `Rails.env` or a
`FEATURE_FLAGS` constant where refactoring is not yet feasible. Always add a comment
explaining why injection is not possible.

---

## FACTORYBOT BEST PRACTICES

### Traits Over Inheritance

Prefer traits to child factories. Traits compose; child factories form hidden hierarchies.

```ruby
# BAD — child factory inheritance
factory :user do
  name { "Alice" }
  factory :admin_user do
    role { "admin" }
    factory :suspended_admin_user do
      active { false }
    end
  end
end

# GOOD — composable traits
factory :user do
  sequence(:email) { |n| "user#{n}@example.com" }
  name   { "Alice" }
  role   { "guest" }
  active { true }

  trait :admin     { role { "admin" } }
  trait :suspended { active { false }; suspended_at { 1.day.ago } }
  trait :unconfirmed { confirmed_at { nil } }

  # Usage: create(:user, :admin, :suspended)
end
```

### `build_stubbed` as Default

Reach for `build_stubbed` first. Move to `build` if you need validations. Move to `create`
only when you need DB persistence.

```ruby
# Fastest — no DB, stubbed associations
let(:user) { build_stubbed(:user, :admin) }

# Needs validations but not persistence
let(:user) { build(:user, :admin) }

# Must be in DB (scopes, callbacks, associations that query)
let(:user) { create(:user, :admin) }
```

### `create_list` vs `build_list`

```ruby
# DB-backed list — for scope/query specs
let(:orders) { create_list(:order, 5, :pending) }

# In-memory list — for unit specs
let(:orders) { build_stubbed_list(:order, 5, :pending) }

# Avoid: Array.new(5) { create(:order) }  — use create_list
```

### Avoid `association` in Factory When Not Always Needed

```ruby
# BAD — always creates a User, even when caller provides one
factory :post do
  association :user  # extra INSERT every time
  title { "My post" }
end

# GOOD — use association only when it must always be present
factory :post do
  user  # shorthand for association :user
  title { "My post" }
end

# Even better for performance: let caller control it
let(:author) { create(:user) }
let(:post)   { create(:post, user: author) }
```

### Sequences for Unique Fields

```ruby
factory :user do
  sequence(:email)    { |n| "user#{n}@example.com" }
  sequence(:username) { |n| "user_#{n}" }
end
```

### `after(:build)` vs `after(:create)`

```ruby
factory :user do
  after(:build) do |user|
    user.name = "#{user.first_name} #{user.last_name}"  # computed; no DB needed
  end

  after(:create) do |user|
    create(:profile, user: user)  # requires persisted user ID
  end
end
```

---

## SHARED EXAMPLES AND SHARED CONTEXTS

### When to Use Shared Examples

Extract to `shared_examples` when:
- The same behaviour is tested across 3+ classes (e.g., all controllers require authentication)
- A module or concern is included in multiple classes
- An interface/duck-type contract must be verified for multiple implementors

```ruby
# spec/support/shared_examples/paginatable.rb
RSpec.shared_examples "a paginatable endpoint" do
  describe "pagination" do
    before { create_list(described_factory, 25) }

    it "defaults to 20 items per page" do
      action.call
      expect(response.parsed_body["data"].size).to eq(20)
    end

    it "respects the per_page param" do
      action.call(per_page: 5)
      expect(response.parsed_body["data"].size).to eq(5)
    end

    it "returns total_count in meta" do
      action.call
      expect(response.parsed_body.dig("meta", "total_count")).to eq(25)
    end
  end
end

# In spec:
RSpec.describe "GET /api/v1/orders", type: :request do
  it_behaves_like "a paginatable endpoint" do
    let(:described_factory) { :order }
    let(:action) { ->(params = {}) { get api_v1_orders_path, params: params, headers: headers } }
  end
end
```

### When to Use Shared Contexts

Extract to `shared_context` when:
- Multiple describe/context groups need identical `let` setup and/or `before` hooks
- A standard authenticated session needs to be set up in many spec files

```ruby
# spec/support/shared_contexts/authenticated.rb
RSpec.shared_context "with authenticated admin" do
  let(:admin) { create(:user, :admin) }
  let(:headers) { { "Authorization" => "Bearer #{token_for(admin)}" } }

  before { sign_in admin }
end

RSpec.shared_context "with frozen time" do |time: "2024-06-01 12:00:00 UTC"|
  around do |example|
    Timecop.freeze(Time.zone.parse(time)) { example.run }
  end
end

# Usage
RSpec.describe "Admin reports" do
  include_context "with authenticated admin"
  include_context "with frozen time", time: "2024-01-15 09:00:00 UTC"

  it "returns reports created today" do
    create(:report, created_at: Time.current)
    get admin_reports_path, headers: headers
    expect(response.parsed_body["data"].first["date"]).to eq("2024-01-15")
  end
end
```

### Naming Convention

| Type | File location | Prefix |
|---|---|---|
| Shared examples | `spec/support/shared_examples/` | `a ...`, `behaves like ...` |
| Shared contexts | `spec/support/shared_contexts/` | `with ...`, `as ...` |

Ensure `spec/rails_helper.rb` or `spec/spec_helper.rb` loads the support directory:

```ruby
Dir[Rails.root.join("spec/support/**/*.rb")].each { |f| require f }
```

---

## RUBOCOP RSPEC RULE REFERENCE

| Rule | Pattern | Default Threshold |
|---|---|---|
| `RSpec/LetSetup` | `let!` for non-side-effect setup | — |
| `RSpec/AnyInstance` | `allow_any_instance_of` | — |
| `RSpec/BeforeAfterAll` | `before(:all)` with mutable state | — |
| `RSpec/ExampleLength` | Giant `it` blocks | 5 lines |
| `RSpec/MultipleExpectations` | Multiple `expect` without `aggregate_failures` | 1 expectation |
| `RSpec/NestedGroups` | Deep `context` nesting | Max 3 |
| `RSpec/ExampleWording` | `it "should ..."` | — |
| `RSpec/HaveAttributes` | Repeated attribute equality checks | — |
| `RSpec/ImplicitSubject` | Anonymous `subject` usage | — |
| `RSpec/SubjectDeclaration` | `subject` declared after `let` | — |
| `RSpec/DescribeClass` | `describe` on non-class values | — |
| `RSpec/DuplicateExampleGroupDescription` | Same group name twice | — |
| `RSpec/MessageSpies` | `expect(...).to receive` vs `have_received` | — |
| `RSpec/Rails/AvoidSetupHook` | `before(:each)` vs `before` | — |
| `FactoryBot/CreateList` | `n.times { create }` instead of `create_list` | — |
| `FactoryBot/AttributeDefinedStatically` | Static values instead of blocks | — |

Add to `.rubocop.yml`:

```yaml
require:
  - rubocop-rspec
  - rubocop-factory_bot

RSpec/ExampleLength:
  Max: 10

RSpec/MultipleExpectations:
  Max: 3

RSpec/NestedGroups:
  Max: 3

RSpec/AnyInstance:
  Enabled: true

RSpec/BeforeAfterAll:
  Enabled: true
```
