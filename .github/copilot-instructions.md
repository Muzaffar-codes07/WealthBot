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
DB User:     (see .env file)
DB Name:     wealthbot_db
Extensions:  uuid-ossp, pg_trgm
Key pins:    bcrypt==4.0.1 (passlib compat), asyncpg, sqlalchemy[asyncio]
Test pins:   pytest-asyncio, pytest-cov, httpx (asyncio_mode="auto", PostgreSQL wealthbot_test DB)
Infra pins:  slowapi>=0.1.9, structlog>=24.1.0, sonner (frontend toast)
ML pins:     xgboost>=2.0.3, transformers>=4.37.0, torch>=2.9.0, scikit-learn>=1.4.0,
             onnxruntime>=1.17.0, joblib>=1.3.2, numpy>=1.26.3, pandas>=2.1.4
ML runtime:  ONNX Runtime (CPU, 16GB RAM) — training on Google Colab (T4 GPU)
```

- **DATABASE_URL**: Configured in `.env` (see `.env.example` for format)
- **Demo account**: `demo@wealthbot.app` / password in `.env` (first_name: "Swarna", seeded with 8 transactions)

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

- **ONNX Runtime inference.** All production inference uses `onnxruntime` (CPU). Never load native XGBoost or PyTorch models in the FastAPI process. Training exports to `.onnx`; inference loads via `ort.InferenceSession`
- **Thread safety.** ONNX sessions loaded once at startup via `MLService` singleton — [app/services/ml_service.py](../app/services/ml_service.py). Shared across requests, wrapped in `run_in_executor` for non-blocking async
- **Training environment.** Training scripts in `ml/training/` are standalone Colab-compatible `.py` files (not notebooks). Target: Google Colab T4 GPU for DistilBERT, CPU for XGBoost
- **DistilBERT strategy.** Freeze all base layers; train only the classification head (transfer learning). Input: `merchant_name + " " + description` → 17 `TransactionCategory` labels
- **Feature vectors.** 21-feature vector defined in `ml/models/feature_config.json` (single source of truth). Use `ml/preprocessing/features.py::extract_user_features()` for both training and inference to prevent train-serve skew
- **Heuristic fallback.** If ONNX models are missing at startup, all prediction endpoints gracefully fall back to heuristic logic. Zero breaking changes
- **Structured logging.** Every prediction must emit a JSON log with: model name, input features (sanitized), output, confidence interval, latency_ms, hashed user_id. Exclude all PII — no raw transaction text in logs
- **Model artifacts.** Stored in `ml/models/` (`.gitignore`-d in production). Key files: `xgboost_spending.onnx`, `categorizer.onnx`, `tokenizer/`, `feature_config.json`, `label_encoder.json`

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
- **ML glue**: `MLService` singleton loads ONNX models at startup via `ml/inference/predictor.py::SpendingPredictor` and `ml/inference/categorizer.py::TransactionCategorizer`. Exposes `predict_spending()`, `calculate_safe_to_spend()`, and `categorize_transaction()`
- **ML data flow**: `ml/preprocessing/features.py::extract_user_features()` → 21-feature numpy vector → `SpendingPredictor.predict()` → (prediction, lower_ci, upper_ci)
- **Auto-categorization**: `POST /api/v1/transactions` without category → DistilBERT predicts `predicted_category` + `category_confidence` inline (~5ms ONNX)
- **Cold-start threshold**: `MIN_TRANSACTIONS_FOR_ML = 10` in `app/api/v1/predictions.py` — below this, heuristic fallback
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
| `useSpendingVelocity()` | `GET /analytics/velocity` | ✅ Working |
| `useSubscriptions()` | `GET /analytics/subscriptions` | ✅ Working |
| `useUploadStatement()` | `POST /statements/upload` | ✅ Working |
| `useAIChat()` | `POST /ai/chat` | ✅ Working |

**Pages now wired to live APIs:**
- `src/app/budgets/page.tsx` → velocity + subscriptions from backend
- `src/app/investments/page.tsx` → live statement CSV upload
- `src/components/assistant/AuraAssistant.tsx` → live `/ai/chat`

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
- **PDF statement extraction is heuristic-first** — parser currently relies on common line patterns; bank-specific PDF templates may need adapters.

---

## Current Task Queue

### Phase 3 — ML Pipeline (do next)

#### Phase 3A — Data Foundation ✅ COMPLETE
| # | Deliverable | File | Status |
|---|------------|------|--------|
| 9 | **Synthetic data generator** | `ml/preprocessing/synthetic_data.py` | ✅ Done |
| 10 | **Feature engineering pipeline** | `ml/preprocessing/features.py` + `ml/models/feature_config.json` | ✅ Done |

- Step 9: `generate_synthetic_dataset(n_users=100, txns_per_user=100, seed=42) → pd.DataFrame` — ~14k Indian-student transactions (2 months, 100 users) with UPI merchants, ₹ amounts, temporal patterns (weekend food spikes, month-end crunch, recurring bills, post-salary looseness)
- Step 10: 21-feature vector (`extract_user_features()` for inference, `build_training_matrix()` for training). Target: `next_7d_spending`. Feature config: `ml/models/feature_config.json`. Training matrix: 787 samples × 21 features

#### Phase 3B — Model Training (Colab-compatible) ✅ COMPLETE
| # | Deliverable | File | Status |
|---|------------|------|--------|
| 11 | **XGBoost spending predictor** | `ml/training/train_xgboost.py` | ✅ Done |
| 12 | **DistilBERT categorizer** | `ml/training/train_categorizer.py` + `ml/training/train_categorizer_colab.ipynb` | ✅ Done |

- Step 11: `XGBRegressor(n_estimators=200, max_depth=6, lr=0.1)`, 80/20 time-aware split, early stopping (best_iteration=36), ONNX export via `onnxmltools` → `ml/models/xgboost_spending.onnx` (78.4 KB). **Results:** MAE=₹688, RMSE=₹994, R²=0.9554. Top features: days_until_month_end, day_of_month, monthly_income
- Step 12: Frozen base + classification head only (0.9% trainable), 10 epochs, batch=32, lr=5e-4, trained on Google Colab T4 GPU. ONNX export (single-file consolidation via `onnx.save_model`) → `ml/models/categorizer.onnx` (256 MB) + `ml/models/tokenizer/` + `ml/models/label_encoder.json` (15 categories). **Results:** val_acc=1.0000 by epoch 2

#### Phase 3C — Inference & Integration ✅ COMPLETE
| # | Deliverable | File | Status |
|---|------------|------|--------|
| 13 | **ONNX inference wrappers** | `ml/inference/predictor.py`, `ml/inference/categorizer.py` | ✅ Done |
| 14 | **MLService refactoring** | `app/services/ml_service.py` | ✅ Done |
| 15 | **Structured prediction logging** | Integrated into inference wrappers | ✅ Done |

- Step 13: `SpendingPredictor` — ONNX Runtime CPUExecutionProvider, 21-feature float32 input, returns `(prediction, lower_ci, upper_ci)` using RMSE=994 for 95% CI. `TransactionCategorizer` — ONNX + HF tokenizer (max_length=64) + softmax → `(category, confidence)`. Smoke tests: predictor `(6194.44, 4246.20, 8142.68)` ✅, categorizer `('Food', 0.982)` for "Swiggy online food delivery" ✅
- Step 14: Complete rewrite of `ml_service.py` — removed joblib/Pydantic models, added `load_models()` async startup, `predict_spending()` + `categorize_transaction()` via `functools.partial` + `run_in_executor`, heuristic fallback preserved. Auto-categorization added to `POST /transactions` — DistilBERT predicts inline when category defaults to OTHER (~5ms ONNX). `predictions.py` rewritten to use `extract_user_features()` for real 21-feature vector extraction from last 60 days of transactions
- Step 15: Both inference wrappers emit structured JSON logs: model name, feature_summary/text_length, output, confidence/CI, latency_ms, hashed user_id (SHA-256). PII excluded

#### Phase 3D — Configuration & Verification ✅ COMPLETE
| # | Deliverable | File | Status |
|---|------------|------|--------|
| 16 | **Config updates** | `config.py`, `requirements.txt`, `.env.example`, `main.py` | ✅ Done |
| 17 | **Training execution** | Run scripts, produce ONNX artifacts | ✅ Done (Phase 3B) |
| 18 | **Integration verification** | Startup, API responses, lint, types | ✅ Done |

- Step 16: Added 5 settings to `config.py`: `xgboost_onnx_path`, `categorizer_onnx_path`, `tokenizer_path`, `label_encoder_path`, `feature_config_path`. Added `onnxruntime>=1.17.0` to `requirements.txt`. Updated `.env.example` with all ML config keys. Changed `main.py` lifespan: `load_model()` → `load_models()`
- Step 17: Completed in Phase 3B — all ONNX artifacts produced and verified
- Step 18: **Verified:** FastAPI startup loads both models ✅. `GET /safe-to-spend` → `model_used: "heuristic"` (demo has 8 txns < 10 threshold, correct behavior). `POST /transactions` with Swiggy → auto-categorized as `Food` (0.982 confidence) ✅. `ruff check` ✅, `black` ✅, `mypy` zero errors in changed files (5 pre-existing in security.py/database.py) ✅

### Phase 4 — Hardening ✅ COMPLETE

| # | Deliverable | Files Created/Modified | Status |
|---|------------|----------------------|--------|
| 19 | **Test suite (≥80% coverage)** | `tests/conftest.py` (rewrite), `tests/test_security.py`, `tests/test_ml_service.py`, `tests/test_users.py`, `tests/test_transactions.py`, `tests/test_predictions.py`, `tests/test_health.py`, `tests/test_logging.py` | ✅ Done |
| 20 | **`slowapi` rate limiting** | `app/core/rate_limit.py`, `app/main.py` | ✅ Done |
| 21 | **`structlog` integration** | `app/core/logging.py`, `app/main.py` | ✅ Done |
| — | **Frontend 429 toast** | `frontend/src/lib/api.ts`, `frontend/src/components/providers/Providers.tsx` | ✅ Done |

- Step 19: **70 tests, 80.96% coverage** against PostgreSQL (`wealthbot_test` DB). Tests: security (19), ml_service (16), users (12), transactions (12), predictions (5), health (4), logging (2). `conftest.py` fully rewritten — per-fixture engine creation (avoids event loop issues), `mock_ml_service` with deterministic outputs, `auth_headers`/`authed_client` fixtures. `pytest-asyncio` with `asyncio_mode="auto"`, function-scoped event loops
- Step 20: `slowapi` Limiter with `get_remote_address` key_func. Custom JSON 429 handler returning `detail` + `retry_after`. Wired into `app.state.limiter` + exception handler in `main.py`. Ready for per-endpoint decorators (`@limiter.limit("5/minute")` on upload, `"20/minute"` on chat)
- Step 21: `structlog` with shared processor chain (contextvars, log_level, logger_name, timestamper, stack_info, unicode). Environment-aware renderer: `JSONRenderer` for prod/staging, `ConsoleRenderer` for dev. `configure_logging()` called during FastAPI lifespan startup
- Frontend: Axios response interceptor catches HTTP 429 → `toast.error()` via `sonner`. `<Toaster theme="dark" position="top-right" richColors />` in Providers

### Backlog (non-blocking improvements)
- Add explicit close button to Aura panel for mobile UX

### Phase 5–8 — Road to Deployment (Current Plan)

#### Phase 5 — API Completion & Frontend Wiring (In Progress)
- 5A Backend endpoints:
  - ✅ `GET /analytics/velocity`
  - ✅ `GET /analytics/subscriptions`
  - ✅ `POST /statements/upload` (`5/minute`, CSV + PDF parser)
  - ✅ `POST /ai/chat` (`20/minute`, rule-based personalized replies)
- 5B Frontend wiring:
  - ✅ `budgets/page.tsx` wired to analytics APIs
  - ✅ `investments/page.tsx` wired to statement upload API
  - ✅ `AuraAssistant.tsx` wired to live `/ai/chat`
  - ✅ Disabled React Query hooks enabled in `useApi.ts`
- 5C Tests:
  - ✅ Added endpoint integration tests for velocity, subscriptions, upload, and AI chat

#### Phase 6 — Security & Auth Hardening
- 6A Middleware in `main.py`: global 500 handler, security headers, TrustedHost, GZip, Request-ID
- 6B Auth improvements: refresh token endpoint + frontend auto-refresh and session UX
- 6C Tests for middleware and refresh flow

#### Phase 7 — CI/CD & Infrastructure
- 7A GitHub Actions: CI and deploy workflows + branch protection
- 7B Docker production stack: auto-migrate entrypoint, frontend Dockerfile, nginx service/proxy
- 7C Env config templates + deployment docs

#### Phase 8 — Production Polish
- 8A Frontend polish: image optimization, lazy charts, metadata, accessibility, mobile Aura close button
- 8B Observability: request logging middleware + Sentry integration
- 8C Final verification: clean compose boot, E2E smoke, load test, OWASP ZAP

---

## Session State

> **Last updated:** 2026-03-14

**What happened this session:**
- Extended Phase 5 upload support from CSV-only to CSV + PDF
  - Added PDF parser path in `app/api/v1/statements.py` with `pdfplumber`
  - Added PDF upload integration test in `tests/test_phase5_endpoints.py`
  - Updated dependency and env docs: `requirements.txt`, `.env.example`
- Started Phase 6A hardening in `app/main.py`
  - Added global 500 exception handler with safe JSON payload
  - Added security headers middleware (HSTS, nosniff, frame deny)
  - Added TrustedHost and GZip middleware
  - Added request ID + process-time response headers via request context middleware
  - Added middleware tests in `tests/test_phase6_middleware.py`
- Verification for this session:
  - `python -m pytest -q tests/test_phase5_endpoints.py tests/test_phase6_middleware.py` ✅
  - `python -m ruff check app/api/v1/statements.py app/main.py app/core/config.py tests/test_phase5_endpoints.py tests/test_phase6_middleware.py` ✅

**What's running:**
- Backend: `uvicorn app.main:app --port 8001`
- Frontend: `cd frontend && npm run dev` on port 3000
- DB: PostgreSQL 18 on localhost:5432

**Next session should:**
1. Begin Phase 6B auth refresh flow (refresh endpoint + frontend token refresh behavior)
2. Add middleware/request ID observability assertions into broader integration suite
3. Run full repo quality gate (`ruff`, `mypy`, `pytest`, `tsc`) before next commit
