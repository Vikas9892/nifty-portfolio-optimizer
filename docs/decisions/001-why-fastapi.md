# ADR 001 — Why FastAPI

**Date:** 2026-07-02
**Status:** Accepted

## Problem

We needed a Python web framework capable of serving a real-time portfolio optimizer that:
- Has built-in async support for non-blocking I/O
- Auto-generates OpenAPI docs (important for dev UX)
- Has a strong Pydantic integration for request validation
- Is production-grade with high throughput

## Options Considered

| Framework | Async | Auto-docs | Validation | Perf |
|-----------|-------|-----------|------------|------|
| FastAPI   | ✅    | ✅ (built-in) | ✅ Pydantic | Very high |
| Flask     | ❌ (WSGI) | ❌ | Manual | Moderate |
| Django REST| ❌   | Partial  | Serializers | Moderate |
| Litestar  | ✅    | ✅        | ✅         | Very high |

## Decision

**FastAPI.** It gives us:
- `async def` route handlers out of the box — critical for the job polling endpoint
- Pydantic v2 models for all schemas — eliminates a class of bugs at the boundary
- Interactive Swagger UI at `/docs` — developers can test without Postman
- Native dependency injection — clean auth, rate-limit, and DB injection
- `Starlette` underneath — production-proven ASGI server

## Consequences

- **Positive:** 3-5× lower response time vs. WSGI frameworks under load (see Locust results)
- **Positive:** Schema validation errors surface at the HTTP boundary, not deep in business logic
- **Trade-off:** Python async is single-threaded — CPU-bound optimization runs in a worker process (solved by Phase 8 job system)
