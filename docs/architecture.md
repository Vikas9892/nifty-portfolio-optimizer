# Architecture

## Overview

```
┌─────────────────────────────────────────────┐
│                  React (Vite)               │
│  AuthContext ── PortfolioContext            │
│  ProtectedRoute → Layout → Pages           │
│  Axios interceptors (JWT + auto-refresh)   │
└───────────────────┬─────────────────────────┘
                    │ HTTPS / JSON
┌───────────────────▼─────────────────────────┐
│           FastAPI  (backend/main.py)        │
│  CORS ── RequestLogging ── SlowAPI          │
│  /api/v1/auth  /api/v1/portfolio            │
│  /api/v1/stocks  /api/v1/benchmark         │
│  /health  /ready  /version                 │
└─────────┬───────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────┐
│            Service Layer                    │
│  AuthService ── PortfolioService            │
│  BenchmarkService ── StocksService          │
└─────────┬───────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────┐
│          Repository Layer                   │
│  UserRepository ── TokenRepository          │
│  AuditRepository ── PortfolioRepository     │
└─────────┬───────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────┐
│      SQLite  (data/portfolio.db)            │
│  users  refresh_tokens  audit_logs          │
│  portfolios  portfolio_weights  prices      │
└─────────────────────────────────────────────┘
```

## Backend Layers

| Layer | Location | Responsibility |
|---|---|---|
| Routers | `backend/app/routers/` | HTTP parsing, authentication dependency injection |
| Services | `backend/app/services/` | Business logic, orchestration, audit logging |
| Repositories | `backend/app/repositories/` | DB queries, domain exceptions |
| Models/DB | `backend/app/models/database.py` | Raw SQL CRUD |
| Schemas | `backend/app/schemas/` | Pydantic request/response models |
| Core | `backend/app/core/` | JWT, bcrypt, config, FastAPI dependencies |

## Frontend Layers

| Layer | Location | Responsibility |
|---|---|---|
| Pages | `frontend/src/pages/` | Route-level components |
| Components | `frontend/src/components/` | Reusable UI primitives and charts |
| Hooks | `frontend/src/hooks/` | Stateful logic, data fetching |
| Context | `frontend/src/context/` | Global state (auth, portfolio, theme) |
| Services | `frontend/src/services/` | Axios wrappers for each API resource |

## Key Design Decisions

### Repository Pattern
Services never write SQL. They call repositories, which call the DB module. This means:
- Business logic is unit-testable without a database
- SQL lives in one place, making schema changes easy

### JWT + Refresh Token Rotation
- Access tokens expire in 15 minutes (short-lived → low blast radius if stolen)
- Refresh tokens are single-use (rotated on every use → replay attacks are detected)
- Refresh tokens are stored as SHA-256 hashes — even if the DB is stolen, tokens can't be used

### SuccessResponse Envelope
Every API response is wrapped as `{"success": true, "message": "...", "data": T}`.  
The Axios response interceptor transparently unwraps this so service calls receive `T` directly.

### Test Isolation
Unit and integration tests redirect SQLite to a fresh `tmp_path` file using `monkeypatch`,
so no test can pollute another and no test touches `data/portfolio.db`.
