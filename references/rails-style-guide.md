# Rails Style Guide — Deslopper Rules

Sources: [rails.rubystyle.guide](https://rails.rubystyle.guide/) / RuboCop Rails / [rails-bestpractices.com](https://rails-bestpractices.com)

## Quick Antipattern Checklist

Run this first on any Rails file:

- [ ] `default_scope` anywhere → remove (named scope instead)
- [ ] `after_save` with email/queue → move to `after_commit`
- [ ] `.count` before/after `.each` on same relation → use `.size`
- [ ] `.where` in AR instance method → extract to filtered association
- [ ] `any?` before `each` on same relation → use `present?` or `.load.any?`
- [ ] `Time.now` / `Date.today` → use `Time.current` / `Date.current`
- [ ] `rescue Exception` → `rescue StandardError`
- [ ] No index on foreign keys → add `add_index`
- [ ] HTTP/Redis call without timeout → add open + read timeouts
- [ ] `User.all.each` for large tables → use `find_each`
- [ ] Instance variable in partial → pass as local
- [ ] Business logic in controller → extract to service/model
- [ ] `save` return value ignored → use `save!` or handle false
- [ ] `update_attribute` → use `update` (with validations)
- [ ] `enum` with array syntax → hash syntax
- [ ] `has_and_belongs_to_many` → `has_many :through`
- [ ] Missing `dependent:` on `has_many`/`has_one`
- [ ] Numeric HTTP status codes → symbols

---

## CONFIGURATION

```ruby
# Initializers — one file per gem
config/initializers/carrierwave.rb   # GOOD
config/initializers/setup.rb         # BAD — mixed concerns

# App-wide settings in application.rb
config.load_defaults 8.0             # Always match your Rails version

# Extra config in YAML
Rails.application.config_for(:payments)  # GOOD
```

---

## ROUTING

```ruby
# member / collection for extra REST actions
resources :subscriptions do
  get 'unsubscribe', on: :member     # GOOD
  get 'search', on: :collection      # GOOD
end

# NOT separate get routes
get '/subscriptions/:id/unsubscribe' # BAD

# Nested resources — shallow to avoid deep nesting
resources :posts do
  resources :comments, shallow: true # GOOD
end

# > 2–3 custom actions signals a missing resource
resources :posts do
  member do
    patch :publish
    patch :archive    # Many custom actions = extract new resource
    patch :feature
  end
end
# Fix: resource :publication, resource :archive, etc.

# Restrict generated routes
resources :comments, only: [:create, :destroy]  # GOOD
resources :comments                              # BAD — exposes 7 routes when 2 needed

# Split large route files
Rails.application.routes.draw do
  draw :api
  draw :admin
end
# config/routes/api.rb, config/routes/admin.rb
```

---

## CONTROLLERS

```ruby
# Skinny controller — one meaningful method per action
def create
  result = Orders::Create.call(order_params, user: current_user)
  result.success? ? redirect_to(result.order) : render(:new)
end

# Render symbols not numbers
render status: :forbidden                # GOOD
render status: :unprocessable_entity     # GOOD
render status: 403                       # BAD

# render plain: not render text:
render plain: 'OK'                       # GOOD
render text: 'OK'                        # BAD — deprecated

# Before actions with explicit only:/except:
before_action :authenticate_user!, only: [:create, :update]

# Namespaced base controllers
class Admin::BaseController < ApplicationController
  before_action :require_admin
  rescue_from ActiveRecord::RecordNotFound, with: :not_found
end
```

---

## MODELS

```ruby
# New-style validations — one attribute per call
validates :email, presence: true, format: { with: URI::MailTo::EMAIL_REGEXP }
validates :name, presence: true, length: { maximum: 100 }

# Custom validators in app/validators/
class ExpirationDateValidator < ActiveModel::Validator
  def validate(record)
    record.errors.add(:expiration_date, "can't be in the past") if record.expiration_date < Date.current
  end
end

# Scopes — use class method when lambda gets complex and must return a relation
scope :recent, -> { order(created_at: :desc) }         # GOOD — simple
def self.for_plan(plan)                                  # GOOD — complex
  where(plan: plan).where("expires_at > ?", Time.current)
end

# self[:attr] over read_attribute/write_attribute
self[:amount] * 100           # GOOD
read_attribute(:amount) * 100 # BAD

# ignored_columns — always append
self.ignored_columns += %i[legacy_col]   # GOOD
self.ignored_columns = %i[legacy_col]    # BAD — overwrites prior

# before_destroy with prepend: true for validation guards
before_destroy :check_no_active_orders, prepend: true  # GOOD
before_destroy :check_no_active_orders                  # BAD — too late

# Association build/create over manual FK
@post = current_user.posts.build(post_params)   # GOOD
@post = Post.new(post_params.merge(user_id: current_user.id))  # BAD
```

---

## ACTIVE RECORD QUERIES

```ruby
# find vs find_by
User.find(id)            # raises RecordNotFound — use in controllers
User.find_by(email: e)   # returns nil — use when absence is valid
User.find_by!(email: e)  # raises if missing — use in service objects

# Ranges in WHERE
User.where(created_at: 30.days.ago..)         # GOOD (beginless range)
User.where(created_at: 30.days.ago..7.days.ago)  # GOOD (between)
User.where("created_at >= ?", 30.days.ago)    # BAD

# pluck / pick / ids
User.pluck(:email)         # Many values — no model instantiation
User.pick(:email)          # Single value from first record
User.ids                   # Instead of pluck(:id)

# where.missing (Rails 6.1+)
Post.where.missing(:author)  # GOOD
Post.left_joins(:author).where(authors: { id: nil })  # BAD

# Multi-attribute where.not — be explicit (Rails 6.1+ NOR semantics)
User.where.not('status = ? AND plan = ?', 'active', 'basic')  # GOOD
User.where.not(status: 'active', plan: 'basic')                # BAD — NOR, not NAND

# Symbol/hash order syntax
User.order(created_at: :desc)   # GOOD
User.order('created_at DESC')   # BAD — breaks with table-ambiguous joins
```

---

## MIGRATIONS

```ruby
# Foreign keys with explicit constraint
t.references :user, foreign_key: true, null: false   # GOOD

# Boolean columns — always set default and null: false
add_column :users, :active, :boolean, default: true, null: false

# Reversible migrations — prefer change
def change
  add_column :users, :phone, :string
end

# Non-reversible — use reversible block
def change
  reversible do |dir|
    dir.up   { execute "ALTER TYPE status ADD VALUE 'archived'" }
    dir.down { raise ActiveRecord::IrreversibleMigration }
  end
end

# Test both directions before committing
# rails db:migrate && rails db:rollback
```

---

## VIEWS

```ruby
# partials — always pass locals
render 'post_summary', post: @post   # GOOD
render 'post_summary'                # BAD — relies on @post ivar

# render collection — batched, faster than loops
render @posts                        # GOOD
@posts.each { |p| render p }        # BAD

# No model layer in views
<% @active_users.each do |u| %>     # GOOD — controller set @active_users
<% User.active.each do |u| %>       # BAD — AR in view
```

---

## MAILERS

```ruby
# Naming — SomethingMailer
class OrderMailer < ApplicationMailer; end   # GOOD
class OrderMail < ApplicationMailer; end     # BAD

# Always both formats
def confirmation
  mail(to: @user.email) do |format|
    format.html
    format.text
  end
end

# Always deliver in background
OrderMailer.confirmation(@order).deliver_later   # GOOD
OrderMailer.confirmation(@order).deliver_now     # BAD in production
```

---

## TIME AND DURATION

```ruby
# Always use Time.current, never Time.now
Time.current                          # GOOD
Time.zone.now                         # GOOD
Time.zone.parse('2024-01-01')         # GOOD
Time.now                              # BAD
Time.parse('2024-01-01')              # BAD

# Duration helpers
2.days.from_now                       # GOOD
Time.current + 2.days                 # BAD

# Range helpers
user.posts.where(created_at: Date.current.all_month)   # GOOD
user.posts.where("created_at BETWEEN ? AND ?",          # BAD
  Date.current.beginning_of_month, Date.current.end_of_month)

# freeze_time in tests
freeze_time do                        # GOOD
  user.touch
  expect(user.updated_at).to eq(Time.current)
end
```

---

## ACTIVE SUPPORT

```ruby
# Safe navigation — prefer &. over try!
object&.name                 # GOOD
object.try!(:name)           # BAD

# Ruby stdlib over Active Support aliases
'hello'.start_with?('h')    # GOOD — stdlib
'hello'.starts_with?('h')   # BAD — AS alias

# exclude? over !include?
statuses.exclude?(:archived)  # GOOD
!statuses.include?(:archived) # BAD
```

---

## BUNDLER

```ruby
# Group gems correctly in Gemfile
group :development, :test do
  gem 'rspec-rails'
  gem 'factory_bot_rails'
  gem 'pry-rails'
end

group :test do
  gem 'capybara'
  gem 'webmock'
end

# Don't put dev/test gems outside their group
gem 'pry'       # BAD — in global scope
```
