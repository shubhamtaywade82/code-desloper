# Next.js 13/14/15 App Router Anti-Patterns Reference

> Reference for the Code Deslopper skill. Covers AI-generated Next.js code that compiles but ships performance bugs, unnecessary client-side JavaScript, broken caching, or security gaps.

---

## Table of Contents

1. [`"use client"` Overuse](#1-use-client-overuse)
2. [Data Fetching in Client Components](#2-data-fetching-in-client-components)
3. [Missing `loading.tsx` / `error.tsx`](#3-missing-loadingtsx--errortsx)
4. [`useEffect` + `fetch` Instead of Server Component Fetch](#4-useeffect--fetch-instead-of-server-component-fetch)
5. [Mixing `pages/` and `app/` Router Conventions](#5-mixing-pages-and-app-router-conventions)
6. [Not Using `generateStaticParams`](#6-not-using-generatestaticparams)
7. [Not Using `revalidate` / `cache` on `fetch`](#7-not-using-revalidate--cache-on-fetch)
8. [`layout.tsx` Doing Too Much](#8-layouttsx-doing-too-much)
9. [Prop-Drilling Server Data Instead of Co-locating Fetches](#9-prop-drilling-server-data-instead-of-co-locating-fetches)
10. [Not Using Parallel / Intercepting Routes](#10-not-using-parallel--intercepting-routes)
11. [Client-Side State for URL-Owned Data](#11-client-side-state-for-url-owned-data)
12. [`cookies()` / `headers()` Called in Wrong Context](#12-cookies--headers-called-in-wrong-context)
13. [Missing `Suspense` Boundaries Around Async Server Components](#13-missing-suspense-boundaries-around-async-server-components)
14. [`router.push` Instead of `<Link>`](#14-routerpush-instead-of-link)
15. [Not Using Next.js `<Image>`](#15-not-using-nextjs-image)
16. [API Routes (`route.ts`) Containing Business Logic](#16-api-routes-routets-containing-business-logic)
17. [Missing `metadata` Exports](#17-missing-metadata-exports)
18. [Server Actions Misuse](#18-server-actions-misuse)
19. [Over-Fetching in `layout.tsx`](#19-over-fetching-in-layouttsx)
20. [Not Using `unstable_cache` / `cache()` for Repeated Server Data](#20-not-using-unstable_cache--cache-for-repeated-server-data)

---

## Decision Trees and Strategy Guides

- [Server vs Client Component Decision Tree](#server-vs-client-component-decision-tree)
- [When to Use `"use server"` vs `"use client"`](#when-to-use-use-server-vs-use-client)
- [Caching Strategy Guide](#caching-strategy-guide)

---

## Risk Score Key

| Score | Meaning |
|-------|---------|
| 1 | Minor: cosmetic / style concern |
| 2 | Low: small performance or DX issue |
| 3 | Medium: measurable performance impact or maintenance burden |
| 4 | High: significant performance regression, bundle bloat, or incorrect behaviour |
| 5 | Critical: security vulnerability, data exposure, or broken functionality |

---

## 1. `"use client"` Overuse

**Risk: 4**

AI models default to adding `"use client"` at the top of every component because they were trained heavily on pre-App-Router React patterns. This forces the entire component subtree into the client bundle, adding kilobytes and eliminating server-side rendering benefits.

### Signs of the Problem

- `"use client"` at the top of a file that has no hooks, no event handlers, and no browser APIs.
- `"use client"` on a component that only renders static HTML or passes through props.
- Every file in `app/` starting with `"use client"`.

### Before (AI-generated)

```tsx
// app/about/page.tsx
"use client";

export default function AboutPage() {
  return (
    <main>
      <h1>About Us</h1>
      <p>We build software.</p>
    </main>
  );
}
```

```tsx
// app/components/UserCard.tsx
"use client";

interface Props {
  name: string;
  email: string;
}

export default function UserCard({ name, email }: Props) {
  return (
    <div className="card">
      <p>{name}</p>
      <p>{email}</p>
    </div>
  );
}
```

### After (corrected)

```tsx
// app/about/page.tsx
// No directive needed — this is a Server Component by default

export default function AboutPage() {
  return (
    <main>
      <h1>About Us</h1>
      <p>We build software.</p>
    </main>
  );
}
```

```tsx
// app/components/UserCard.tsx
// Server Component — no hooks, no events, pure rendering

interface Props {
  name: string;
  email: string;
}

export default function UserCard({ name, email }: Props) {
  return (
    <div className="card">
      <p>{name}</p>
      <p>{email}</p>
    </div>
  );
}
```

### Safety Notes

- Removing `"use client"` from a component that actually uses hooks will cause a build error — check for `useState`, `useEffect`, `useRef`, `useContext`, event handlers (`onClick`, `onChange`, etc.), and browser-only APIs (`window`, `document`, `localStorage`).
- If a Server Component imports a Client Component, that is fine — the Client Component boundary is respected at the import level.
- Third-party components that use hooks internally must be wrapped in a Client Component even if your code doesn't use hooks directly.

---

## 2. Data Fetching in Client Components

**Risk: 4**

AI frequently generates components that fetch data client-side with `useEffect`/`useState` or a client-side data-fetching library (SWR, React Query) when the data is not user-specific and could be fetched on the server, eliminating a waterfall and reducing bundle size.

### Before (AI-generated)

```tsx
"use client";

import { useEffect, useState } from "react";

interface Product {
  id: string;
  name: string;
  price: number;
}

export default function ProductList() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/products")
      .then((r) => r.json())
      .then((data) => {
        setProducts(data);
        setLoading(false);
      });
  }, []);

  if (loading) return <p>Loading...</p>;

  return (
    <ul>
      {products.map((p) => (
        <li key={p.id}>{p.name} — ${p.price}</li>
      ))}
    </ul>
  );
}
```

### After (corrected)

```tsx
// app/products/page.tsx — Server Component, no directive needed

interface Product {
  id: string;
  name: string;
  price: number;
}

async function getProducts(): Promise<Product[]> {
  const res = await fetch("https://api.example.com/products", {
    next: { revalidate: 60 }, // ISR: revalidate every 60 seconds
  });

  if (!res.ok) throw new Error("Failed to fetch products");
  return res.json();
}

export default async function ProductList() {
  const products = await getProducts();

  return (
    <ul>
      {products.map((p) => (
        <li key={p.id}>{p.name} — ${p.price}</li>
      ))}
    </ul>
  );
}
```

### Safety Notes

- Client-side fetching with SWR/React Query is still appropriate when data must be real-time, user-specific per-session, or mutated optimistically.
- Server Component fetch runs at request time (or build time for static routes) — it does not run in the browser.
- If the endpoint requires credentials that only exist in the browser session, client-side fetching may be necessary.

---

## 3. Missing `loading.tsx` / `error.tsx`

**Risk: 3**

AI often generates page files without the companion `loading.tsx` and `error.tsx` files. Without these, users see no feedback during data loading and get unhandled React errors instead of graceful fallbacks.

### Before (AI-generated)

```
app/
  dashboard/
    page.tsx      ← async server component, no streaming
```

```tsx
// app/dashboard/page.tsx
export default async function DashboardPage() {
  const data = await fetchDashboardData(); // slow fetch, no boundary
  return <Dashboard data={data} />;
}
```

### After (corrected)

```
app/
  dashboard/
    page.tsx
    loading.tsx   ← shown while page.tsx suspends
    error.tsx     ← shown when page.tsx throws
```

```tsx
// app/dashboard/loading.tsx
export default function DashboardLoading() {
  return (
    <div aria-busy="true" aria-label="Loading dashboard">
      <div className="skeleton" />
      <div className="skeleton" />
    </div>
  );
}
```

```tsx
// app/dashboard/error.tsx
"use client"; // error boundaries must be Client Components

interface Props {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function DashboardError({ error, reset }: Props) {
  return (
    <div role="alert">
      <h2>Something went wrong loading the dashboard.</h2>
      <p>{error.message}</p>
      <button onClick={reset}>Try again</button>
    </div>
  );
}
```

```tsx
// app/dashboard/page.tsx — unchanged, Next.js wires boundaries automatically
export default async function DashboardPage() {
  const data = await fetchDashboardData();
  return <Dashboard data={data} />;
}
```

### Safety Notes

- `error.tsx` must be a Client Component (`"use client"`) because React error boundaries are implemented as class components internally.
- `loading.tsx` wraps the page in a `<Suspense>` automatically — you do not need to add `<Suspense>` to the page itself for this basic streaming case.
- `error.tsx` does not catch errors thrown during rendering in `layout.tsx` at the same level — add a separate `error.tsx` one level up or use `global-error.tsx` for root layout errors.

---

## 4. `useEffect` + `fetch` Instead of Server Component Fetch

**Risk: 4**

This is the most common AI pattern. It creates a client-side waterfall: browser downloads JS bundle, mounts component, fires fetch, waits for response, then renders. A server component eliminates the first three steps.

### Before (AI-generated)

```tsx
"use client";

import { useEffect, useState } from "react";

export default function UserProfile({ userId }: { userId: string }) {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    fetch(`/api/users/${userId}`)
      .then((r) => r.json())
      .then(setUser);
  }, [userId]);

  if (!user) return <p>Loading user...</p>;
  return <div>{user.name}</div>;
}
```

### After (corrected)

```tsx
// app/users/[id]/page.tsx — Server Component
import { notFound } from "next/navigation";

interface Props {
  params: { id: string };
}

async function getUser(id: string): Promise<User> {
  const res = await fetch(`https://api.example.com/users/${id}`, {
    next: { revalidate: 300 },
  });
  if (res.status === 404) notFound();
  if (!res.ok) throw new Error("Failed to fetch user");
  return res.json();
}

export default async function UserProfile({ params }: Props) {
  const user = await getUser(params.id);
  return <div>{user.name}</div>;
}
```

### Safety Notes

- `notFound()` throws a Next.js-specific error that renders the `not-found.tsx` file — use it instead of returning `null` or a 404 message inline.
- The `useEffect` pattern is still appropriate for data that changes after mount based on user interaction (e.g., live search results, WebSocket data).
- When converting, check whether the fetch uses browser-only auth tokens (e.g., tokens from `localStorage`) — those cannot move to the server as-is.

---

## 5. Mixing `pages/` and `app/` Router Conventions

**Risk: 5**

AI trained on older Next.js examples generates `pages/` patterns inside `app/` or vice versa. This causes silent misrouting, broken data fetching, or build errors.

### Before (AI-generated — wrong conventions in `app/`)

```tsx
// app/dashboard/page.tsx — using pages/ patterns inside app/
import { GetServerSideProps } from "next"; // WRONG: pages/ API

export const getServerSideProps: GetServerSideProps = async (ctx) => {
  const data = await fetchData();
  return { props: { data } };
};

export default function Dashboard({ data }: { data: Data }) {
  return <div>{data.title}</div>;
}
```

```tsx
// app/api/users/route.ts — but file is inside pages/api/
// pages/api/users.ts — using app/ Response API
export default function handler(req: Request, res: Response) {
  return Response.json({ users: [] }); // WRONG: app/ API in pages/ handler
}
```

### After (corrected — consistent `app/` conventions)

```tsx
// app/dashboard/page.tsx — app/ Server Component pattern
async function fetchData(): Promise<Data> {
  const res = await fetch("https://api.example.com/data", {
    next: { revalidate: 60 },
  });
  return res.json();
}

export default async function Dashboard() {
  const data = await fetchData();
  return <div>{data.title}</div>;
}
```

```tsx
// app/api/users/route.ts — correct app/ Route Handler
import { NextResponse } from "next/server";

export async function GET() {
  const users = await getUsers();
  return NextResponse.json({ users });
}
```

### Safety Notes

- `getServerSideProps`, `getStaticProps`, and `getStaticPaths` are **`pages/` only** — they are ignored silently in `app/`.
- `pages/api/` handlers use `(req: NextApiRequest, res: NextApiResponse)` — app/ Route Handlers use `(request: Request)` and return `Response`.
- During migration, both routers can coexist. A route in `app/` takes precedence over the same path in `pages/`.
- Check `next.config.js` for `experimental.appDir` — in Next.js 13.4+ it is enabled by default; in older versions it must be opted in.

---

## 6. Not Using `generateStaticParams`

**Risk: 3**

AI generates dynamic routes without `generateStaticParams`, causing every request to be server-rendered at runtime even when the set of possible params is known at build time.

### Before (AI-generated)

```tsx
// app/blog/[slug]/page.tsx — always dynamic, never pre-rendered
export default async function BlogPost({
  params,
}: {
  params: { slug: string };
}) {
  const post = await getPost(params.slug);
  return <article>{post.content}</article>;
}
```

### After (corrected)

```tsx
// app/blog/[slug]/page.tsx
import { notFound } from "next/navigation";

export async function generateStaticParams() {
  const posts = await getPosts(); // fetched once at build time
  return posts.map((post) => ({ slug: post.slug }));
}

// Optional: control behaviour for slugs not returned by generateStaticParams
export const dynamicParams = false; // 404 for unknown slugs (default: true)

export default async function BlogPost({
  params,
}: {
  params: { slug: string };
}) {
  const post = await getPost(params.slug);
  if (!post) notFound();
  return <article>{post.content}</article>;
}
```

### Safety Notes

- `generateStaticParams` replaces `getStaticPaths` from the `pages/` router.
- Set `dynamicParams = false` if you want a hard 404 for any slug not generated at build time.
- Set `dynamicParams = true` (default) to fall back to SSR for slugs not pre-generated — useful for large content sets.
- For nested dynamic segments, return an array of objects with all required param keys.

---

## 7. Not Using `revalidate` / `cache` on `fetch`

**Risk: 4**

AI-generated server fetches often omit cache options entirely. In Next.js 15, the default changed from `force-cache` (Next.js 13/14) to `no-store` (Next.js 15), meaning every request re-fetches unless told otherwise. In 13/14, the opposite risk exists: data is cached forever unintentionally.

### Before (AI-generated — no cache config)

```tsx
// Fetches on every request in Next.js 15 (no-store default)
// or caches forever in Next.js 13/14 (force-cache default)
async function getProducts() {
  const res = await fetch("https://api.example.com/products");
  return res.json();
}
```

### After — Static Data (rare updates)

```tsx
async function getProducts() {
  const res = await fetch("https://api.example.com/products", {
    cache: "force-cache", // explicitly static — only changes on redeploy
  });
  if (!res.ok) throw new Error("Failed to fetch");
  return res.json();
}
```

### After — Incrementally Revalidated Data

```tsx
async function getProducts() {
  const res = await fetch("https://api.example.com/products", {
    next: { revalidate: 3600 }, // revalidate at most once per hour
  });
  if (!res.ok) throw new Error("Failed to fetch");
  return res.json();
}
```

### After — Tag-Based Revalidation

```tsx
async function getProduct(id: string) {
  const res = await fetch(`https://api.example.com/products/${id}`, {
    next: { tags: [`product-${id}`] }, // revalidate on demand via revalidateTag()
  });
  if (!res.ok) throw new Error("Failed to fetch");
  return res.json();
}

// In a Server Action or Route Handler triggered by a webhook:
import { revalidateTag } from "next/cache";
revalidateTag(`product-${id}`);
```

### After — Always Dynamic

```tsx
async function getCurrentUser() {
  const res = await fetch("https://api.example.com/me", {
    cache: "no-store", // always fetch fresh — for user-specific data
  });
  if (!res.ok) throw new Error("Failed to fetch");
  return res.json();
}
```

### Safety Notes

- In Next.js 15, the default is `no-store`. In 13/14, it was `force-cache`. Always be explicit.
- `next: { revalidate: 0 }` is equivalent to `cache: "no-store"`.
- Route segment config (`export const revalidate = 60`) sets the default for all fetches in a segment — individual fetch options override this.
- `revalidatePath()` clears the Next.js cache for a path; `revalidateTag()` targets tagged fetches specifically.

---

## 8. `layout.tsx` Doing Too Much

**Risk: 3**

AI frequently puts data fetching, business logic, authentication checks, and heavy computation inside `layout.tsx`. Layouts are persistent across navigation and should be lightweight shells.

### Before (AI-generated)

```tsx
// app/dashboard/layout.tsx
import { getUser } from "@/lib/auth";
import { getNotifications } from "@/lib/notifications";
import { getSubscription } from "@/lib/billing";
import { getFeatureFlags } from "@/lib/features";
import { redirect } from "next/navigation";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const user = await getUser();
  if (!user) redirect("/login");

  // Heavy fetches that run on every navigation within the layout
  const notifications = await getNotifications(user.id);
  const subscription = await getSubscription(user.id);
  const flags = await getFeatureFlags(user.id);

  // Complex business logic in layout
  const isTrialing = subscription.status === "trialing";
  const trialDaysLeft = Math.floor(
    (subscription.trialEnd - Date.now()) / 86400000
  );

  return (
    <div>
      <nav>
        <NotificationBell count={notifications.unread} />
        {isTrialing && <TrialBanner daysLeft={trialDaysLeft} />}
      </nav>
      {children}
    </div>
  );
}
```

### After (corrected)

```tsx
// app/dashboard/layout.tsx — minimal, focused on structure
import { verifySession } from "@/lib/auth";
import { redirect } from "next/navigation";
import { Suspense } from "react";
import { NotificationBell } from "./NotificationBell";
import { TrialBanner } from "./TrialBanner";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Auth check is appropriate in layout — it gates the entire section
  const session = await verifySession();
  if (!session) redirect("/login");

  return (
    <div>
      <nav>
        {/* Each component fetches its own data independently */}
        <Suspense fallback={null}>
          <NotificationBell userId={session.userId} />
        </Suspense>
        <Suspense fallback={null}>
          <TrialBanner userId={session.userId} />
        </Suspense>
      </nav>
      {children}
    </div>
  );
}
```

```tsx
// app/dashboard/NotificationBell.tsx — Server Component, fetches own data
import { getNotifications } from "@/lib/notifications";

export async function NotificationBell({ userId }: { userId: string }) {
  const notifications = await getNotifications(userId);
  return <button aria-label={`${notifications.unread} unread`}>🔔</button>;
}
```

```tsx
// app/dashboard/TrialBanner.tsx — Server Component, fetches own data
import { getSubscription } from "@/lib/billing";

export async function TrialBanner({ userId }: { userId: string }) {
  const sub = await getSubscription(userId);
  if (sub.status !== "trialing") return null;

  const daysLeft = Math.floor((sub.trialEnd - Date.now()) / 86400000);
  return <div className="banner">Trial ends in {daysLeft} days</div>;
}
```

### Safety Notes

- Auth guards (session checks + redirects) are appropriate in `layout.tsx`.
- Data needed by all children can be fetched in layout but should use caching — do not fetch uncached user-specific data that changes per request.
- Layouts do not re-mount on navigation between children — they persist. This is intentional, not a bug.

---

## 9. Prop-Drilling Server Data Instead of Co-locating Fetches

**Risk: 3**

AI generates a top-level component that fetches all data and drills it down through props, mimicking old React patterns. With Server Components, each component can fetch its own data without a performance penalty.

### Before (AI-generated)

```tsx
// app/page.tsx — fetches everything, drills it down
export default async function HomePage() {
  const [user, posts, trending, recommendations] = await Promise.all([
    getUser(),
    getPosts(),
    getTrending(),
    getRecommendations(),
  ]);

  return (
    <main>
      <Header user={user} />
      <PostFeed posts={posts} user={user} />
      <Sidebar trending={trending} recommendations={recommendations} user={user} />
    </main>
  );
}
```

### After (corrected)

```tsx
// app/page.tsx — each component is responsible for its own data
import { Suspense } from "react";

export default function HomePage() {
  return (
    <main>
      <Suspense fallback={<HeaderSkeleton />}>
        <Header />
      </Suspense>
      <Suspense fallback={<FeedSkeleton />}>
        <PostFeed />
      </Suspense>
      <Suspense fallback={<SidebarSkeleton />}>
        <Sidebar />
      </Suspense>
    </main>
  );
}
```

```tsx
// app/components/Header.tsx — Server Component, fetches own data
export async function Header() {
  const user = await getUser(); // cached — same request deduplication
  return <header>Welcome, {user.name}</header>;
}
```

```tsx
// app/components/PostFeed.tsx — Server Component, fetches own data
export async function PostFeed() {
  const posts = await getPosts();
  return <ul>{posts.map((p) => <PostCard key={p.id} post={p} />)}</ul>;
}
```

### Safety Notes

- Next.js deduplicates `fetch` calls with the same URL and options within a single request — calling `getUser()` in three components does not result in three HTTP requests.
- For non-`fetch` data sources (database, ORM), use React's `cache()` function to deduplicate: `const getUser = cache(async () => db.user.findFirst())`.
- Prop-drilling is still appropriate when the parent genuinely owns the data (e.g., a form that needs to pass field values to children).

---

## 10. Not Using Parallel / Intercepting Routes

**Risk: 2**

AI generates modal-like UIs as client-side state (`useState` controlling visibility) when Next.js App Router has first-class support for modals that preserve URL, work with the browser back button, and render the background page simultaneously.

### Before (AI-generated — modal as client state)

```tsx
"use client";

import { useState } from "react";

export default function PhotoGallery({ photos }: { photos: Photo[] }) {
  const [selected, setSelected] = useState<Photo | null>(null);

  return (
    <div>
      {photos.map((p) => (
        <img key={p.id} src={p.url} onClick={() => setSelected(p)} />
      ))}
      {selected && (
        <div className="modal">
          <img src={selected.url} />
          <button onClick={() => setSelected(null)}>Close</button>
        </div>
      )}
    </div>
  );
}
```

### After (corrected — intercepting route modal)

```
app/
  gallery/
    page.tsx                    ← gallery grid
    @modal/
      (.)photos/[id]/
        page.tsx                ← modal shown over gallery
    photos/
      [id]/
        page.tsx                ← full photo page (direct navigation)
    layout.tsx                  ← renders both slot and children
```

```tsx
// app/gallery/layout.tsx
export default function GalleryLayout({
  children,
  modal,
}: {
  children: React.ReactNode;
  modal: React.ReactNode;
}) {
  return (
    <>
      {children}
      {modal}
    </>
  );
}
```

```tsx
// app/gallery/@modal/(.)photos/[id]/page.tsx
import { Modal } from "@/components/Modal";

export default async function PhotoModal({
  params,
}: {
  params: { id: string };
}) {
  const photo = await getPhoto(params.id);
  return (
    <Modal>
      <img src={photo.url} alt={photo.alt} />
    </Modal>
  );
}
```

### Safety Notes

- Intercepting routes use `(.)` for same level, `(..)` for one level up, `(..)(..)` for two levels up, `(...)` for root.
- This pattern is appropriate for: image lightboxes, login modals over the current page, shopping cart drawers, detail panels.
- It is NOT a replacement for simple UI toggles — use `useState` for dropdowns, tooltips, and accordions.

---

## 11. Client-Side State for URL-Owned Data

**Risk: 3**

AI stores filter, sort, and pagination state in `useState`, which breaks browser history, prevents sharing links, and loses state on page refresh. Search params are the correct owner for this kind of UI state.

### Before (AI-generated)

```tsx
"use client";

import { useState } from "react";

export default function ProductSearch() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [page, setPage] = useState(1);
  const [results, setResults] = useState<Product[]>([]);

  // useEffect + fetch chain omitted for brevity
}
```

### After (corrected)

```tsx
// app/products/page.tsx — Server Component reads search params from URL
interface Props {
  searchParams: {
    q?: string;
    category?: string;
    page?: string;
  };
}

export default async function ProductSearch({ searchParams }: Props) {
  const query = searchParams.q ?? "";
  const category = searchParams.category ?? "all";
  const page = Number(searchParams.page ?? "1");

  const results = await searchProducts({ query, category, page });

  return (
    <div>
      <SearchForm defaultQuery={query} defaultCategory={category} />
      <ProductGrid products={results.items} />
      <Pagination currentPage={page} totalPages={results.totalPages} />
    </div>
  );
}
```

```tsx
// app/products/SearchForm.tsx — Client Component, updates URL on submit
"use client";

import { useRouter, useSearchParams } from "next/navigation";

export function SearchForm({
  defaultQuery,
  defaultCategory,
}: {
  defaultQuery: string;
  defaultCategory: string;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const params = new URLSearchParams(searchParams);
    params.set("q", String(form.get("q") ?? ""));
    params.set("category", String(form.get("category") ?? "all"));
    params.set("page", "1");
    router.push(`/products?${params.toString()}`);
  }

  return (
    <form onSubmit={handleSubmit}>
      <input name="q" defaultValue={defaultQuery} />
      <select name="category" defaultValue={defaultCategory}>
        <option value="all">All</option>
        <option value="electronics">Electronics</option>
      </select>
      <button type="submit">Search</button>
    </form>
  );
}
```

### Safety Notes

- `searchParams` in Server Component page props is a plain object — it is not an instance of `URLSearchParams`.
- In Client Components, use `useSearchParams()` from `next/navigation`, not `window.location.search`.
- Accessing `searchParams` in a Server Component makes the page dynamically rendered (opts out of static generation).

---

## 12. `cookies()` / `headers()` Called in Wrong Context

**Risk: 5**

AI calls `cookies()` and `headers()` from `next/headers` inside Client Components, inside non-async functions, or outside of the server request lifecycle — all of which either cause build errors or silently return empty values.

### Before (AI-generated)

```tsx
// WRONG: cookies() called in a Client Component
"use client";

import { cookies } from "next/headers";

export default function ThemeToggle() {
  const theme = cookies().get("theme")?.value ?? "light"; // runtime error
  return <button>{theme}</button>;
}
```

```tsx
// WRONG: headers() called outside request context
// lib/config.ts — used at module initialization time
import { headers } from "next/headers";

const host = headers().get("host"); // undefined at module load
export const API_URL = `https://${host}/api`;
```

### After (corrected)

```tsx
// Server Component reads the cookie and passes the value to Client Component
// app/components/ThemeProvider.tsx — Server Component
import { cookies } from "next/headers";
import { ThemeToggle } from "./ThemeToggle";

export async function ThemeProvider() {
  const theme = (await cookies()).get("theme")?.value ?? "light";
  return <ThemeToggle initialTheme={theme} />;
}
```

```tsx
// app/components/ThemeToggle.tsx — Client Component receives value as prop
"use client";

import { useState } from "react";

export function ThemeToggle({ initialTheme }: { initialTheme: string }) {
  const [theme, setTheme] = useState(initialTheme);
  return <button onClick={() => setTheme(t => t === "light" ? "dark" : "light")}>{theme}</button>;
}
```

```tsx
// Correct: headers() used in async Server Component or Route Handler
// app/api/me/route.ts
import { headers } from "next/headers";

export async function GET() {
  const headersList = await headers();
  const auth = headersList.get("authorization");
  // ...
}
```

### Safety Notes

- In Next.js 15, `cookies()` and `headers()` return Promises — always `await` them.
- In Next.js 13/14, they were synchronous — `cookies()` not `await cookies()`. Check the target version.
- These APIs can only be used in Server Components, Server Actions, and Route Handlers.
- Never call them at module scope or in utility functions called during module initialization.

---

## 13. Missing `Suspense` Boundaries Around Async Server Components

**Risk: 3**

AI generates async Server Components without wrapping them in `<Suspense>`, preventing streaming and causing the entire page to wait for the slowest fetch.

### Before (AI-generated)

```tsx
// app/page.tsx — entire page blocks on all three fetches
export default async function HomePage() {
  return (
    <main>
      <HeroSection />     {/* fast */}
      <FeaturedPosts />   {/* slow — 800ms fetch, blocks everything */}
      <NewsletterBox />   {/* fast */}
    </main>
  );
}

// FeaturedPosts.tsx
export async function FeaturedPosts() {
  const posts = await getPosts(); // no Suspense above — blocks page render
  return <ul>{posts.map(p => <li key={p.id}>{p.title}</li>)}</ul>;
}
```

### After (corrected)

```tsx
// app/page.tsx — streams each section independently
import { Suspense } from "react";

export default function HomePage() {
  return (
    <main>
      <HeroSection />   {/* renders immediately, no async */}
      <Suspense fallback={<PostsSkeleton />}>
        <FeaturedPosts />   {/* streams in when ready */}
      </Suspense>
      <NewsletterBox />   {/* renders immediately */}
    </main>
  );
}
```

```tsx
// FeaturedPosts.tsx — async Server Component, same as before
export async function FeaturedPosts() {
  const posts = await getPosts();
  return <ul>{posts.map(p => <li key={p.id}>{p.title}</li>)}</ul>;
}
```

### After — Sequential Dependencies (avoid when possible)

```tsx
// When B depends on A's result, nest Suspense boundaries
export default function Page() {
  return (
    <Suspense fallback={<UserSkeleton />}>
      <UserSection />
    </Suspense>
  );
}

async function UserSection() {
  const user = await getUser();
  return (
    <>
      <UserProfile user={user} />
      <Suspense fallback={<PostsSkeleton />}>
        <UserPosts userId={user.id} />
      </Suspense>
    </>
  );
}
```

### Safety Notes

- `<Suspense>` boundaries must wrap the async component at the point where you want fallback to appear — not inside the async component itself.
- Server Components inside `<Suspense>` stream HTML to the client — they do not send JavaScript.
- For parallel independent fetches, use `Promise.all` inside a single async component rather than nesting Suspense unnecessarily.

---

## 14. `router.push` Instead of `<Link>`

**Risk: 2**

AI uses `useRouter().push()` for standard navigation — particularly for nav links and buttons that look like links. `<Link>` prefetches the destination on hover, participates in browser history correctly, and is accessible by default.

### Before (AI-generated)

```tsx
"use client";

import { useRouter } from "next/navigation";

export function NavBar() {
  const router = useRouter();

  return (
    <nav>
      <button onClick={() => router.push("/")}>Home</button>
      <button onClick={() => router.push("/about")}>About</button>
      <button onClick={() => router.push("/blog")}>Blog</button>
    </nav>
  );
}
```

### After (corrected)

```tsx
// No "use client" needed for a nav bar with only links
import Link from "next/link";

export function NavBar() {
  return (
    <nav>
      <Link href="/">Home</Link>
      <Link href="/about">About</Link>
      <Link href="/blog">Blog</Link>
    </nav>
  );
}
```

### When `router.push` Is Appropriate

```tsx
"use client";

import { useRouter } from "next/navigation";

export function LoginForm() {
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await login(/* ... */);
    router.push("/dashboard"); // redirect after async action — correct use
  }

  return <form onSubmit={handleSubmit}>{/* ... */}</form>;
}
```

### Safety Notes

- `router.push` is appropriate after form submissions, auth flows, and programmatic redirects.
- For links that should open in a new tab: `<Link href="..." target="_blank" rel="noopener noreferrer">`.
- `<Link>` prefetching can be disabled with `prefetch={false}` for links behind auth or to heavy pages.

---

## 15. Not Using Next.js `<Image>`

**Risk: 3**

AI generates `<img>` tags directly. Next.js `<Image>` handles lazy loading, format conversion (WebP/AVIF), responsive sizes, and prevents layout shift — all automatically.

### Before (AI-generated)

```tsx
export function Avatar({ src, name }: { src: string; name: string }) {
  return <img src={src} alt={name} width={64} height={64} />;
}
```

```tsx
export function HeroBanner() {
  return (
    <img
      src="/hero.jpg"
      alt="Hero image"
      style={{ width: "100%", height: "400px" }}
    />
  );
}
```

### After (corrected)

```tsx
import Image from "next/image";

export function Avatar({ src, name }: { src: string; name: string }) {
  return (
    <Image
      src={src}
      alt={name}
      width={64}
      height={64}
      className="rounded-full"
    />
  );
}
```

```tsx
import Image from "next/image";

export function HeroBanner() {
  return (
    <div style={{ position: "relative", height: 400 }}>
      <Image
        src="/hero.jpg"
        alt="Hero image"
        fill
        priority          // LCP image — skip lazy loading
        sizes="100vw"
        style={{ objectFit: "cover" }}
      />
    </div>
  );
}
```

### Safety Notes

- External image domains must be listed in `next.config.js` under `images.remotePatterns`.
- Use `priority` on the LCP image (the largest image visible above the fold) — do not use it on all images.
- `fill` requires the parent container to have `position: relative` and an explicit height.
- For images with unknown dimensions at build time (user avatars, CMS images), use `fill` + `sizes` or pass explicit `width` and `height` props.

---

## 16. API Routes (`route.ts`) Containing Business Logic

**Risk: 4**

AI writes all database queries, validation, and business rules directly inside Route Handlers. This makes logic untestable, unreusable, and couples HTTP concerns to business concerns.

### Before (AI-generated)

```tsx
// app/api/orders/route.ts — business logic inside Route Handler
import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

export async function POST(request: NextRequest) {
  const body = await request.json();

  if (!body.items || body.items.length === 0) {
    return NextResponse.json({ error: "No items" }, { status: 400 });
  }

  const user = await db.user.findUnique({ where: { id: body.userId } });
  if (!user) return NextResponse.json({ error: "User not found" }, { status: 404 });

  const inventory = await db.product.findMany({
    where: { id: { in: body.items.map((i: any) => i.productId) } },
  });

  // 50 more lines of business logic...
  const total = inventory.reduce((sum, p) => sum + p.price, 0);
  const order = await db.order.create({ data: { userId: body.userId, total } });

  return NextResponse.json({ orderId: order.id });
}
```

### After (corrected)

```tsx
// lib/orders/createOrder.ts — pure business logic, testable
import { z } from "zod";
import { db } from "@/lib/db";

const CreateOrderSchema = z.object({
  userId: z.string().cuid(),
  items: z.array(z.object({ productId: z.string().cuid(), quantity: z.number().int().positive() })).min(1),
});

export type CreateOrderInput = z.infer<typeof CreateOrderSchema>;

export async function createOrder(input: CreateOrderInput) {
  const validated = CreateOrderSchema.parse(input);

  const user = await db.user.findUnique({ where: { id: validated.userId } });
  if (!user) throw new Error("USER_NOT_FOUND");

  // Business logic lives here, not in the route handler
  const order = await db.order.create({ data: { userId: validated.userId } });
  return order;
}
```

```tsx
// app/api/orders/route.ts — thin HTTP adapter
import { NextRequest, NextResponse } from "next/server";
import { createOrder } from "@/lib/orders/createOrder";
import { getSession } from "@/lib/auth";

export async function POST(request: NextRequest) {
  const session = await getSession(request);
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  try {
    const order = await createOrder(body as any);
    return NextResponse.json({ orderId: order.id }, { status: 201 });
  } catch (err) {
    if (err instanceof Error && err.message === "USER_NOT_FOUND") {
      return NextResponse.json({ error: "User not found" }, { status: 404 });
    }
    throw err; // let Next.js handle unexpected errors
  }
}
```

### Safety Notes

- Route Handlers should only handle: parsing the request, calling service functions, mapping errors to HTTP responses, and returning a response.
- Consider using Server Actions instead of API routes for form submissions and mutations from React components — they are simpler and type-safe end-to-end.
- Always validate input with Zod or equivalent before passing to business logic.

---

## 17. Missing `metadata` Exports

**Risk: 2**

AI generates page files without `metadata` exports or `generateMetadata` functions, resulting in pages with no title, description, or Open Graph tags.

### Before (AI-generated)

```tsx
// app/blog/[slug]/page.tsx — no metadata
export default async function BlogPost({ params }: { params: { slug: string } }) {
  const post = await getPost(params.slug);
  return <article>{post.content}</article>;
}
```

### After — Static Metadata

```tsx
// app/layout.tsx — site-wide defaults
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: {
    template: "%s | My Site",
    default: "My Site",
  },
  description: "The default site description.",
  openGraph: {
    siteName: "My Site",
    type: "website",
  },
};
```

### After — Dynamic Metadata

```tsx
// app/blog/[slug]/page.tsx
import type { Metadata } from "next";
import { notFound } from "next/navigation";

interface Props {
  params: { slug: string };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const post = await getPost(params.slug);
  if (!post) return { title: "Post Not Found" };

  return {
    title: post.title,
    description: post.excerpt,
    openGraph: {
      title: post.title,
      description: post.excerpt,
      images: post.coverImage ? [{ url: post.coverImage }] : [],
      type: "article",
      publishedTime: post.publishedAt,
    },
    twitter: {
      card: "summary_large_image",
    },
  };
}

export default async function BlogPost({ params }: Props) {
  const post = await getPost(params.slug);
  if (!post) notFound();
  return <article>{post.content}</article>;
}
```

### Safety Notes

- `generateMetadata` is deduplicated with the page's own data fetching — the same `getPost` call will not fire twice if it is a `fetch` with caching.
- Metadata from child segments overrides the parent — set a template in `layout.tsx` and specific titles in each page.
- Do not include `<title>` or `<meta>` tags in the JSX — use `metadata` exports only to avoid duplicates.

---

## 18. Server Actions Misuse

**Risk: 5**

AI generates Server Actions that are too broad (exported from shared files without proper scope), lack input validation, skip authorization checks, or expose internal errors to the client.

### Before (AI-generated)

```tsx
// app/actions.ts — overly broad, no auth, no validation
"use server";

import { db } from "@/lib/db";

// Any client can call this with any input
export async function deleteUser(userId: string) {
  await db.user.delete({ where: { id: userId } });
  return { success: true };
}

export async function updatePost(id: string, data: any) {
  const post = await db.post.update({ where: { id }, data });
  return post; // may expose internal fields
}
```

### After (corrected)

```tsx
// app/admin/users/actions.ts — scoped to admin section
"use server";

import { z } from "zod";
import { db } from "@/lib/db";
import { getSession } from "@/lib/auth";
import { revalidatePath } from "next/cache";

const DeleteUserSchema = z.object({
  userId: z.string().cuid(),
});

export async function deleteUser(formData: FormData) {
  // 1. Authenticate
  const session = await getSession();
  if (!session) throw new Error("Unauthorized");

  // 2. Authorize
  if (session.role !== "admin") throw new Error("Forbidden");

  // 3. Validate input
  const { userId } = DeleteUserSchema.parse({
    userId: formData.get("userId"),
  });

  // 4. Prevent deleting self
  if (userId === session.userId) throw new Error("Cannot delete your own account");

  // 5. Execute
  await db.user.delete({ where: { id: userId } });

  // 6. Revalidate affected paths
  revalidatePath("/admin/users");
}
```

```tsx
// app/admin/users/DeleteUserButton.tsx
"use client";

import { deleteUser } from "./actions";
import { useTransition } from "react";

export function DeleteUserButton({ userId }: { userId: string }) {
  const [isPending, startTransition] = useTransition();

  return (
    <form action={deleteUser}>
      <input type="hidden" name="userId" value={userId} />
      <button type="submit" disabled={isPending} aria-busy={isPending}>
        {isPending ? "Deleting..." : "Delete"}
      </button>
    </form>
  );
}
```

### Safety Notes

- Server Actions are POST endpoints — anyone can call them with arbitrary data. Always validate and authorize.
- Never throw errors with internal details to the client — in production, Next.js redacts server error messages; in dev they are visible.
- Colocate Server Actions with the features that use them, not in a single global `actions.ts`.
- Use `zod` or similar to parse and validate all input before touching the database.
- Use `revalidatePath` or `revalidateTag` after mutations so the UI stays in sync.

---

## 19. Over-Fetching in `layout.tsx`

**Risk: 3**

AI puts uncached data fetches in `layout.tsx` that run on every navigation within that segment — not just when the layout first renders. This defeats the persistent layout benefit and hammers the database on every route change.

### Before (AI-generated)

```tsx
// app/(app)/layout.tsx
export default async function AppLayout({ children }: { children: React.ReactNode }) {
  // This fetch runs on EVERY navigation to any route under (app)/
  // even though the layout does not unmount
  const user = await db.user.findUnique({
    where: { id: getUserIdFromSession() },
    include: { preferences: true, subscription: true },
  });

  return (
    <div>
      <Sidebar user={user} />
      {children}
    </div>
  );
}
```

### After (corrected — cached fetch)

```tsx
// lib/user.ts
import { cache } from "react";
import { db } from "@/lib/db";
import { getSession } from "@/lib/auth";

// React cache() deduplicates within a single request
export const getCurrentUser = cache(async () => {
  const session = await getSession();
  if (!session) return null;

  return db.user.findUnique({
    where: { id: session.userId },
    select: {
      id: true,
      name: true,
      email: true,
      // Only select what the layout actually needs
    },
  });
});
```

```tsx
// app/(app)/layout.tsx
import { getCurrentUser } from "@/lib/user";
import { redirect } from "next/navigation";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  return (
    <div>
      <Sidebar userName={user.name} />
      {children}
    </div>
  );
}
```

### Safety Notes

- In Next.js App Router, layouts do not re-run their code when children navigate — the layout component function is not called again. However, the fetch inside it still runs per-request on the server for any request to a child route. Caching is essential.
- `react.cache()` deduplicates calls within a single render pass — it does not persist across requests.
- For layout data that changes rarely (user profile, feature flags), use `next: { revalidate: 300 }` on `fetch` or set a short TTL in `unstable_cache`.

---

## 20. Not Using `unstable_cache` / `cache()` for Repeated Server-Side Data

**Risk: 3**

AI re-fetches the same data from the database multiple times within a request, or does not cache data that could safely be cached across requests (e.g., reference data, configuration, feature flags).

### Before (AI-generated)

```tsx
// Called multiple times per request, no deduplication
async function getFeatureFlags() {
  return db.featureFlag.findMany(); // new DB query every call
}

// Called in layout, page, and multiple components — 4 queries
export default async function Layout({ children }) {
  const flags = await getFeatureFlags();
  // ...
}
```

### After — Per-Request Deduplication with `cache()`

```tsx
// lib/feature-flags.ts
import { cache } from "react";
import { db } from "@/lib/db";

// Deduplicated within a single request — DB queried at most once per request
export const getFeatureFlags = cache(async () => {
  return db.featureFlag.findMany({ where: { enabled: true } });
});
```

### After — Cross-Request Caching with `unstable_cache`

```tsx
// lib/feature-flags.ts
import { unstable_cache } from "next/cache";
import { db } from "@/lib/db";

// Cached across requests — revalidated every 5 minutes
// Good for data that changes rarely (config, feature flags, reference data)
export const getFeatureFlags = unstable_cache(
  async () => {
    return db.featureFlag.findMany({ where: { enabled: true } });
  },
  ["feature-flags"],            // cache key
  {
    revalidate: 300,            // 5 minutes
    tags: ["feature-flags"],    // allows revalidateTag("feature-flags")
  }
);
```

### After — Typed Wrapper with Error Handling

```tsx
// lib/cache.ts — utility for consistent cross-request caching
import { unstable_cache } from "next/cache";

export function createCachedFetcher<T>(
  fetcher: () => Promise<T>,
  key: string[],
  options: { revalidate?: number; tags?: string[] } = {}
) {
  return unstable_cache(fetcher, key, {
    revalidate: options.revalidate ?? 60,
    tags: options.tags ?? key,
  });
}

// Usage
export const getConfig = createCachedFetcher(
  () => db.siteConfig.findFirst(),
  ["site-config"],
  { revalidate: 3600, tags: ["config"] }
);
```

### Safety Notes

- `react.cache()` is per-request deduplication — it does not survive between requests.
- `unstable_cache` is Next.js's cross-request server-side cache — it persists on the server between requests.
- Do not use `unstable_cache` for user-specific data unless the cache key includes the user ID.
- `unstable_cache` is marked unstable but is the recommended pattern for non-`fetch` data sources in Next.js 14/15. It is expected to stabilize.
- In Next.js 15, `use cache` directive (experimental) is the successor to `unstable_cache`.

---

## Server vs Client Component Decision Tree

```
Does the component need:
│
├─ useState / useReducer?                    → Client Component
├─ useEffect / useLayoutEffect?              → Client Component
├─ useRef (for DOM access)?                  → Client Component
├─ onClick / onChange / other event handlers? → Client Component
├─ Browser APIs (window, navigator, etc.)?   → Client Component
├─ Third-party library that uses hooks?      → Client Component
│
└─ None of the above?
   │
   ├─ Does it fetch data?                    → Server Component (fetch in component)
   ├─ Does it access server resources         → Server Component
   │  (DB, filesystem, env vars)?
   ├─ Does it need to stay secret            → Server Component
   │  (API keys, tokens)?
   └─ Is it purely presentational?           → Server Component (default)
```

### Composition Pattern

Keep Client Components at the leaves of the tree. Server Components can render Client Components, but Client Components cannot render Server Components (they can accept them as `children` props).

```tsx
// Correct: Server Component wraps Client Component
// app/page.tsx (Server Component)
import { InteractiveWidget } from "./InteractiveWidget"; // Client Component

export default async function Page() {
  const data = await fetchData(); // runs on server
  return <InteractiveWidget initialData={data} />;
}
```

```tsx
// Correct: Client Component accepts Server Component as children
// app/layout.tsx (Server Component)
import { Sidebar } from "./Sidebar"; // Client Component

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <Sidebar>
      {children} {/* children can be Server Components */}
    </Sidebar>
  );
}
```

---

## When to Use `"use server"` vs `"use client"`

### `"use client"`

Add at the top of a file (module scope) when:

- The component uses React hooks (`useState`, `useEffect`, `useRef`, `useContext`, etc.)
- The component handles browser events
- The component uses browser-only APIs
- The component uses a third-party library that requires client-side execution

```tsx
"use client";
// Everything exported from this file becomes a Client Component
```

**Propagates down**: All components imported inside a Client Component file are also treated as client-side, even without the directive.

### `"use server"`

Add at the top of a file (module scope) or inside a function when:

- The file exports Server Actions (functions called from Client Components that run on the server)
- You want to mark individual async functions as Server Actions within a Server Component file

```tsx
// As a file directive — all exports are Server Actions
"use server";

export async function createPost(formData: FormData) { /* ... */ }
export async function deletePost(id: string) { /* ... */ }
```

```tsx
// As an inline directive — only this function is a Server Action
// app/posts/page.tsx (Server Component file)
export default function PostPage() {
  async function handleDelete(id: string) {
    "use server"; // inline Server Action
    await db.post.delete({ where: { id } });
    revalidatePath("/posts");
  }
  // ...
}
```

### Neither Directive Needed

- Server Components (the default in `app/`) — no directive required
- Route Handlers (`route.ts`) — always server-side, no directive needed
- Middleware (`middleware.ts`) — runs on the Edge, no directive needed
- Next.js config files — server-side, no directive needed

---

## Caching Strategy Guide

### Decision Matrix

| Data Type | Changes How Often | Strategy | Implementation |
|-----------|------------------|----------|----------------|
| Static content (legal pages, docs) | Rarely / deploy | Full static | `cache: "force-cache"` or `export const revalidate = false` |
| Blog posts, product catalog | Hours / days | ISR | `next: { revalidate: 3600 }` |
| News, feeds, scores | Minutes | Short ISR | `next: { revalidate: 60 }` |
| User-specific data | Per user | Dynamic + per-user cache key | `cache: "no-store"` or `unstable_cache` with user key |
| Real-time data | Seconds | Dynamic, no cache | `cache: "no-store"` |
| Reference data (countries, categories) | Infrequently | Cross-request cache | `unstable_cache` with long TTL |

### Route Segment Configuration

Set defaults for all fetches in a segment:

```tsx
// app/blog/layout.tsx or page.tsx
export const dynamic = "force-static";  // all fetches: force-cache
export const dynamic = "force-dynamic"; // all fetches: no-store
export const revalidate = 3600;         // all fetches: revalidate every hour
export const runtime = "edge";          // run on Edge Runtime
```

### On-Demand Revalidation

```tsx
// Revalidate a specific path (clears all cached data for that URL)
import { revalidatePath } from "next/cache";
revalidatePath("/blog/[slug]", "page");

// Revalidate all pages using a layout
revalidatePath("/blog", "layout");

// Revalidate by tag (only clears fetches tagged with this tag)
import { revalidateTag } from "next/cache";
revalidateTag("posts");
```

### Caching Layers in Next.js

```
Request
  │
  ├─ Router Cache (client-side, in-memory, ~30s for dynamic, ~5min for static)
  │   Stores visited RSC payloads in the browser
  │
  ├─ Full Route Cache (server-side, persistent)
  │   Stores statically rendered route HTML + RSC payload
  │
  ├─ Data Cache (server-side, persistent)
  │   Stores fetch() responses — survives across requests and deployments
  │   unless revalidated
  │
  └─ Request Memoization (per-request, in-memory)
      Deduplicates fetch() calls with same URL within one render pass
      Also: react.cache() for non-fetch deduplication
```

### Cache Anti-Patterns to Watch For

```tsx
// BAD: Dynamic function makes entire route dynamic
export default async function Page() {
  const headersList = await headers(); // opts out of static generation
  const data = await fetch("https://api.example.com/static-data"); // now uncached
}

// GOOD: Isolate dynamic parts, keep static data cached
export default async function Page() {
  const data = await fetch("https://api.example.com/static-data", {
    next: { revalidate: 3600 },
  });
  return (
    <>
      <StaticContent data={data} />
      <Suspense>
        <DynamicSection /> {/* reads headers() in isolation */}
      </Suspense>
    </>
  );
}
```

---

*Last updated: 2026-06-06. Covers Next.js 13.4 through 15.x App Router.*
