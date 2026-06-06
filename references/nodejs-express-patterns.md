# Node.js / Express / Fastify Anti-Patterns Reference

> Reference for the **Code Deslopper** skill. Each pattern documents what AI commonly generates, why it is harmful, and the corrected form. Risk scores are 1 (cosmetic) to 5 (production-breaking / security incident).

---

## Table of Contents

1. [Business Logic in Route Handlers](#1-business-logic-in-route-handlers)
2. [Missing Error Middleware](#2-missing-error-middleware)
3. [Callback Pyramid / Not Using async/await](#3-callback-pyramid--not-using-asyncawait)
4. [No Input Validation at Route Boundary](#4-no-input-validation-at-route-boundary)
5. [Synchronous Blocking in Async Context](#5-synchronous-blocking-in-async-context)
6. [Missing Request / Response Timeout](#6-missing-request--response-timeout)
7. [Overly Broad `app.use()` / Middleware Ordering Issues](#7-overly-broad-appuse--middleware-ordering-issues)
8. [God Router — No HTTP/Business Layer Separation](#8-god-router--no-httpbusiness-layer-separation)
9. [Secrets/Config Hard-Coded in Source](#9-secretsconfig-hard-coded-in-source)
10. [No Graceful Shutdown Handling](#10-no-graceful-shutdown-handling)
11. [`console.log` Instead of Structured Logger](#11-consolelog-instead-of-structured-logger)
12. [Missing Rate Limiting / Auth Middleware Ordering](#12-missing-rate-limiting--auth-middleware-ordering)
13. [`require()` Inside Functions (Hot-Path Module Loading)](#13-require-inside-functions-hot-path-module-loading)
14. [Unhandled Promise Rejections Not Forwarded to `next(err)`](#14-unhandled-promise-rejections-not-forwarded-to-nexterr)
15. [Global State Mutation in Middleware](#15-global-state-mutation-in-middleware)
16. [Missing or Overly Permissive CORS](#16-missing-or-overly-permissive-cors)
17. [No Response Compression](#17-no-response-compression)
18. [Leaking Internal Error Details to Clients](#18-leaking-internal-error-details-to-clients)
19. [Not Using `router.param()` for Common Param Resolution](#19-not-using-routerparam-for-common-param-resolution)
20. [Circular `require()` / Dependency Cycles](#20-circular-require--dependency-cycles)
21. [Express Middleware Ordering Guide](#express-middleware-ordering-guide)
22. [Fastify vs Express: Pattern Applicability Matrix](#fastify-vs-express-pattern-applicability-matrix)
23. [Recommended Project Layout](#recommended-project-layout)

---

## 1. Business Logic in Route Handlers

**Risk: 4 / 5**

AI routinely drops database queries, external API calls, and complex conditionals directly into the route handler because it is the shortest path from prompt to working code. This makes the logic untestable without spinning up an HTTP server and couples every future change to the routing layer.

### Before (AI-generated)

```typescript
// routes/users.ts
import { Router, Request, Response } from 'express';
import { db } from '../db';

const router = Router();

router.post('/users', async (req: Request, res: Response) => {
  const { email, password, role } = req.body;

  // business logic, validation, hashing — all inline
  if (!email.includes('@')) {
    return res.status(400).json({ error: 'Invalid email' });
  }

  const existing = await db.query('SELECT id FROM users WHERE email = $1', [email]);
  if (existing.rows.length > 0) {
    return res.status(409).json({ error: 'Email already registered' });
  }

  const hash = require('bcrypt').hashSync(password, 10); // blocking sync AND hot-path require
  const result = await db.query(
    'INSERT INTO users (email, password_hash, role) VALUES ($1, $2, $3) RETURNING id',
    [email, hash, role ?? 'user']
  );

  res.status(201).json({ id: result.rows[0].id });
});

export default router;
```

### After (deslopped)

```typescript
// services/user.service.ts
import bcrypt from 'bcrypt';
import { db } from '../db';
import { ConflictError, ValidationError } from '../errors';

export interface CreateUserInput {
  email: string;
  password: string;
  role?: string;
}

export async function createUser(input: CreateUserInput): Promise<{ id: string }> {
  if (!input.email.includes('@')) {
    throw new ValidationError('Invalid email address');
  }

  const existing = await db.query('SELECT id FROM users WHERE email = $1', [input.email]);
  if (existing.rows.length > 0) {
    throw new ConflictError('Email already registered');
  }

  const passwordHash = await bcrypt.hash(input.password, 10);
  const result = await db.query(
    'INSERT INTO users (email, password_hash, role) VALUES ($1, $2, $3) RETURNING id',
    [input.email, passwordHash, input.role ?? 'user']
  );

  return { id: result.rows[0].id };
}

// routes/users.ts
import { Router, Request, Response, NextFunction } from 'express';
import { createUser } from '../services/user.service';

const router = Router();

router.post('/users', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const user = await createUser(req.body);
    res.status(201).json(user);
  } catch (err) {
    next(err); // delegate to error middleware
  }
});

export default router;
```

**Safety notes**
- The service layer is now independently unit-testable with no HTTP machinery.
- Throwing typed errors (`ConflictError`, `ValidationError`) lets the central error middleware map them to status codes once, globally.
- Fastify: same pattern; use a `service` injected via `fastify.decorate` or dependency injection rather than a bare import if you want to mock it in plugin tests.

---

## 2. Missing Error Middleware

**Risk: 5 / 5**

Without a four-argument Express error handler, unhandled errors either crash the process or silently return a 200 with an empty body. AI almost never adds the error middleware because it is not part of the specific feature requested.

### Before (AI-generated)

```typescript
// app.ts
import express from 'express';
import userRouter from './routes/users';

const app = express();
app.use(express.json());
app.use('/api', userRouter);

app.listen(3000);
// Any thrown error in a route handler -> Express default error handler ->
// HTML "Internal Server Error" page, status 500, leaks stack in development.
// In production the response often hangs entirely.
```

### After (deslopped)

```typescript
// app.ts
import express, { Request, Response, NextFunction } from 'express';
import userRouter from './routes/users';
import { AppError } from './errors';
import { logger } from './logger';

const app = express();
app.use(express.json());
app.use('/api', userRouter);

// 404 catch-all — must come AFTER all routers
app.use((_req: Request, res: Response) => {
  res.status(404).json({ error: 'Not found' });
});

// Central error handler — MUST have exactly 4 parameters so Express recognises it
app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
  if (err instanceof AppError) {
    logger.warn({ err }, err.message);
    return res.status(err.statusCode).json({ error: err.message });
  }

  logger.error({ err }, 'Unexpected error');
  res.status(500).json({ error: 'Internal server error' });
});

export default app;

// errors.ts
export class AppError extends Error {
  constructor(
    public readonly message: string,
    public readonly statusCode: number = 500
  ) {
    super(message);
    this.name = this.constructor.name;
    Error.captureStackTrace(this, this.constructor);
  }
}

export class ValidationError extends AppError {
  constructor(message: string) { super(message, 400); }
}

export class NotFoundError extends AppError {
  constructor(message: string) { super(message, 404); }
}

export class ConflictError extends AppError {
  constructor(message: string) { super(message, 409); }
}
```

**Safety notes**
- The four-parameter signature `(err, req, res, next)` is mandatory. If you accidentally omit a parameter, Express treats the function as a regular middleware and it will never receive errors.
- Always log the full error object server-side; never forward raw stack traces to the client.
- Fastify: use `fastify.setErrorHandler()`. Fastify's error model is slightly different — it calls your handler with `(error, request, reply)`.

---

## 3. Callback Pyramid / Not Using async/await

**Risk: 3 / 5**

Older training data causes AI to emit nested callbacks inside Express route handlers. Errors thrown inside callbacks are not caught by Express or any upstream `try/catch`.

### Before (AI-generated)

```typescript
router.get('/report', (req, res) => {
  db.query('SELECT * FROM orders', (err, result) => {
    if (err) return res.status(500).json({ error: err.message }); // leaks details
    fs.readFile('./template.html', 'utf8', (err2, template) => {
      if (err2) return res.status(500).json({ error: err2.message });
      const html = template.replace('{{data}}', JSON.stringify(result.rows));
      mailer.send({ to: req.query.email, body: html }, (err3) => {
        if (err3) return res.status(500).json({ error: err3.message });
        res.json({ sent: true });
      });
    });
  });
});
```

### After (deslopped)

```typescript
import { promisify } from 'util';
import fs from 'fs/promises';

router.get('/report', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const result = await db.query('SELECT * FROM orders');
    const template = await fs.readFile('./template.html', 'utf8');
    const html = template.replace('{{data}}', JSON.stringify(result.rows));
    await mailer.sendAsync({ to: req.query.email as string, body: html });
    res.json({ sent: true });
  } catch (err) {
    next(err);
  }
});
```

**Safety notes**
- Wrap every `async` route handler in `try/catch` and forward to `next(err)`, or use a wrapper utility (see pattern 14).
- `util.promisify` converts callback-based APIs when a native promise variant is unavailable.
- Fastify: async handlers automatically propagate thrown errors to the error handler — no `try/catch` required, but it is still good practice for clarity.

---

## 4. No Input Validation at Route Boundary

**Risk: 4 / 5**

AI trusts `req.body` completely. Without validation, malformed payloads reach the database, business logic, or external APIs, causing cryptic runtime errors, SQL injection vectors, or data corruption.

### Before (AI-generated)

```typescript
router.post('/transfer', async (req, res) => {
  const { fromAccount, toAccount, amount } = req.body;
  await bankService.transfer(fromAccount, toAccount, amount); // amount could be NaN, negative, undefined
  res.json({ ok: true });
});
```

### After (deslopped) — Zod

```typescript
import { z } from 'zod';
import { validateBody } from '../middleware/validate';

const TransferSchema = z.object({
  fromAccount: z.string().uuid(),
  toAccount: z.string().uuid(),
  amount: z.number().positive().multipleOf(0.01),
});

router.post(
  '/transfer',
  validateBody(TransferSchema),
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      // req.body is now typed and validated
      const { fromAccount, toAccount, amount } = req.body;
      await bankService.transfer(fromAccount, toAccount, amount);
      res.json({ ok: true });
    } catch (err) {
      next(err);
    }
  }
);

// middleware/validate.ts
import { z, ZodSchema } from 'zod';
import { Request, Response, NextFunction } from 'express';

export function validateBody<T>(schema: ZodSchema<T>) {
  return (req: Request, res: Response, next: NextFunction): void => {
    const result = schema.safeParse(req.body);
    if (!result.success) {
      res.status(400).json({
        error: 'Validation failed',
        issues: result.error.issues.map((i) => ({ path: i.path, message: i.message })),
      });
      return;
    }
    req.body = result.data;
    next();
  };
}
```

**Safety notes**
- Validate all untrusted sources: `req.body`, `req.params`, `req.query`, `req.headers`.
- Zod is preferred for TypeScript projects because it produces inferred types. Joi and `express-validator` are equally valid.
- Fastify: use JSON Schema for route-level validation via `schema.body`; it is compiled to a fast validator and runs before the handler automatically.

---

## 5. Synchronous Blocking in Async Context

**Risk: 4 / 5**

AI uses synchronous Node.js APIs (`fs.readFileSync`, `crypto.pbkdf2Sync`, `JSON.parse` on large buffers) inside request handlers. These block the event loop and degrade latency for every concurrent user.

### Before (AI-generated)

```typescript
router.get('/config', (req, res) => {
  const raw = fs.readFileSync('./config.json', 'utf8'); // blocks event loop
  const config = JSON.parse(raw);                       // fine for small payloads, risky at scale
  res.json(config);
});

router.post('/hash', (req, res) => {
  const hash = crypto.pbkdf2Sync(req.body.password, 'salt', 100000, 64, 'sha512'); // ~200 ms block
  res.json({ hash: hash.toString('hex') });
});
```

### After (deslopped)

```typescript
import fs from 'fs/promises';
import { promisify } from 'util';
import crypto from 'crypto';

const pbkdf2 = promisify(crypto.pbkdf2);

// Load config once at startup, not per-request
let appConfig: Record<string, unknown>;
async function loadConfig(): Promise<void> {
  const raw = await fs.readFile('./config.json', 'utf8');
  appConfig = JSON.parse(raw);
}

// Large JSON: stream and parse incrementally with `stream-json`
router.get('/config', (_req: Request, res: Response) => {
  res.json(appConfig); // already loaded at boot
});

router.post('/hash', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const hash = await pbkdf2(req.body.password, 'salt', 100000, 64, 'sha512');
    res.json({ hash: hash.toString('hex') });
  } catch (err) {
    next(err);
  }
});
```

**Safety notes**
- Any operation taking more than ~1 ms that is not I/O-bound should be offloaded to a worker thread (`worker_threads`) or a separate process.
- `JSON.parse` on payloads over ~50 MB can pause the loop measurably; use streaming JSON parsers (`stream-json`, `@streamparser/json`) for large bodies.
- Enforce a body size limit in your JSON middleware: `express.json({ limit: '1mb' })`.
- Fastify: same concerns; Fastify's built-in JSON serializer is faster than `JSON.stringify` but `JSON.parse` during deserialization is still synchronous.

---

## 6. Missing Request / Response Timeout

**Risk: 4 / 5**

AI-generated servers have no timeouts. A slow upstream dependency or an infinite loop causes the request to hang, consuming a socket and memory until the process is restarted.

### Before (AI-generated)

```typescript
const app = express();
app.use(express.json());
// No timeout anywhere
app.use('/api', router);
app.listen(3000);
```

### After (deslopped)

```typescript
import http from 'http';
import express from 'express';
import { createServer } from 'http';

const app = express();

// 1. Request-level timeout via middleware (response must start within N ms)
app.use((req: Request, res: Response, next: NextFunction) => {
  res.setTimeout(30_000, () => {
    res.status(503).json({ error: 'Request timed out' });
  });
  next();
});

app.use(express.json({ limit: '1mb' }));
app.use('/api', router);

// 2. Server-level keep-alive and headers timeout
const server = createServer(app);
server.keepAliveTimeout = 65_000;   // slightly above ALB/nginx defaults
server.headersTimeout = 66_000;     // must be > keepAliveTimeout

// 3. Per-route timeout for expensive operations
import { createTimeout } from '../middleware/timeout'; // see below

router.get('/slow-report', createTimeout(10_000), async (req, res, next) => {
  // ...
});

// middleware/timeout.ts
export function createTimeout(ms: number) {
  return (_req: Request, res: Response, next: NextFunction): void => {
    const handle = setTimeout(() => {
      if (!res.headersSent) {
        res.status(503).json({ error: 'Operation timed out' });
      }
    }, ms);
    res.on('finish', () => clearTimeout(handle));
    res.on('close', () => clearTimeout(handle));
    next();
  };
}
```

**Safety notes**
- `server.headersTimeout` must be greater than `server.keepAliveTimeout` to prevent race conditions with reverse proxies.
- The `connect-timeout` npm package provides similar functionality but is unmaintained; prefer the pattern above.
- Fastify: use `fastify.server.setTimeout()` or the per-route `config.timeout` option with `@fastify/request-context`.

---

## 7. Overly Broad `app.use()` / Middleware Ordering Issues

**Risk: 3 / 5**

AI registers middleware in arbitrary order or applies heavy middleware globally when it is only needed for specific routes, adding latency to every request.

### Before (AI-generated)

```typescript
app.use(morgan('combined'));            // OK globally
app.use(helmet());                      // OK globally
app.use('/api', router);
app.use(express.json());               // WRONG: after router, body never parsed for /api
app.use(authMiddleware);               // WRONG: runs after routes, never guards them
app.use(express.static('public'));     // WRONG: should come last or be served by nginx
```

### After (deslopped)

```typescript
// Correct ordering — read top-to-bottom

// 1. Security headers (always first)
app.use(helmet());

// 2. Request logging (needs raw request, before body parse)
app.use(morgan('combined'));

// 3. Body parsing (before any route that reads req.body)
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: true, limit: '1mb' }));

// 4. CORS (before routes so preflight OPTIONS gets handled)
app.use(cors(corsOptions));

// 5. Global rate limiting
app.use(rateLimiter);

// 6. Authentication (global or scoped; see pattern 12)
app.use('/api', authMiddleware);

// 7. Application routes
app.use('/api/v1', v1Router);
app.use('/api/v2', v2Router);

// 8. Static files (low priority, served last by Node — prefer nginx/CDN)
app.use(express.static('public'));

// 9. 404 handler
app.use((_req, res) => res.status(404).json({ error: 'Not found' }));

// 10. Error handler (must be last, must have 4 params)
app.use(errorHandler);
```

**Safety notes**
- Express middleware runs in registration order; there is no way to re-order without restarting.
- Avoid `app.use(express.json())` after `app.use('/api', router)` — the body will be unparsed inside the router.
- Fastify: middleware ordering is less fragile because Fastify uses a plugin system with explicit `await fastify.register(...)` sequencing, but `addHook('onRequest', ...)` vs `addHook('preHandler', ...)` order still matters.

---

## 8. God Router — No HTTP/Business Layer Separation

**Risk: 4 / 5**

AI generates a single router file that handles authentication, database access, caching, email sending, and HTTP responses. This is the route-level equivalent of pattern 1 but at file scale.

### Before (AI-generated)

```typescript
// routes/index.ts — 800+ lines
router.post('/checkout', async (req, res) => { /* DB, Stripe, email, inventory, logging */ });
router.get('/dashboard', async (req, res) => { /* DB, Redis, aggregation, PDF generation */ });
router.delete('/account', async (req, res) => { /* DB, email, analytics event, cascade */ });
```

### After (deslopped)

```
src/
  routes/          ← HTTP concerns only (parse req, call service, send res)
    checkout.ts
    dashboard.ts
    account.ts
  services/        ← orchestration (calls repositories, external services)
    checkout.service.ts
    dashboard.service.ts
    account.service.ts
  repositories/    ← data access only (SQL / ORM / Redis)
    order.repository.ts
    user.repository.ts
  clients/         ← external API wrappers (Stripe, SendGrid, etc.)
    stripe.client.ts
    email.client.ts
```

```typescript
// routes/checkout.ts — thin HTTP adapter
import { Router } from 'express';
import { CheckoutService } from '../services/checkout.service';
import { validateBody } from '../middleware/validate';
import { CheckoutSchema } from '../schemas/checkout.schema';

const router = Router();
const service = new CheckoutService();

router.post('/', validateBody(CheckoutSchema), async (req, res, next) => {
  try {
    const result = await service.processCheckout(req.body, req.user!.id);
    res.status(201).json(result);
  } catch (err) {
    next(err);
  }
});

export default router;
```

**Safety notes**
- Routes should contain no business logic — only: parse input, call service, map output to HTTP response, forward errors.
- Services should contain no HTTP primitives (`req`, `res`, `next`). They must be callable from a CLI, queue worker, or test without an HTTP context.

---

## 9. Secrets/Config Hard-Coded in Source

**Risk: 5 / 5**

AI hard-codes API keys, database URLs, and JWT secrets directly in source files. These end up in version control and are exposed in build artifacts.

### Before (AI-generated)

```typescript
const stripe = new Stripe('sk_live_abcdef1234567890', { apiVersion: '2023-10-16' });

const jwtSecret = 'mysecretkey'; // committed to git

const db = new Pool({
  connectionString: 'postgresql://admin:password@prod-db.internal:5432/myapp',
});
```

### After (deslopped)

```typescript
// config/env.ts — single validated config module
import { z } from 'zod';

const EnvSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']),
  DATABASE_URL: z.string().url(),
  JWT_SECRET: z.string().min(32),
  STRIPE_SECRET_KEY: z.string().startsWith('sk_'),
  PORT: z.coerce.number().default(3000),
});

const parsed = EnvSchema.safeParse(process.env);
if (!parsed.success) {
  console.error('Invalid environment variables:', parsed.error.flatten().fieldErrors);
  process.exit(1);
}

export const env = parsed.data;

// usage
import { env } from '../config/env';
const stripe = new Stripe(env.STRIPE_SECRET_KEY, { apiVersion: '2023-10-16' });
```

```
# .env (git-ignored)
DATABASE_URL=postgresql://admin:password@localhost:5432/myapp_dev
JWT_SECRET=a-random-32-plus-character-string-here
STRIPE_SECRET_KEY=sk_test_...
```

**Safety notes**
- Add `.env` and all `*.local` variants to `.gitignore` before the first commit.
- Use `.env.example` with dummy values committed to the repo as documentation.
- In production, inject secrets via your platform's secret manager (AWS Secrets Manager, GCP Secret Manager, Vault, Kubernetes secrets) — never via committed files.
- Fail fast at startup if required variables are missing (as shown above with `process.exit(1)`).

---

## 10. No Graceful Shutdown Handling

**Risk: 4 / 5**

AI-generated servers terminate instantly on `SIGTERM`. In-flight requests are aborted, database transactions are rolled back unexpectedly, and message queue consumers abandon work.

### Before (AI-generated)

```typescript
app.listen(3000, () => console.log('Server running'));
// SIGTERM from Kubernetes/Docker kills process immediately
// No connection draining, no cleanup
```

### After (deslopped)

```typescript
import http from 'http';
import { db } from './db';
import { logger } from './logger';

const server = http.createServer(app);

server.listen(env.PORT, () => {
  logger.info({ port: env.PORT }, 'Server started');
});

async function shutdown(signal: string): Promise<void> {
  logger.info({ signal }, 'Shutdown initiated');

  // 1. Stop accepting new connections
  server.close(async (err) => {
    if (err) {
      logger.error({ err }, 'Error closing server');
      process.exit(1);
    }

    try {
      // 2. Drain external resources in order
      await db.end();                  // close DB pool
      // await redisClient.quit();     // close Redis
      // await mqConsumer.stop();      // stop queue consumer
      logger.info('Graceful shutdown complete');
      process.exit(0);
    } catch (cleanupErr) {
      logger.error({ err: cleanupErr }, 'Cleanup failed');
      process.exit(1);
    }
  });

  // 3. Force kill if draining takes too long (Kubernetes terminationGracePeriodSeconds)
  setTimeout(() => {
    logger.warn('Shutdown timeout exceeded, forcing exit');
    process.exit(1);
  }, 30_000).unref();
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));

// Catch unhandled errors so the process does not die silently
process.on('uncaughtException', (err) => {
  logger.fatal({ err }, 'Uncaught exception');
  process.exit(1);
});

process.on('unhandledRejection', (reason) => {
  logger.fatal({ reason }, 'Unhandled promise rejection');
  process.exit(1);
});
```

**Safety notes**
- Kubernetes sends `SIGTERM` and waits `terminationGracePeriodSeconds` (default 30 s) before sending `SIGKILL`. Match your shutdown timeout to this value minus a small buffer.
- `server.close()` stops new connections but does not close existing keep-alive connections in Node < 18.2. Use the `http-terminator` package or `server.closeAllConnections()` (Node 18.2+) to close idle keep-alive sockets immediately.
- Fastify: call `await fastify.close()` which triggers all registered `onClose` hooks in reverse registration order.

---

## 11. `console.log` for Logging Instead of Structured Logger

**Risk: 3 / 5**

AI uses `console.log` and `console.error` throughout. These produce unstructured plain-text output that is impossible to query in log aggregation systems and has no log levels, correlation IDs, or serialization safety.

### Before (AI-generated)

```typescript
router.post('/order', async (req, res) => {
  console.log('Creating order for user', req.user.id);
  try {
    const order = await orderService.create(req.body);
    console.log('Order created:', order.id);
    res.json(order);
  } catch (err) {
    console.error('Failed to create order:', err); // may log sensitive data
    res.status(500).json({ error: 'Server error' });
  }
});
```

### After (deslopped) — pino

```typescript
// logger.ts
import pino from 'pino';

export const logger = pino({
  level: process.env.LOG_LEVEL ?? 'info',
  redact: ['req.headers.authorization', 'req.body.password', 'req.body.cardNumber'],
  ...(process.env.NODE_ENV !== 'production' && {
    transport: { target: 'pino-pretty', options: { colorize: true } },
  }),
});

// Attach request-scoped child logger with correlation ID
// middleware/requestLogger.ts
import { v4 as uuidv4 } from 'uuid';

export function requestLogger(req: Request, res: Response, next: NextFunction): void {
  req.log = logger.child({
    requestId: req.headers['x-request-id'] ?? uuidv4(),
    method: req.method,
    url: req.url,
  });
  req.log.info('Request received');
  const start = Date.now();
  res.on('finish', () => {
    req.log.info({ statusCode: res.statusCode, durationMs: Date.now() - start }, 'Request completed');
  });
  next();
}

// route handler
router.post('/order', async (req: Request, res: Response, next: NextFunction) => {
  req.log.info({ userId: req.user!.id }, 'Creating order');
  try {
    const order = await orderService.create(req.body);
    req.log.info({ orderId: order.id }, 'Order created');
    res.json(order);
  } catch (err) {
    next(err); // error middleware logs at error level
  }
});
```

**Safety notes**
- Use `redact` to prevent logging sensitive fields; pino replaces them with `[Redacted]`.
- Structured JSON logs (one JSON object per line) are directly ingested by Datadog, CloudWatch, Elastic, Loki, etc.
- `console.log` is synchronous in some environments and can itself block the event loop under high write volume; pino is asynchronous by default.
- Winston is an acceptable alternative; pino is preferred for performance-sensitive applications.

---

## 12. Missing Rate Limiting / Auth Middleware Ordering

**Risk: 5 / 5**

AI either omits rate limiting entirely or registers it after authentication, allowing unauthenticated requests to hammer the auth layer and enabling credential-stuffing attacks.

### Before (AI-generated)

```typescript
app.use(express.json());
app.use('/api', authMiddleware);   // auth runs before rate limit — attacker can enumerate
app.use('/api', router);
// No rate limiting at all on public routes
```

### After (deslopped)

```typescript
import rateLimit from 'express-rate-limit';
import RedisStore from 'rate-limit-redis';

// Tighter limit on auth endpoints (brute-force protection)
const authRateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  limit: 10,
  standardHeaders: 'draft-7',
  legacyHeaders: false,
  store: new RedisStore({ sendCommand: (...args) => redisClient.sendCommand(args) }),
  keyGenerator: (req) => req.ip ?? 'unknown',
  message: { error: 'Too many requests, please try again later' },
});

// General API limit
const apiRateLimiter = rateLimit({
  windowMs: 60 * 1000,
  limit: 100,
  store: new RedisStore({ sendCommand: (...args) => redisClient.sendCommand(args) }),
});

// Correct order for auth routes:
// 1. Rate limit FIRST (unauthenticated, cheap to evaluate)
// 2. Then parse body
// 3. Then validate input
// 4. Then authenticate
app.post('/auth/login', authRateLimiter, validateBody(LoginSchema), loginHandler);
app.post('/auth/register', authRateLimiter, validateBody(RegisterSchema), registerHandler);

// Correct order for protected routes:
// 1. Rate limit (global)
// 2. Authenticate
// 3. Authorize (role/permission check)
// 4. Validate input
// 5. Handler
app.use('/api', apiRateLimiter, authMiddleware);
app.use('/api/admin', requireRole('admin'));
app.use('/api', router);
```

**Safety notes**
- Use a distributed store (Redis) for rate limiting in multi-instance deployments. In-memory stores are per-process and easily bypassed by running multiple dynos/pods.
- Consider IP + user-ID composite keys for authenticated endpoints to prevent a single compromised account from burning rate limits for others.
- Fastify: use `@fastify/rate-limit` with the `redis` option. Hook placement: `preHandler` for per-route, `onRequest` for global.

---

## 13. `require()` Inside Functions (Hot-Path Module Loading)

**Risk: 3 / 5**

AI occasionally moves `require()` calls inside route handlers or frequently called functions. Node.js caches modules after the first load, but the cache lookup, file-system stat, and JSON parse still happen on the first call per process and add latency. More importantly, it signals a design smell and can break tree-shaking.

### Before (AI-generated)

```typescript
router.post('/pdf', async (req, res, next) => {
  try {
    const PDFDocument = require('pdfkit'); // loaded on first request, not at startup
    const sharp = require('sharp');
    // ...
  } catch (err) {
    next(err);
  }
});
```

### After (deslopped)

```typescript
// All imports at the top of the module, evaluated once at startup
import PDFDocument from 'pdfkit';
import sharp from 'sharp';

router.post('/pdf', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const doc = new PDFDocument();
    // ...
  } catch (err) {
    next(err);
  }
});
```

**Legitimate exception — lazy loading for cold-start optimisation:**

```typescript
// Acceptable: dynamic import for heavy modules not needed on every code path
// and only in ESM context or where the trade-off is explicit
let heavyLib: typeof import('some-heavy-lib') | null = null;

async function getHeavyLib() {
  if (!heavyLib) {
    heavyLib = await import('some-heavy-lib');
  }
  return heavyLib;
}
```

**Safety notes**
- CommonJS `require()` is synchronous; inside an async handler it still blocks the event loop on first invocation.
- In ESM, dynamic `import()` is async and acceptable for lazy loading, but should be memoized as shown above.
- Never conditionally `require()` inside try/catch to "silently fail" on missing optional dependencies — fail loudly at startup.

---

## 14. Unhandled Promise Rejections Not Forwarded to `next(err)`

**Risk: 5 / 5**

AI generates `async` route handlers without `try/catch`. Express does not automatically catch promise rejections (Express 4). The rejection goes to the global `unhandledRejection` handler and typically crashes or silently drops the request.

### Before (AI-generated)

```typescript
// Express 4 — no try/catch, no next(err)
router.get('/users/:id', async (req, res) => {
  const user = await userService.findById(req.params.id); // rejection? silent hang
  res.json(user);
});
```

### After (deslopped) — Option A: try/catch (explicit)

```typescript
router.get('/users/:id', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const user = await userService.findById(req.params.id);
    res.json(user);
  } catch (err) {
    next(err);
  }
});
```

### After (deslopped) — Option B: asyncHandler wrapper (DRY)

```typescript
// utils/asyncHandler.ts
import { Request, Response, NextFunction, RequestHandler } from 'express';

type AsyncRequestHandler = (req: Request, res: Response, next: NextFunction) => Promise<void>;

export function asyncHandler(fn: AsyncRequestHandler): RequestHandler {
  return (req, res, next) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}

// usage — clean, no try/catch boilerplate
router.get(
  '/users/:id',
  asyncHandler(async (req, res) => {
    const user = await userService.findById(req.params.id);
    res.json(user);
  })
);
```

### After (deslopped) — Option C: Express 5 (async-native)

```typescript
// Express 5 (npm install express@5) handles async errors natively
// No asyncHandler wrapper needed; thrown errors are forwarded automatically
router.get('/users/:id', async (req, res) => {
  const user = await userService.findById(req.params.id);
  res.json(user);
});
```

**Safety notes**
- Check your Express major version. Express 4 requires manual forwarding. Express 5 (stable since 2024) handles it automatically.
- The `asyncHandler` wrapper is the most portable solution across Express 4 and 5.
- Fastify: async handlers always propagate rejections to the error handler — no wrapper needed.

---

## 15. Global State Mutation in Middleware

**Risk: 4 / 5**

AI mutates module-level variables inside middleware to "share" state across requests. In a concurrent server, this creates race conditions where one request overwrites state being read by another.

### Before (AI-generated)

```typescript
// middleware/context.ts
let currentUser: User | null = null; // GLOBAL — shared across all concurrent requests

export function authMiddleware(req: Request, res: Response, next: NextFunction): void {
  const token = req.headers.authorization?.split(' ')[1];
  currentUser = verifyJwt(token); // request A overwrites while request B is reading
  next();
}

export function getCurrentUser(): User | null {
  return currentUser; // returns wrong user under concurrency
}
```

### After (deslopped) — attach to `req`

```typescript
// Augment Express Request type
declare global {
  namespace Express {
    interface Request {
      user?: User;
    }
  }
}

// middleware/auth.ts
export function authMiddleware(req: Request, res: Response, next: NextFunction): void {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) {
    return void res.status(401).json({ error: 'Unauthorized' });
  }
  try {
    req.user = verifyJwt(token); // scoped to this request object — safe
    next();
  } catch {
    res.status(401).json({ error: 'Invalid token' });
  }
}

// anywhere downstream in the same request chain
router.get('/profile', authMiddleware, (req, res) => {
  res.json(req.user); // safe — request-scoped
});
```

**Safety notes**
- Request-scoped state belongs on the `req` object. For more complex scenarios (e.g., multi-layered context not reachable via `req`), use `AsyncLocalStorage` from `node:async_hooks` — it provides true async-scoped context without global mutation.
- Fastify: use `request.local` or `fastify-plugin` context; avoid module-level mutable state for the same reasons.

---

## 16. Missing or Overly Permissive CORS

**Risk: 4 / 5**

AI either omits CORS configuration (browser requests fail) or uses `origin: '*'` with credentials enabled (which browsers reject) or allows all origins in production (security risk).

### Before (AI-generated)

```typescript
// Option A: no CORS at all — browsers cannot call the API
app.use(express.json());

// Option B: wildcard with credentials — browsers reject this combination
app.use(cors({ origin: '*', credentials: true }));
```

### After (deslopped)

```typescript
import cors from 'cors';

const ALLOWED_ORIGINS = (process.env.ALLOWED_ORIGINS ?? '')
  .split(',')
  .map((o) => o.trim())
  .filter(Boolean);

app.use(
  cors({
    origin: (origin, callback) => {
      // Allow server-to-server requests (no origin) and listed origins
      if (!origin || ALLOWED_ORIGINS.includes(origin)) {
        callback(null, true);
      } else {
        callback(new Error(`CORS: origin '${origin}' not allowed`));
      }
    },
    credentials: true,           // required for cookies / Authorization header
    methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Request-ID'],
    maxAge: 86400,               // preflight cache in seconds
  })
);

// Handle OPTIONS preflight explicitly before auth middleware
app.options('*', cors());
```

```
# .env
ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
```

**Safety notes**
- `credentials: true` and `origin: '*'` cannot be used together — the browser will reject such responses (`Access-Control-Allow-Origin` cannot be `*` when `Access-Control-Allow-Credentials` is `true`).
- Always configure CORS from environment variables so the allowed list differs between development (`localhost:3000`) and production.
- Fastify: use `@fastify/cors` with identical options.

---

## 17. No Response Compression

**Risk: 2 / 5**

AI-generated servers send uncompressed JSON and HTML. Compression typically reduces payload size by 60–80%, directly improving time-to-first-byte and reducing egress cost.

### Before (AI-generated)

```typescript
const app = express();
app.use(express.json());
// No compression — all responses sent uncompressed
```

### After (deslopped)

```typescript
import compression from 'compression';

app.use(
  compression({
    level: 6,             // balanced CPU vs compression ratio (default)
    threshold: 1024,      // only compress responses larger than 1 KB
    filter: (req, res) => {
      // Skip compression for Server-Sent Events and already-compressed formats
      if (req.headers['accept'] === 'text/event-stream') return false;
      return compression.filter(req, res);
    },
  })
);
```

**For Brotli (Node 18+):**

```typescript
import zlib from 'node:zlib';
import shrinkRay from 'shrink-ray-current'; // brotli + zopfli

app.use(shrinkRay({ brotli: { quality: 4 } }));
```

**Safety notes**
- Compression adds CPU overhead. For high-throughput APIs serving a reverse proxy, consider offloading compression to nginx (`gzip on; gzip_types application/json;`) and disabling it in Node.
- Never compress streaming responses unless you buffer the full stream first — this defeats the purpose of streaming.
- Fastify: use `@fastify/compress` which supports brotli, gzip, and deflate with content negotiation via `Accept-Encoding`.

---

## 18. Leaking Internal Error Details to Clients

**Risk: 5 / 5**

AI passes raw `Error` objects or stack traces directly into API responses, exposing file paths, library versions, SQL queries, and internal architecture to attackers.

### Before (AI-generated)

```typescript
router.post('/login', async (req, res) => {
  try {
    const user = await userService.login(req.body.email, req.body.password);
    res.json(user);
  } catch (err) {
    // Sends full stack trace to client
    res.status(500).json({ error: err.message, stack: err.stack });
  }
});
```

### After (deslopped)

```typescript
// Central error handler in app.ts — one place, consistent behaviour
app.use((err: unknown, req: Request, res: Response, _next: NextFunction) => {
  if (err instanceof AppError) {
    // Known, intentionally thrown errors — safe to surface message
    logger.warn({ err, requestId: req.requestId }, 'Application error');
    return res.status(err.statusCode).json({ error: err.message });
  }

  // Unknown errors — log everything, send nothing sensitive
  logger.error({ err, requestId: req.requestId }, 'Unexpected error');

  // In development, include the stack for easier debugging
  const body: Record<string, unknown> = { error: 'Internal server error' };
  if (process.env.NODE_ENV === 'development') {
    body.debug = err instanceof Error ? err.stack : String(err);
  }

  res.status(500).json(body);
});
```

**Safety notes**
- SQL errors often contain table names, column names, and query fragments. Never surface them to clients.
- Use a correlation/request ID in error responses so clients can report it and you can look it up in logs: `{ error: 'Internal server error', requestId: 'uuid' }`.
- Fastify: customise `fastify.setErrorHandler()`. Fastify exposes `error.validation` for schema errors; sanitise before returning.

---

## 19. Not Using `router.param()` for Common Param Resolution

**Risk: 2 / 5**

AI repeats the same `findById` lookup in every route handler that uses the same URL parameter, duplicating error handling and adding noise.

### Before (AI-generated)

```typescript
router.get('/users/:userId', async (req, res, next) => {
  try {
    const user = await userService.findById(req.params.userId);
    if (!user) return res.status(404).json({ error: 'User not found' });
    res.json(user);
  } catch (err) { next(err); }
});

router.put('/users/:userId', async (req, res, next) => {
  try {
    const user = await userService.findById(req.params.userId); // duplicated
    if (!user) return res.status(404).json({ error: 'User not found' });
    const updated = await userService.update(user.id, req.body);
    res.json(updated);
  } catch (err) { next(err); }
});
```

### After (deslopped)

```typescript
// Resolve :userId once; attach to req; all handlers below use req.resolvedUser
router.param('userId', async (req: Request, res: Response, next: NextFunction, id: string) => {
  try {
    const user = await userService.findById(id);
    if (!user) return void res.status(404).json({ error: 'User not found' });
    req.resolvedUser = user; // attach to request — type-augment Express.Request
    next();
  } catch (err) {
    next(err);
  }
});

router.get('/users/:userId', (req, res) => {
  res.json(req.resolvedUser); // already resolved
});

router.put('/users/:userId', asyncHandler(async (req, res) => {
  const updated = await userService.update(req.resolvedUser!.id, req.body);
  res.json(updated);
}));
```

**Safety notes**
- `router.param()` runs once per unique param name per request, regardless of how many routes match.
- This pattern is Express-specific. Fastify achieves the same result with `preHandler` hooks scoped to a plugin or individual routes.

---

## 20. Circular `require()` / Dependency Cycles Between Modules

**Risk: 3 / 5**

AI imports module A in module B and module B in module A. Node.js handles circular CommonJS requires by returning a partially initialised export object, causing `TypeError: X is not a function` at runtime — typically only on the first require cycle hit.

### Before (AI-generated)

```typescript
// services/order.service.ts
import { UserService } from './user.service'; // imports user
// ...

// services/user.service.ts
import { OrderService } from './order.service'; // imports order → cycle
// ...
```

### After (deslopped) — break the cycle

**Strategy 1: Extract shared dependency to a third module**

```typescript
// repositories/user.repository.ts  ← no imports from services
// repositories/order.repository.ts ← no imports from services

// services/user.service.ts
import { userRepository } from '../repositories/user.repository';
// No import from order.service

// services/order.service.ts
import { orderRepository } from '../repositories/order.repository';
import { userRepository } from '../repositories/user.repository';
// No import from user.service
```

**Strategy 2: Dependency injection (inversion of control)**

```typescript
// services/order.service.ts
export class OrderService {
  constructor(
    private readonly orderRepo: OrderRepository,
    private readonly userRepo: UserRepository // injected — no direct import of UserService
  ) {}
}
```

**Strategy 3: Lazy import (last resort)**

```typescript
// Only inside a function, after modules have fully loaded
async function getRelatedOrders(userId: string) {
  const { OrderService } = await import('./order.service'); // deferred
  // ...
}
```

**Safety notes**
- Use `madge` or `dependency-cruiser` in CI to detect cycles: `madge --circular src/`.
- Circular dependencies in ESM (`import`) cause `ReferenceError` (live bindings not yet initialised), which is harder to debug than CJS cycles.
- Fastify plugin architecture naturally avoids cycles because plugins are registered sequentially and dependencies are declared via `fastify-plugin`'s `dependencies` option.

---

## Express Middleware Ordering Guide

This is the canonical order for a production Express application. Deviating from this order causes subtle bugs that only appear under specific conditions.

```
┌────────────────────────────────────────────────────────────────┐
│                      REQUEST ARRIVES                           │
└───────────────────────────┬────────────────────────────────────┘
                            │
              ┌─────────────▼──────────────┐
              │  1. helmet()               │  Security headers
              │     trust proxy config     │
              └─────────────┬──────────────┘
                            │
              ┌─────────────▼──────────────┐
              │  2. Request logger         │  Log before body parse
              └─────────────┬──────────────┘
                            │
              ┌─────────────▼──────────────┐
              │  3. cors()                 │  Handles OPTIONS preflight
              └─────────────┬──────────────┘
                            │
              ┌─────────────▼──────────────┐
              │  4. compression()          │  Before body parse
              └─────────────┬──────────────┘
                            │
              ┌─────────────▼──────────────┐
              │  5. express.json()         │  Body parsing
              │     express.urlencoded()   │
              └─────────────┬──────────────┘
                            │
              ┌─────────────▼──────────────┐
              │  6. Global rate limiter    │  Before auth (cheap check)
              └─────────────┬──────────────┘
                            │
              ┌─────────────▼──────────────┐
              │  7. Auth middleware        │  Token verification
              │     (scoped to /api)       │
              └─────────────┬──────────────┘
                            │
              ┌─────────────▼──────────────┐
              │  8. Route-level validators │  Zod / Joi schemas
              └─────────────┬──────────────┘
                            │
              ┌─────────────▼──────────────┐
              │  9. Route handler          │  Business logic via service
              └─────────────┬──────────────┘
                            │
              ┌─────────────▼──────────────┐
              │  10. 404 catch-all         │  After all routes
              └─────────────┬──────────────┘
                            │
              ┌─────────────▼──────────────┐
              │  11. Error handler         │  4-param, always last
              └────────────────────────────┘
```

**Rules:**
- `cors()` must run before auth so that preflight `OPTIONS` requests are answered without authentication.
- Rate limiting runs before auth so unauthenticated attackers are throttled before expensive JWT verification.
- Body parsing must precede any middleware that reads `req.body`.
- The 404 handler must come after all routes; the error handler must come last.
- Never place `express.static()` before authentication if the static files are protected.

---

## Fastify vs Express: Pattern Applicability Matrix

| # | Anti-Pattern | Express | Fastify | Notes |
|---|---|---|---|---|
| 1 | Business logic in route handler | Yes | Yes | Universal; framework-agnostic |
| 2 | Missing error middleware | Yes — explicit `app.use(err, req, res, next)` | Partial — `setErrorHandler` needed but async errors auto-caught | Fastify catches async errors; sync throws still need handler |
| 3 | Callback pyramid | Yes | Yes | Both support async natively |
| 4 | No input validation | Yes | Partial — Fastify validates JSON Schema by default; Zod adapter available | Fastify's built-in schema validation removes this risk for body/query |
| 5 | Sync blocking | Yes | Yes | Event loop is shared regardless of framework |
| 6 | Missing timeout | Yes | Yes — use `connectionTimeout`, `requestTimeout` options | Fastify has built-in options; Express needs manual middleware |
| 7 | Middleware ordering | Yes | Partial — Fastify uses lifecycle hooks (`onRequest`, `preHandler`, etc.) with explicit ordering | Lifecycle hooks are less error-prone than Express's linear stack |
| 8 | God router | Yes | Yes | Service layer separation is universal |
| 9 | Secrets in code | Yes | Yes | Universal |
| 10 | No graceful shutdown | Yes | Partial — `fastify.close()` handles hooks; still need SIGTERM listener | Fastify's `close()` is more ergonomic |
| 11 | console.log | Yes | Yes | pino is Fastify's default logger; configure, don't replace |
| 12 | Rate limit / auth ordering | Yes | Partial — `@fastify/rate-limit` integrates with lifecycle; ordering via hook stage | Hook stage (`onRequest` vs `preHandler`) determines order |
| 13 | require() in functions | Yes | Yes | Node.js module system issue |
| 14 | Unhandled promise rejections | Critical in Express 4; fixed in Express 5 | Not applicable — Fastify catches async rejections automatically | Upgrade to Express 5 or use asyncHandler |
| 15 | Global state mutation | Yes | Yes | Universal concurrency issue |
| 16 | Missing/permissive CORS | Yes | Yes — `@fastify/cors` | Same concept, different package |
| 17 | No compression | Yes | Yes — `@fastify/compress` | Similar; Fastify compresses more efficiently |
| 18 | Leaking error details | Yes | Yes | Universal |
| 19 | No router.param() | Yes | Not applicable — use `preHandler` hooks in Fastify | Fastify does not have `param()` |
| 20 | Circular dependencies | Yes | Yes | Node.js module system issue |

---

## Recommended Project Layout

A clean layout enforces layer separation, prevents circular dependencies, and makes each anti-pattern above structurally impossible when followed consistently.

```
src/
├── app.ts                    # Express/Fastify app factory (no server.listen here)
├── server.ts                 # Entry point: listen, SIGTERM, uncaughtException
├── config/
│   └── env.ts                # Zod-validated env schema (pattern 9)
├── routes/                   # HTTP layer only: parse → validate → call service → respond
│   ├── index.ts              # Router aggregator
│   ├── users.ts
│   ├── orders.ts
│   └── auth.ts
├── middleware/               # Reusable Express middleware
│   ├── auth.ts               # JWT verification → req.user
│   ├── validate.ts           # Zod body/query/param validators
│   ├── rateLimiter.ts        # Rate limit configs
│   ├── requestLogger.ts      # pino child logger per request
│   └── errorHandler.ts       # Central 4-param error handler
├── services/                 # Business logic, orchestration (no req/res)
│   ├── user.service.ts
│   ├── order.service.ts
│   └── auth.service.ts
├── repositories/             # Data access only (DB queries, Redis)
│   ├── user.repository.ts
│   └── order.repository.ts
├── clients/                  # External API wrappers
│   ├── stripe.client.ts
│   └── email.client.ts
├── schemas/                  # Zod schemas (shared by routes and services)
│   ├── user.schema.ts
│   └── order.schema.ts
├── errors/                   # Typed error classes
│   └── index.ts
├── logger.ts                 # pino/winston instance
└── types/                    # Global type augmentations
    └── express.d.ts          # Augment Express.Request (req.user, req.log, etc.)
```

**Key constraints enforced by this layout:**
- `routes/` never imports from `repositories/` — all data access goes through `services/`.
- `services/` never imports from `routes/` or `middleware/` — no HTTP primitives.
- `repositories/` never imports from `services/` — no circular data access.
- `clients/` knows nothing about the application domain — pure API wrappers.
- `errors/` is a leaf node — imported by everyone, imports nothing from the application.

```typescript
// types/express.d.ts — augment once, use everywhere
import { User } from '../services/user.service';
import { Logger } from 'pino';

declare global {
  namespace Express {
    interface Request {
      user?: User;
      log: Logger;
      requestId: string;
      resolvedUser?: User;
    }
  }
}
```

---

*Reference maintained for the Code Deslopper skill. Update when new anti-patterns are identified or framework versions introduce native solutions.*
