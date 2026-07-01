# ADR 004 — Why Repository Pattern

**Date:** 2026-07-02
**Status:** Accepted

## Problem

The portfolio service needs to:
- Persist and retrieve data from PostgreSQL (production) and SQLite (development)
- Be testable without a live database
- Not couple business logic to SQL syntax

## Options Considered

| Pattern | Testability | Decoupling | Boilerplate |
|---------|-------------|------------|-------------|
| Repository pattern | ✅ Easy to mock | ✅ Full | Moderate |
| Active Record (ORM) | Partial | ❌ | Low |
| Direct DB calls in service | ❌ Hard to test | ❌ | Low |
| DAO (Data Access Object) | ✅ | ✅ | High |

## Decision

**Repository pattern** with thin repository classes wrapping the `database.py` functions.

```
PortfolioService
    → PortfolioRepository  (interface: save / get_all / get_by_id / delete)
        → database.py      (SQL layer: SQLAlchemy Core)
```

## Consequences

- **Positive:** Tests monkeypatch `_db_module._engine` to a fresh SQLite file — no DB needed in CI
- **Positive:** `PortfolioService` reads like business logic, not SQL
- **Positive:** Swapping PostgreSQL for another DB only changes `database.py`, not services
- **Trade-off:** Extra layer of classes for a simple CRUD app — justified because it enabled Phase 6 test suite (95% service coverage without any network I/O)
