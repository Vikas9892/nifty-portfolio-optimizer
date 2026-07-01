# ADR 005 — Why JWT (with refresh token rotation)

**Date:** 2026-07-02
**Status:** Accepted

## Problem

We need authentication that:
- Works across multiple backend replicas (Phase 8: load-balanced FastAPI × 2)
- Doesn't require a DB lookup on every request (performance)
- Can be revoked when users log out

## Options Considered

| Mechanism | Stateless | Revocable | Multi-replica | Complexity |
|-----------|-----------|-----------|---------------|------------|
| JWT (access + refresh) | ✅ | ✅ (via DB) | ✅ | Moderate |
| Session cookies (server-side) | ❌ | ✅ | ❌ without shared store | Low |
| Opaque tokens (DB lookup) | ❌ | ✅ | ✅ | Low |
| API keys | ✅ | ✅ | ✅ | Low — but no expiry |

## Decision

**JWT with short-lived access tokens (15 min) + long-lived refresh tokens (7 days).**

- Access token: stateless, validated by signature — zero DB hits on protected endpoints
- Refresh token: stored as a hash in the DB — revocable at logout or device compromise
- Rotation: each refresh call issues a new refresh token and revokes the old one (single-use)

## Consequences

- **Positive:** Multiple FastAPI replicas behind a load balancer work without shared session state
- **Positive:** Access token expiry limits the blast radius of a leaked token to 15 minutes
- **Positive:** Frontend auto-refresh queue (`api.ts`) handles 401 → silent token refresh without user interruption
- **Trade-off:** Access tokens cannot be revoked mid-flight (15 min window). Mitigated by short TTL
- **Trade-off:** Refresh token DB lookup adds one query per session renewal — acceptable at this scale
