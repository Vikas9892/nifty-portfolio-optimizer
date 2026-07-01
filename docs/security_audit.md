# Security Audit

*Last reviewed: 2026-07-02*

---

## 1. Authentication & Authorization

| Check | Status | Notes |
|---|---|---|
| JWT signed with HS256 | ✅ | Secret via `JWT_SECRET_KEY` env var — never hardcoded |
| Access token TTL | ✅ | 15 minutes — short-lived |
| Refresh token TTL | ✅ | 7 days — rotated on each use |
| Refresh token stored in DB | ✅ | Hash stored, not plaintext |
| Protected endpoints require Bearer token | ✅ | `Depends(get_current_user)` on all sensitive routes |
| Password hashed with bcrypt | ✅ | `passlib[bcrypt]` |
| No passwords in logs | ✅ | Only email/user_id logged |

**Recommendation:** Rotate `JWT_SECRET_KEY` every 90 days in production.

---

## 2. Input Validation

| Check | Status | Notes |
|---|---|---|
| Pydantic v2 models on all request bodies | ✅ | Type-safe validation at API boundary |
| Ticker symbols validated (format check) | ⚠️ | Basic check only — no whitelist |
| Date range validated (start < end) | ✅ | Pydantic validator |
| SQL injection | ✅ | SQLAlchemy Core parameterized queries only |
| Path traversal | ✅ | No file paths from user input |

**Recommendation:** Add ticker symbol whitelist against Nifty 500 universe.

---

## 3. CORS

| Check | Status | Notes |
|---|---|---|
| Origins whitelist | ✅ | `CORS_ORIGINS` env var; default: localhost only |
| Credentials allowed | ✅ | Required for cookie-based refresh tokens |
| All methods allowed | ✅ | Required for full REST support |

**Recommendation:** In production, set `CORS_ORIGINS` to your exact frontend domain only.

---

## 4. Rate Limiting

| Endpoint | Limit | Notes |
|---|---|---|
| POST /auth/login | 5/min | Brute-force protection |
| POST /auth/register | 3/min | Spam protection |
| POST /jobs/optimize | 10/min (user), 100/min (premium) | Cost control |
| All other | 200/min | Global default |

Rate limiting via `slowapi` (Redis-backed in prod, in-memory in dev).

---

## 5. Secrets Management

| Secret | Where stored | Notes |
|---|---|---|
| `JWT_SECRET_KEY` | `.env` file / env var | Never committed to git (`.gitignore`) |
| `DATABASE_URL` | `.env` file / env var | Contains password — never logged |
| `REDIS_URL` | `.env` file / env var | Never logged |
| `SMTP_PASS` | `.env` / alertmanager template var | Not committed |
| `SLACK_WEBHOOK_URL` | `.env` / alertmanager template var | Not committed |

Verify: `git log --all --full-history -- "**/.env"` should show no `.env` commits.

---

## 6. Security Headers

Recommended additions (add via Nginx or a middleware):

```nginx
add_header X-Content-Type-Options nosniff;
add_header X-Frame-Options DENY;
add_header Referrer-Policy strict-origin-when-cross-origin;
add_header Permissions-Policy "geolocation=(), microphone=()";
```

**Current status:** Not yet implemented as FastAPI middleware. Nginx config can be added.

---

## 7. Dependency Audit

Run before each release:

```bash
pip install pip-audit
pip-audit -r requirements.txt
```

**Known pattern:** Yahoo Finance (`yfinance`) pulls in many transitive dependencies.
Pin versions in `requirements.txt` and audit before major upgrades.

---

## 8. Data Privacy

- Portfolios are user-scoped: queries always filter by `user_id`
- No PII beyond email + name stored
- Refresh tokens are hashed (bcrypt) — raw token never stored
- Logs do not contain passwords or tokens

---

## 9. Threat Model (Top 5)

| Threat | Likelihood | Impact | Mitigated by |
|---|---|---|---|
| Brute-force login | High | High | Rate limiting (5/min), bcrypt |
| Token theft (XSS) | Medium | High | Short TTL (15min), httpOnly cookie for refresh |
| SSRF via ticker URL | Low | Medium | No user-controlled URLs in code |
| DoS via heavy optimize | Medium | Medium | Rate limiting, async queue, circuit breaker |
| Secret leak via env | Low | Critical | `.gitignore`, env-only secrets |
