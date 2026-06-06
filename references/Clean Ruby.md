# Clean Ruby: A Guide to Crafting Better Code for Rubyists
*by Carleton DiLeo (2019)*

## Table of Contents
1. [The Qualities of Clean Code](#chapter-1-the-qualities-of-clean-code)
2. [Naming Things](#chapter-2-naming-things)
3. [Creating Quality Methods](#chapter-3-creating-quality-methods)
4. [Using Boolean Logic](#chapter-4-using-boolean-logic)
5. [Classes](#chapter-5-classes)
6. [Refactoring](#chapter-6-refactoring)
7. [Test-Driven Development (TDD)](#chapter-7-test-driven-development-tdd)

---

## Chapter 1: The Qualities of Clean Code
What is clean code? It's a hard concept to define, but you know it when you see it. We focus on:
- **Readable**: Effort required to understand what a piece of code does.
- **Easy to change**: Extensibility and maintenance.
- **Straightforward**: Simplicity in solutions.

### Readability
Code should be like a well-written book; it doesn't expect you to dig into details to discover its purpose. Avoid ambiguous names and unnecessary complexity.

### Extensibility
The ability to add new features without breaking existing ones or requiring massive rewrites.

### Simplicity
Avoid complicated solutions unless you can’t solve your problem with a simple one. "Keep it simple, stupid" (K.I.S.S.).

---

## Chapter 2: Naming Things
Choosing the wrong name can determine whether code is easy to read or confusing. Poor names have a compounding effect.

### Variables
A good name takes away the guesswork. Trust your instincts.

#### Naming Conventions
Follow guidelines so the team writes using a single voice. In Ruby, use **snake_case** for variables and methods, and **CamelCase** for classes and modules.

#### Length
Avoid overly short names like `a` or `t`. However, names don't need to be paragraphs; find the balance.

#### Avoid Unnecessary Information
Don't include the data type in the name (e.g., `user_hash`).

### Methods
Methods should use **verbs** and describe the action they perform (e.g., `send_email`, `calculate_total`).
- **Return Value**: Naming should imply what is returned.
- **Bang Methods**: Use `!` only when the method is dangerous or modifies the receiver in place.

### Classes
Should represent a single **Purpose** or **Role**. Use nouns for class names.

---

## Chapter 3: Creating Quality Methods
The smallest block of code in an application.

### Parameters
- **Use Fewer Parameters**: Ideally 0-2. Use options hashes or keyword arguments for more.
- **Parameter Order**: Most important/required parameters first.

### Return Values
Methods should have consistent return types. Avoid returning `nil` if possible (use Null Object pattern or empty collections).

### Guard Clause
Use early returns to reduce nesting and clarify logic.
```ruby
def process(user)
  return unless user.active?
  # ... logic ...
end
```

### Limit Nesting
Avoid deep `if/else` or loop nesting. Extract logic into separate methods.

---

## Chapter 4: Using Boolean Logic
Complex boolean logic is a frequent source of bugs.

### Using a Variable
Store complex conditions in descriptive variables.
```ruby
is_eligible = user.active? && user.age >= 18
if is_eligible
  # ...
end
```

### Using a Method
Abstract complex logic into its own predicate method (ending in `?`).

### Unless
Use `unless` for negative conditions, but **never** with an `else` block.

### Ternary Operator
Use only for very simple, one-line assignments.

### Truthy and Falsy
In Ruby, only `false` and `nil` are falsy. Everything else (including `0` and `""`) is truthy.

---

## Chapter 5: Classes
Techniques for high-quality classes.

### Initialize Method
Keep it simple. Limit operations to assignments. Move complex operations to separate methods.

### Single Responsibility Principle (SRP)
A class should have only one reason to change.

### Composition Over Inheritance
"Has-a" vs "Is-a". Instead of deep inheritance trees, compose classes of smaller, specialized objects.

---

## Chapter 6: Refactoring
Consistently making small changes to improve code prevents technical debt.

### When to Refactor
Every code change is an opportunity. Use the "Red-Green-Refactor" cycle.

### Common Techniques
- **Extract Method**: Move code blocks into new, well-named methods.
- **Move Logic**: Shift logic closer to the data it operates on (Model over Controller).
- **Remove Comments**: If code needs a comment to be understood, it might need better naming or refactoring.

---

## Chapter 7: Test-Driven Development (TDD)
Write tests first to define the requirement.

### Benefits
- Codes will be simpler and cleaner.
- Easier to refactor with confidence.
- Documents the behavior of the application.

### Cycle
1. **Red**: Write a failing test.
2. **Green**: Write the minimum code to make it pass.
3. **Refactor**: Clean up the code while keeping the test passing.
