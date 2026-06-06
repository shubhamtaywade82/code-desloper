# Clean JavaScript and TypeScript: A Guide to Crafting Better Code

This guide adapts Robert C. Martin's *Clean Code* principles for JavaScript and TypeScript. Use these practices to write readable, reusable, and refactorable code.

## Table of Contents
1. [Variables](#1-variables)
2. [Functions](#2-functions)
3. [Objects & Data Structures](#3-objects--data-structures)
4. [Classes](#4-classes)
5. [SOLID Principles](#5-solid-principles)
6. [Concurrency](#6-concurrency)
7. [Error Handling](#7-error-handling)
8. [Testing](#8-testing)

---

## 1. Variables

### 1.1 Use Meaningful and Pronounceable Names
Avoid cryptic abbreviations. Names should reveal intent.
```typescript
// BEFORE
const yyyymmdstr = moment().format("YYYY/MM/DD");

// AFTER
const currentDate = moment().format("YYYY/MM/DD");
```

### 1.2 Use Searchable Names
Avoid magic numbers or strings. Store them in descriptive constants.
```typescript
// BEFORE
setTimeout(blastOff, 86400000);

// AFTER
const MILLISECONDS_IN_A_DAY = 24 * 60 * 60 * 1000;
setTimeout(blastOff, MILLISECONDS_IN_A_DAY);
```

### 1.3 Use Explanatory Variables
Break down complex conditions or logic into named variables.
```typescript
// BEFORE
if (address.split(",")[1].trim() === "NY") {
  // ...
}

// AFTER
const addressParts = address.split(",");
const state = addressParts[1].trim();
const isNewYork = state === "NY";

if (isNewYork) {
  // ...
}
```

### 1.4 Avoid Unnecessary Context
If the class or object name already provides context, do not repeat it in the property names.
```typescript
// BEFORE
const car = {
  carMake: "Honda",
  carModel: "Accord",
  carColor: "Blue"
};

// AFTER
const car = {
  make: "Honda",
  model: "Accord",
  color: "Blue"
};
```

---

## 2. Functions

### 2.1 Limit Function Arguments
Ideally, functions should have two or fewer arguments. If a function requires more parameters, bundle them into a single configuration object.
```typescript
// BEFORE
function createMenu(title: string, body: string, buttonText: string, cancellable: boolean) {
  // ...
}

// AFTER
interface MenuConfig {
  title: string;
  body: string;
  buttonText: string;
  cancellable: boolean;
}
function createMenu(config: MenuConfig) {
  // ...
}
```

### 2.2 Functions Should Do One Thing
A function should perform exactly one task. When a function does multiple things, it is harder to test, compose, and reason about.
```typescript
// BEFORE
function emailActiveUsers(users: User[]) {
  users.forEach((user) => {
    const userRecord = database.find(user.id);
    if (userRecord.isActive()) {
      emailService.send(userRecord.email, "Your account is active!");
    }
  });
}

// AFTER
function emailActiveUsers(users: User[]) {
  users.filter(isActiveUser).forEach(sendActivationEmail);
}

function isActiveUser(user: User): boolean {
  const userRecord = database.find(user.id);
  return userRecord.isActive();
}

function sendActivationEmail(user: User) {
  emailService.send(user.email, "Your account is active!");
}
```

### 2.3 Do Not Use Flags as Function Parameters
Flags tell the function to do more than one thing. Split the function into two instead.
```typescript
// BEFORE
function createFile(name: string, temp: boolean) {
  if (temp) {
    fs.create(`./temp/${name}`);
  } else {
    fs.create(name);
  }
}

// AFTER
function createTempFile(name: string) {
  fs.create(`./temp/${name}`);
}

function createFile(name: string) {
  fs.create(name);
}
```

### 2.4 Avoid Side Effects (Prefer Pure Functions)
A function should return a value based strictly on its inputs without modifying external state or mutable parameters unless explicitly expected.
```typescript
// BEFORE
const addItemToCart = (cart: CartItem[], item: CartItem): void => {
  cart.push(item); // Modifies the original array
};

// AFTER
const addItemToCart = (cart: CartItem[], item: CartItem): CartItem[] => {
  return [...cart, item]; // Returns a new array
};
```

---

## 3. Objects & Data Structures

### 3.1 Encapsulate Conditionals
Check state inside classes or objects rather than exposing internal properties.
```typescript
// BEFORE
if (user.status === "active" && user.permissions.includes("admin")) {
  // ...
}

// AFTER
if (user.isAdmin()) {
  // ...
}
```

---

## 4. Classes

### 4.1 Prefer Composition Over Inheritance
Inheritance introduces tight coupling. Use composition to assemble behaviors dynamically.
```typescript
// BEFORE
class Employee extends Person {
  // Tight coupling to Person details
}

// AFTER
class Employee {
  private personDetails: Person;
  constructor(person: Person) {
    this.personDetails = person;
  }
}
```

### 4.2 Use Method Chaining
Returning `this` at the end of class methods enables fluid method chaining.
```typescript
// BEFORE
const car = new Car();
car.setMake("Honda");
car.setModel("Civic");
car.setColor("Red");

// AFTER
class Car {
  private make = "";
  private model = "";
  private color = "";

  setMake(make: string): this {
    this.make = make;
    return this;
  }
  setModel(model: string): this {
    this.model = model;
    return this;
  }
  setColor(color: string): this {
    this.color = color;
    return this;
  }
}
const car = new Car().setMake("Honda").setModel("Civic").setColor("Red");
```

---

## 5. SOLID Principles

### 5.1 Single Responsibility Principle (SRP)
A class should have one, and only one, reason to change.
```typescript
// BEFORE
class User {
  constructor(private name: string) {}
  saveUser() {
    database.save(this); // Mixing identity and persistence
  }
}

// AFTER
class User {
  constructor(public readonly name: string) {}
}
class UserRepository {
  save(user: User) {
    database.save(user);
  }
}
```

### 5.2 Open/Closed Principle (OCP)
Software entities should be open for extension, but closed for modification.
```typescript
// BEFORE
class AreaCalculator {
  calculate(shapes: any[]) {
    return shapes.reduce((area, shape) => {
      if (shape.type === "rectangle") return area + shape.width * shape.height;
      if (shape.type === "circle") return area + Math.PI * Math.pow(shape.radius, 2);
      return area;
    }, 0);
  }
}

// AFTER
interface Shape {
  getArea(): number;
}
class Rectangle implements Shape {
  constructor(private width: number, private height: number) {}
  getArea() { return this.width * this.height; }
}
class Circle implements Shape {
  constructor(private radius: number) {}
  getArea() { return Math.PI * Math.pow(this.radius, 2); }
}
class AreaCalculator {
  calculate(shapes: Shape[]) {
    return shapes.reduce((area, shape) => area + shape.getArea(), 0);
  }
}
```

---

## 6. Concurrency

### 6.1 Prefer Promises & Async/Await Over Callbacks
Callbacks create deeply nested structures ("callback hell"). Async/await leads to clean, linear code.
```typescript
// BEFORE
getData((a) => {
  getMoreData(a, (b) => {
    getEvenMoreData(b, (c) => {
      console.log(c);
    });
  });
});

// AFTER
async function displayData() {
  const a = await getData();
  const b = await getMoreData(a);
  const c = await getEvenMoreData(b);
  console.log(c);
}
```

---

## 7. Error Handling

### 7.1 Never Swallow Caught Errors
Swallowing errors makes debugging impossible. Always log, rethrow, or handle them gracefully.
```typescript
// BEFORE
try {
  calculateResult();
} catch (error) {
  // Silent failure
}

// AFTER
try {
  calculateResult();
} catch (error) {
  console.error("Failed to calculate result:", error);
  notifyErrorTrackingService(error);
}
```

---

## 8. Testing

### 8.1 Single Concept Per Test
A test should verify one specific behavior. Use the **AAA (Arrange, Act, Assert)** pattern.
```typescript
// AFTER
describe("Calendar", () => {
  it("should block weekends when booking", () => {
    // Arrange
    const calendar = new Calendar();
    const saturday = new Date("2026-06-06");

    // Act
    const isBookable = calendar.canBook(saturday);

    // Assert
    expect(isBookable).toBe(false);
  });
});
```
