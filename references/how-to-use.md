# How to Use Code Deslopper

---

## Quick Start (30 seconds)

Paste your code and say one of these:

```
"Deslop this"
"Clean up this AI-generated code"
"Review this for slop"
"What smells does this have?"
```

That's it. The skill does the rest.

---

## Step 1 — What to Provide

Give the skill one of these inputs:

| Input type | What to send | Best for |
|---|---|---|
| **Single file** | Paste the file content | Focused cleanup of one class/module |
| **PR diff** | Paste `git diff main...HEAD` | Reviewing AI-generated changes |
| **File tree + files** | Paste `find app/ -name "*.rb"` output + suspicious files | Whole-feature audit |
| **Tool output + files** | Paste RuboCop/Reek/ESLint JSON + the flagged files | Maximum detection accuracy |

Also tell the skill:
1. **Stack** — Rails / React / Django / Node / mixed
2. **Tests** — yes (full coverage) / partial / none
3. **Scope** — "just the service layer" / "the whole PR" / "everything in app/services/"

---

## Step 2 — Phase 1: Read the Smell Report

The skill returns a smell report table. Here's how to read it:

```
| File                                          | Line | Category                | Risk | Evidence                              | Action  |
|-----------------------------------------------|------|-------------------------|------|---------------------------------------|---------|
| app/services/user_registration_service.rb     | 3    | trivial_service         | 2    | call delegates to User.create         | refactor|
| app/services/order_processor.rb               | 1    | fragmented_orchestration| 3    | only calls order.validate!            | ask     |
| app/services/order_handler.rb                 | 1    | fragmented_orchestration| 3    | only calls Payment.charge(order)      | ask     |
| app/services/base_service.rb                  | 1    | fake_inheritance        | 3    | empty class, no polymorphism          | ask     |
| app/controllers/users_controller.rb           | 12   | verb_inflation          | 2    | do_process instead of create          | refactor|
| app/models/post.rb                            | 45   | after_save_side_effect  | 4    | email enqueued inside transaction     | ask     |
| app/controllers/posts_controller.rb           | 8    | idor_risk               | 5    | Post.find without user scope          | STOP    |
```

**Risk colour guide:**

| Risk | Meaning | What happens |
|---|---|---|
| 1–2 | Safe — dead code, trivial inlining, style fix | Skill proceeds automatically |
| 3 | Moderate — cross-file, needs verification | Skill asks for your approval before patching |
| 4 | Structural — behaviour change possible | Skill presents full risk analysis, asks for explicit "yes" |
| 5 | Security / auth / callbacks | Skill stops. Flags for human review. Does not emit a patch. |

**Action column:**

| Action | What it means |
|---|---|
| `refactor` | Skill will auto-generate the patch |
| `ask` | Skill will explain the risk and wait for your approval |
| `STOP` | Security or high-risk — review manually |

---

## Step 3 — Approve or Redirect

After the smell report, reply with one of these:

| Your reply | What happens |
|---|---|
| `"Proceed with all"` | Applies risk 1–2 automatically; asks on each risk 3–4 item; stops on risk 5 |
| `"Only fix the 1–2 items"` | Auto-applies safe changes only; shows risk 3+ as flagged items for later |
| `"Fix items 1, 3, 5"` | Applies only the specific rows you name |
| `"Explain item 2 before touching it"` | Skill provides full analysis without applying a patch |
| `"Skip the service layer, just fix the controllers"` | Scopes Phase 2 to your preference |
| `"Stop — I'll handle the auth issue manually"` | Skill skips risk 5 items and continues with the rest |

---

## Step 4 — Read the Patch Output

Every approved change produces this structure:

```
## Safe Refactor Plan
[What is wrong, what to change, why it is safe]

## Proposed Patch
```diff
- old code
+ new code
```

## Test Impact
- Tests to run: spec/requests/users_spec.rb
- Tests that need updates: none
- New tests suggested: spec/services/order_checkout_spec.rb

## Risk Notes
- Behaviour change: none
- Files to double-check: none
- When to stop and ask: if payment gateway is called outside checkout flow
```

Apply the patch yourself (or say `"apply it"` if your agent can edit files).

---

## Common Prompts

### Run the full two-phase workflow
```
Deslop app/services/ — it's all AI-generated. Stack is Rails 7.
Tests are partial (request specs only, no unit specs on services).
```

### Review a PR diff
```
Here's the git diff for this PR. Run Code Deslopper on it.
Stack: Next.js 14 App Router + TypeScript. Tests: Vitest, full coverage.

[paste diff]
```

### Quick single-file check
```
Deslop this file. Flag anything risky, fix what's safe.

[paste file]
```

### Feed tool output for higher accuracy
```
Here's RuboCop output [paste rubocop.json] and Reek output [paste reek.json]
for app/services/. Now run Code Deslopper on top of this and give me
the unified smell report.
```

### Only YARD docs pass
```
Check this file for YARD documentation issues only.
Add missing docs on public methods, fix stale types, remove comments
that just restate the method name.

[paste file]
```

### Style pass only
```
Run a style-only pass on this file using the Ruby Style Guide.
Risk score 1 items only — auto-fix formatting, naming, flow of control.
Do not touch architecture or business logic.
```

### Python cleanup
```
Deslop this Django view file. AI generated it. 
Flag bare excepts, trivial CBVs, and Any type annotations.

[paste file]
```

---

## Reading Each Smell Category

| Category | What it is | Typical fix |
|---|---|---|
| `trivial_service` | Service object that only calls one AR method | Inline to model or controller |
| `fake_inheritance` | `BaseService` / `ApplicationService` with no polymorphism | Delete the chain |
| `fragmented_orchestration` | 3 classes each doing one step of the same workflow | Merge into one transaction object |
| `scope_vs_service` | Service that only builds a `where` chain | Convert to model scope |
| `enterprise_suffix` | `Manager`/`Coordinator`/`Handler` for trivial work | Rename to what it does |
| `empty_wrapper` | React component that only renders `{children}` | Use container element directly |
| `redundant_memo` | `useMemo` with cheap computation or static deps | Inline the value |
| `derived_state` | `useState` for a value derivable from props | Compute at render time |
| `n_plus_one` | Association accessed in loop without eager load | Add `includes` / `eager_load` |
| `count_vs_size` | `.count` on a loaded relation | Replace with `.size` |
| `after_save_side_effect` | Email/job fired inside transaction | Move to `after_commit` |
| `idor_risk` | AR load without user scoping | Scope to `current_user.association` |
| `sql_injection` | String interpolation in `where` | Use hash conditions or placeholders |
| `rescue_exception` | `rescue Exception` (catches signals) | `rescue StandardError` |
| `missing_timeout` | HTTP/Redis client without timeout | Add `open_timeout` + `timeout` |
| `long_method` | Method > 10 LOC (Ruby) or > 15 LOC (JS) | Extract sub-methods |
| `feature_envy` | Method uses another class's data more than its own | Move method to that class |
| `message_chain` | `a.b.c.d` — Law of Demeter violation | Use `delegate` or extract method |
| `primitive_obsession` | Raw string/int for domain concept | Create a value object |
| `speculative_generality` | YAGNI — methods that exist "just in case" | Delete |
| `dead_code` | Method/class with no callers | Delete |
| `stale_yard` | YARD doc with wrong type or stale `@param` | Update or remove |
| `missing_yard` | Public API in `lib/` with no YARD | Add YARD |
| `bare_except` | Python `except: pass` or `except Exception: pass` | Specific exception |
| `trivial_cbv` | Django class-based view with no CBV benefit | Convert to FBV |
| `any_type` | Python/TS `Any` / `: any` annotation | Concrete type |

---

## Concrete Before → After Examples

### Rails: Trivial Service (Risk 2 — auto-fix)

```ruby
# BEFORE — AI generated
class UserRegistrationService < BaseService
  def self.call(params)
    User.create(params)
  end
end

# In controller:
user = UserRegistrationService.call(user_params)

# AFTER — deslopped
# In controller:
user = User.create(user_params)
# UserRegistrationService deleted. BaseService deleted.
```

### Rails: Fragmented Orchestration (Risk 3 — ask first)

```ruby
# BEFORE — 3 separate classes called in sequence
OrderProcessor.call(@order)   # validates + saves
PaymentHandler.call(@order)   # charges card
NotificationManager.call(@order) # sends email

# AFTER — one transaction object
class OrderCheckout
  def self.call(order)
    ActiveRecord::Base.transaction do
      order.validate!
      order.save!
      PaymentGateway.charge(order.total)
      order.update!(paid: true)
    end
    OrderMailer.confirmation(order).deliver_later  # outside transaction
  end
end

OrderCheckout.call(@order)
```

### React: Wrapper + useMemo + derived state (Risk 1–2 — auto-fix)

```tsx
// BEFORE — AI generated
const UserCardWrapper = ({ children }) => <div className="card">{children}</div>;

const UserProfile = ({ user }) => {
  const fullName = useMemo(
    () => `${user.firstName} ${user.lastName}`,
    [user.firstName, user.lastName]
  );
  const [displayName, setDisplayName] = useState(fullName);
  useEffect(() => { setDisplayName(fullName); }, [fullName]);

  return (
    <UserCardWrapper>
      <h1>{displayName}</h1>
    </UserCardWrapper>
  );
};

// AFTER — deslopped
const UserProfile = ({ user }) => {
  const fullName = `${user.firstName} ${user.lastName}`;
  return (
    <div className="card">
      <h1>{fullName}</h1>
    </div>
  );
};
// UserCardWrapper deleted.
```

### Python: Trivial Manager + bare except (Risk 2 + Risk 4)

```python
# BEFORE — AI generated
class EmailManager:
    def send_welcome(self, user_id: int) -> None:
        try:
            user = User.objects.get(id=user_id)
            send_mail("Welcome", "Hello!", "from@example.com", [user.email])
        except:
            pass

# AFTER — deslopped
def send_welcome_email(user_id: int) -> None:
    try:
        user = User.objects.get(id=user_id)
        send_mail("Welcome", "Hello!", "from@example.com", [user.email])
    except User.DoesNotExist:
        logger.warning("send_welcome_email: user %s not found", user_id)
    except SMTPException as e:
        logger.error("send_welcome_email: SMTP error: %s", e)
        raise
# EmailManager class deleted.
```

---

## Using Tool Output as Phase 1 Input

If you run static analysis first, paste the output alongside the code:

```
Here is my RuboCop output and Reek output. Feed these into Phase 1 
of Code Deslopper and produce a unified smell report.

=== rubocop.json ===
[paste]

=== reek.json ===
[paste]

=== Files being reviewed ===
[paste app/services/*.rb]
```

The skill will cross-reference tool findings with its own semantic analysis —
for example: "Reek flags FeatureEnvy in `UserRegistrationService` AND Solargraph 
shows no external callers → Risk 2 trivial service, safe to inline."

See [tool-integration.md](tool-integration.md) for the full pipeline commands.

---

## Scope Limits — When to Split the Work

| Situation | Recommendation |
|---|---|
| > 10 files at once | Split into layers: run deslopper on services first, then models, then controllers |
| Mixed risk levels | Do a risk-1–2 pass first to clear safe wins, then discuss risk-3+ |
| No tests | Run deslopper in detect-only mode first: `"Smell report only — no patches"` |
| Legacy code you don't own | Use `"flag only, no patches"` and share the report with the owner |
| Active refactor in progress | Wait until the branch is stable before running Code Deslopper |

---

## What Code Deslopper Never Touches

No matter what you say, these are protected:

- Authorization and authentication logic
- Validations (`validates`, Zod schemas, Pydantic validators)
- Side effects in their declared order (DB writes, network calls, job enqueuing)
- Framework hooks (`before_action`, `after_commit`, `useEffect` dependencies)
- Public API method signatures
- Anything with risk score 5
- Test files (unless you explicitly ask for YARD/style fixes in specs)
