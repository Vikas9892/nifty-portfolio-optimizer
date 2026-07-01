# ADR 002 — Why SQLAlchemy Core (not ORM)

**Date:** 2026-07-02
**Status:** Accepted

## Problem

We need a DB layer that:
- Works with SQLite in development and PostgreSQL in production without code changes
- Gives fine-grained control over SQL for audit trails and complex joins
- Doesn't require a separate migration tool for a project of this size

## Options Considered

| Approach | Control | Portability | Complexity |
|----------|---------|-------------|-----------|
| SQLAlchemy Core (raw Table + expressions) | High | Excellent | Moderate |
| SQLAlchemy ORM (mapped classes) | Moderate | Excellent | High |
| Raw sqlite3 / psycopg2 | Full | Manual adapter | Low |
| Tortoise-ORM / SQLModel | ORM-level | asyncio-native | Moderate |

## Decision

**SQLAlchemy Core with raw Table definitions.** Reasons:

1. **Portability:** `create_engine` with the right URL handles SQLite ↔ PostgreSQL — zero code changes, only env var changes.
2. **Control:** We write explicit `INSERT`, `SELECT`, `UPDATE`, `DELETE` via Core expressions — no hidden N+1 queries.
3. **Simplicity:** No migration framework (Alembic) needed at this scale; `metadata.create_all()` handles table creation.
4. **Performance:** Core expressions compile to the same SQL as ORM but with less Python overhead.

## Consequences

- **Positive:** A single `get_engine()` call serves both environments transparently
- **Positive:** Every DB interaction is explicit — easy to add metrics or logging at the query level
- **Trade-off:** More boilerplate per CRUD operation vs. ORM. Acceptable given the small schema (6 tables)
- **Future:** If the schema grows beyond ~15 tables, migrate to ORM + Alembic migrations
