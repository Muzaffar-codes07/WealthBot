# WealthBot — AI Agent Guidelines

WealthBot is a predictive personal finance app for Indian students. It predicts a **"Safe-to-Spend"** daily limit. Stack: **FastAPI + PostgreSQL** (backend), **Next.js 16 + Tailwind** (frontend), **XGBoost + DistilBERT** (ML).

---

## Context Management Protocol

> **This file is the agent's persistent memory.** Update the `## Session State` section at the **end of every iteration** (feature, bugfix, testing pass, or refactor) so the next conversation inherits full context.

**Rules for the agent:**
1. **Read first.** At the start of every conversation, read this entire file to restore context — project state, known bugs, what's done, what's next.
2. **Write last.** Before ending a conversation, update `## Session State` with: what changed, what broke, what's next. Keep entries concise (bullet points, not prose).
3. **Never duplicate.** If a section already covers the fact, update in-place rather than appending.
4. **Mark completion.** When a task-queue item is finished, strike it out (`~~text~~`) and add `✅ COMPLETE` to the phase header.
5. **Log bugs.** Any confirmed bug discovered during testing goes into `## Known Issues`. Remove when fixed.
6. **Versions matter.** Record dependency pins and environment details in `## Environment` so future sessions don't debug phantom mismatches.

---

## Execution Rules

- **No placeholders.** Never write `// implement later`, `pass`, or `TODO`. Write the actual logic.
- **No conversational filler.** Output production-ready code; skip explanations of basic concepts.
- **Icons:** Use `lucide-react` exclusively for UI icons.
- Always run linters/type-checks after generating code to confirm correctness.

## Code Style

### Python (Backend)

- **Formatter**: Black (`line-length = 88`, target `py312`) — [pyproject.toml](../pyproject.toml)
- **Linter**: Ruff (rules: `E, W, F, I, B, C4, UP, ARG, SIM`)
- **Type checker**: MyPy strict — all functions must have full type annotations
- **Docstrings**: Google-style (`Args:`, `Returns:`). Module headers: RST `====` underlines
- **Section separators**: 77-char `# ====...====` block-comment headers between logical sections
- **Naming**: `snake_case` functions/variables, `PascalCase` classes, `UPPER_SNAKE` constants
- **Imports**: stdlib → third-party → local (one blank line between groups). First-party: `app`, `ml`
- **Exemplars**: [app/core/security.py](../app/core/security.py), [app/db/models.py](../app/db/models.py)

### TypeScript (Frontend)

- **Strict mode** enabled — [tsconfig.json](../frontend/tsconfig.json)
- **Path alias**: `@/*` → `./src/*`
- **Components**: `'use client'` directive on interactive leaves, functional, named exports. Pages use `export default function`
- **Naming**: `PascalCase` components/interfaces, `camelCase` functions, `UPPER_SNAKE` constants
- **Styling**: Tailwind CSS only via `className`. Custom classes (`.card`, `.btn-primary`) in [globals.css](../frontend/src/styles/globals.css) with `@layer components`
- **Exemplars**: [src/app/page.tsx](../frontend/src/app/page.tsx), [src/components/ui/MetricCard.tsx](../frontend/src/components/ui/MetricCard.tsx)

## Architecture

```
Backend (FastAPI)          Frontend (Next.js 16)      ML Pipeline
├─ app/main.py (entry)     ├─ src/app/ (pages)        ├─ ml/inference/
├─ app/api/v1/ (routes)    ├─ src/components/         ├─ ml/preprocessing/
├─ app/core/ (config,sec)  ├─ src/stores/ (Zustand)   ├─ ml/training/
├─ app/db/ (models,engine) ├─ src/hooks/ (React Query) └─ ml/models/ (artifacts)
├─ app/schemas/ (Pydantic) ├─ src/lib/ (api,utils)
└─ app/services/ (ML glue) └─ src/types/ (interfaces)
```

- **Database**: Async SQLAlchemy 2.0 via `asyncpg`. Singleton `DatabaseManager` — [app/db/database.py](../app/db/database.py). Financial amounts: `Numeric(15,2)`, never `Float`
- **Config**: `pydantic-settings` + `.env` + `@lru_cache` singleton — [app/core/config.py](../app/core/config.py)
- **Frontend state**: **Zustand** for ephemeral UI state only (sidebar, dark mode). **React Query** for all server/API state. Never sync API data into Zustand
- **API proxy**: Next.js rewrites `/api/:path*` → FastAPI — [next.config.js](../frontend/next.config.js)
- **Docker**: Multi-stage build (Python 3.12-slim), non-root `wealthbot` user (UID 1000). Compose: `db` (Postgres 16), `api` (FastAPI), `redis` (Redis 7)

## Environment

```
Python:      3.12  (venv at .venv/)
Node:        LTS   (frontend/)
PostgreSQL:  18    (localhost:5432)
DB User:     wealthbot_user / wealthbot_secret
DB Name:     wealthbot_db
Extensions:  uuid-ossp, pg_trgm
Key pins:    bcrypt==4.0.1 (passlib compat), asyncpg, sqlalchemy[asyncio]
```

- **DATABASE_URL**: `postgresql+asyncpg://wealthbot_user:wealthbot_secret@localhost:5432/wealthbot_db`
- **Demo account**: `demo@wealthbot.app` / `Demo@1234` (first_name: "Swarna", seeded with 8 transactions)

## Build and Test

```bash
# Backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev     # http://localhost:3000

# Lint & Format
black app/ ml/ tests/
ruff check app/ ml/ tests/
mypy app/
cd frontend && npm run lint && npm run type-check   # tsc --noEmit

# Test (target ≥80% coverage)
pytest --cov=app --cov-report=term-missing

# Migrations
alembic upgrade head
alembic revision --autogenerate -m "description"

# Docker
docker-compose up --build
```

## Strict Engineering Constraints

### Backend

- **Non-blocking ML inference.** Never call `joblib.load()`, `model.predict()`, or HuggingFace pipelines directly in `async def` routes. Wrap in `fastapi.concurrency.run_in_threadpool` or use a background worker
- **Model lifespan.** Preload models during startup via FastAPI `@asynccontextmanager` lifespan events. Never lazy-load on the first request
- **Pagination.** All list endpoints must use `limit`/`offset` pagination
- **Rate limiting.** Apply `slowapi` rate-limiting to `/ai/chat` and `/statements/upload`
- **DB session.** Always use `async with db_manager.session()`. The `DatabaseManager` is a Singleton — don't re-instantiate in DI

### Frontend

- **Server Components first.** Use `'use client'` only at interactive leaves (charts, buttons, forms), not at layout level
- **State boundaries.** React Query = server state (API cache, loading, errors). Zustand = client UI state (toggles, theme). Never mix
- **Providers.** `Providers.tsx` wraps `QueryClientProvider` + `ErrorBoundary` + React Query Devtools. Wired into `layout.tsx` ✅
- **Auth.** Bearer token via `localStorage` (`auth_token` key). Axios interceptor handles 401 → `/login` redirect. All React Query hooks gated by `enabled: !!getToken()`

### ML Pipeline

- **Thread safety.** XGBoost and DistilBERT models loaded once at startup, shared across requests via `MLService` singleton — [app/services/ml_service.py](../app/services/ml_service.py)
- **Feature vectors.** Use `TransactionFeatures` Pydantic model for all ML input validation
- **Structured logging.** Every prediction must emit a JSON log with: input features, output, confidence, latency. Exclude all PII

## Conventions

- **Barrel exports**: Every component subfolder has an `index.ts` re-exporting all public members
- **Types**: Shared TS types in [src/types/index.ts](../frontend/src/types/index.ts). Data interfaces (`WBTransaction`, `Subscription`) alongside mock data in [constants/data.ts](../frontend/src/constants/data.ts)
- **API hooks**: One hook per endpoint in [src/hooks/useApi.ts](../frontend/src/hooks/useApi.ts). Invalidate query cache on mutations
- **Mock data context**: Indian student finance — ₹ currency, UPI apps (GPay, PhonePe), Indian merchants (Swiggy, Zomato, Zepto, Rapido)
- **Alembic**: Auto-formats migrations with Black post-write hook — [alembic.ini](../alembic.ini)
- **Test DB**: SQLite in-memory with `StaticPool` for fast async tests — [tests/conftest.py](../tests/conftest.py)
- **Tailwind design**: Dark theme only. Custom colors: `background-primary: #0a0f1a`, `accent-green: #22c55e`. See [tailwind.config.js](../frontend/tailwind.config.js)

## Security

- **Password hashing**: bcrypt via passlib (12 rounds) — [app/core/security.py](../app/core/security.py)
- **JWT**: HS256, 30min expiry, payload: `sub`, `exp`, `iat`, `type`. Default secret key **must** be changed in production
- **PII masking** (GDPR/SOC 2): Regex masks for email, phone, SSN, credit card, plus Indian PAN/Aadhaar/UPI VPAs. `sanitize_log_data()` redacts recursively. Controlled by `enable_pii_masking` flag
- **CORS**: Whitelist only trusted origins in `ALLOWED_ORIGINS`
- **Docker**: Non-root user, read-only volume mounts for app code

## Integration Points

- **API surface** (`/api/v1/`): `/safe-to-spend`, `/transactions`, `/analytics/velocity`, `/analytics/subscriptions`, `/statements/upload`, `/ai/chat`
- **ML glue**: `MLService` singleton loads XGBoost via `joblib`, exposes `predict_spending()` and `calculate_safe_to_spend()`
- **DB extensions**: `uuid-ossp` + `pg_trgm` — [scripts/init-db.sql](../scripts/init-db.sql)

---

## Completed Work

### Phase 1 — Backend API ✅ COMPLETE

| # | Deliverable | Files Created | Key Details |
|---|------------|---------------|-------------|
| 1 | **Pydantic schemas** | `app/schemas/{common,user,transaction,prediction}.py`, `__init__.py` | `PaginatedResponse[T]` generic, `SafeToSpendResponse` with risk_level/model_used, `CategoryUpdateRequest` |
| 2 | **API route handlers** | `app/api/v1/{users,transactions,predictions}.py`, `app/api/deps.py` | Auth: register + JWT login. Transactions: full CRUD, pagination, search (merchant+description+category via ILIKE). Predictions: heuristic safe-to-spend with ML activation threshold (≥10 txns) |
| 3 | **Alembic migration** | `alembic/versions/20260305_0001_initial_tables_users_transactions.py` | `users` table (UUID PK, email unique, Numeric(15,2) financial fields) + `transactions` table (FK to users, category, recurring flag) |
| 4 | **`.env.example`** | `.env.example` | DATABASE_URL, SECRET_KEY, MODEL_PATH, ALLOWED_ORIGINS, ENABLE_PII_MASKING, etc. |

**Backend verification (all 200 OK):**
- `POST /api/v1/auth/token` — JWT login working
- `GET /api/v1/users/me` — returns authenticated user profile
- `GET /api/v1/safe-to-spend` — heuristic: ₹37,164 (₹50k income − expenses)
- `GET /api/v1/transactions` — 8 seeded transactions with pagination
- `PATCH /api/v1/transactions/{id}` — category update with cache invalidation

### Phase 2 — Frontend Wiring ✅ COMPLETE

| # | Deliverable | Files Created/Modified | Key Details |
|---|------------|----------------------|-------------|
| 5 | **Providers wired** | `src/components/providers/Providers.tsx` → `src/app/layout.tsx` | `QueryClientProvider` with `staleTime: 60s`, `retry: 1`, devtools enabled |
| 6 | **Login/registration** | `src/app/login/page.tsx` | Toggle login ↔ register mode, auto-login after register, password visibility toggle, error display from backend |
| 7 | **Pages connected to live API** | `src/app/page.tsx`, `src/app/transactions/page.tsx` | Home: `useSafeToSpend()` + `useTransactions(limit:3)`. Transactions: search with 300ms debounce, pagination (20/page), inline category edit via `useUpdateTransactionCategory()` |
| 8 | **Loading states & skeletons** | All page files | `SkeletonGauge`, `SkeletonTransactions` on home. `Loader2` spinner on login. Auth gating via `useRequireAuth()` on all protected pages |

**Frontend component inventory:**

| Component | Path | Purpose |
|-----------|------|---------|
| `MainLayout` | `src/components/layout/MainLayout.tsx` | 3-column responsive layout (sidebar / main / Aura assistant) |
| `Sidebar` | `src/components/layout/Sidebar.tsx` | Fixed left nav, slide-in on mobile, auto-closes on link click |
| `Header` | `src/components/layout/Header.tsx` | Reusable page header with title, subtitle, notification bell, action button |
| `AuraAssistant` | `src/components/assistant/AuraAssistant.tsx` | Right-side AI chat panel (`w-80`), contextual tips per page |
| `Providers` | `src/components/providers/Providers.tsx` | React Query + Error Boundary wrapper |
| `MetricCard` | `src/components/ui/MetricCard.tsx` | Stat card with icon, value, trend |
| `CategoryBadge` | `src/components/ui/CategoryBadge.tsx` | Colored category tag |
| `ProgressBar` | `src/components/ui/ProgressBar.tsx` | Animated progress indicator |
| `StatusBadge` | `src/components/ui/StatusBadge.tsx` | Status pill (active, due, etc.) |
| `TimeRangeSelector` | `src/components/ui/TimeRangeSelector.tsx` | Period toggle tabs |

**API hooks** (all in `src/hooks/useApi.ts`):

| Hook | Endpoint | Status |
|------|----------|--------|
| `useLogin()` | `POST /auth/token` | ✅ Working |
| `useRegister()` | `POST /auth/register` | ✅ Working |
| `useCurrentUser()` | `GET /users/me` | ✅ Working |
| `useRequireAuth()` | (client redirect guard) | ✅ Working |
| `useLogout()` | (client-side token clear) | ✅ Working |
| `useSafeToSpend()` | `GET /safe-to-spend` | ✅ Working |
| `useTransactions()` | `GET /transactions` | ✅ Working |
| `useUpdateTransactionCategory()` | `PATCH /transactions/{id}` | ✅ Working |
| `useSpendingVelocity()` | `GET /analytics/velocity` | ⏸ Disabled (Phase 3) |
| `useSubscriptions()` | `GET /analytics/subscriptions` | ⏸ Disabled (Phase 3) |
| `useUploadStatement()` | `POST /statements/upload` | ⏸ Disabled (Phase 3) |
| `useAIChat()` | `POST /ai/chat` | ⏸ Disabled (Phase 3) |

**Pages still using mock data** (to be wired in Phase 3):
- `src/app/budgets/page.tsx` (Analytics / "Leakage Hunter") — subscriptions, velocity chart, spending stats from `constants/data.ts`
- `src/app/investments/page.tsx` (Settings / "Vault & Settings") — statement upload uses local fake delay, privacy logs from mock

### Phase 2.5 — Visual Testing & Responsiveness ✅ COMPLETE

Tested via Playwright MCP at three breakpoints:

| Viewport | Width | Layout | Result |
|----------|-------|--------|--------|
| Mobile | 375×812 | Single column, hamburger menu, toggle Aura | ✅ Clean |
| Tablet | 768×1024 | Single column, wider cards | ✅ Clean |
| Desktop | 1440×900 | 3-column: sidebar + main + Aura | ✅ Clean |

**Pages visually verified:** Login, Home, Transactions, Analytics, Settings — all viewports.

**Bugs found and fixed during testing:**
- **Aura panel 8px leak on mobile** — `translate-x-full` (320px) left 8px visible due to scrollbar width on `fixed right-0` positioning. Fixed → `translate-x-[105%]` in `MainLayout.tsx`, plus `overflow-x-hidden` on body in `globals.css`
- **Transaction search didn't match categories** — backend ILIKE only checked `merchant_name` + `description`. Fixed → added `Transaction.category.ilike(pattern)` to the `or_()` clause in `app/api/v1/transactions.py`

**Interactive elements verified:**
- ✅ Mobile hamburger menu — opens/closes sidebar correctly
- ✅ Sidebar navigation — links navigate and auto-close sidebar on mobile
- ✅ Aura assistant toggle — opens on mobile, closes via backdrop tap
- ✅ Transaction search — filters by merchant name and category, 300ms debounce
- ✅ Category edit — pencil icon opens dropdown, selecting a category triggers PATCH mutation + cache invalidation

---

## Known Issues

- **Aura toggle button unreachable when panel is open on mobile** — The panel (z-40) covers the header toggle button (z-30). Users must tap the backdrop overlay to close. UX improvement: add an explicit close (X) button inside the Aura panel header for mobile, or raise the header z-index above the panel.
- **"1 Issue" Next.js dev badge** — Dev-only indicator, not a production issue.
- **Analytics & Settings pages** — Still consume mock data from `constants/data.ts`. Need backend endpoints for velocity, subscriptions, and statement upload (Phase 3).

---

## Current Task Queue

### Phase 3 — ML Pipeline (do next)
9. **Preprocessing** — feature engineering in `ml/preprocessing/` (transaction aggregation, time features)
10. **XGBoost training** — spending prediction model in `ml/training/`
11. **DistilBERT fine-tuning** — transaction categorization in `ml/training/`
12. **Inference pipeline** — production serving in `ml/inference/` with structured logging
13. **Model artifacts** — trained `.joblib`/`.bin` files in `ml/models/`

### Phase 4 — Hardening
14. **Test suite** — pytest cases for all API endpoints, services, and security module (target ≥80% coverage)
15. **`slowapi` rate limiting** on `/ai/chat` and `/statements/upload`
16. **`structlog`** integration for structured JSON logging across backend

### Backlog (non-blocking improvements)
- Wire Analytics page (`/budgets`) to live API once velocity/subscription endpoints exist
- Wire Settings page (`/investments`) to live statement upload endpoint
- Add explicit close button to Aura panel for mobile UX

---

## Session State

> **Last updated:** 2026-03-07

**What happened this session:**
- Completed Phase 2.5 visual testing — verified all interactive elements (Recalculate, View All, search, category edit, hamburger, Aura toggle) at 3 breakpoints via Playwright MCP
- Confirmed ESLint config fix — removed duplicate `export default`, `eslint src/` = 0 errors, 0 warnings
- Confirmed Zustand hydration fix already applied — `skipHydration: true` + `useHydration()` hook in Providers.tsx
- Confirmed `tsc --noEmit` = 0 errors
- Corrected Next.js version in docs: 14 → **16.1.6**
- **Phase 2.5 is fully COMPLETE**

**What's running:**
- Backend: `uvicorn app.main:app --reload --port 8000`
- Frontend: `cd frontend && npm run dev` on port 3000
- DB: PostgreSQL 18 on localhost:5432

**Next session should:**
1. Begin Phase 3 — ML pipeline (preprocessing → training → inference)
2. Optionally add close button to Aura panel header for mobile
