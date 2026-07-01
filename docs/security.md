# Security

## Authentication Flow

```
Client                               Server
  │                                    │
  │  POST /api/v1/auth/register        │
  │  {"name","email","password"}  ──►  │  bcrypt(password, cost=12)
  │  ◄──  {access_token, refresh_token}│  JWT(sub=user_id, exp=15min)
  │                                    │  save SHA256(refresh_token) in DB
  │                                    │
  │  GET /api/v1/portfolio/history     │
  │  Authorization: Bearer <at>   ──►  │  decode JWT → user_id
  │  ◄──  [{...portfolios...}]         │  query portfolios WHERE user_id=?
  │                                    │
  │  POST /api/v1/auth/refresh         │
  │  {"refresh_token": "<rt>"}    ──►  │  SHA256(rt) → lookup DB
  │  ◄──  {new_access, new_refresh}    │  revoke old rt, issue new pair
```

## Password Hashing

Uses `bcrypt` directly (not `passlib`), which is incompatible with bcrypt 4.x on Python 3.13.

- Work factor: auto-negotiated by `bcrypt.gensalt()` (default 12 rounds)
- Passwords are never stored or logged in plaintext
- `verify_password` uses constant-time comparison to prevent timing attacks

## JWT

- Algorithm: HS256 (configurable via `.env`)
- Access token lifetime: 15 minutes
- Payload: `{"sub": user_id, "email": email, "type": "access", "exp": ...}`
- Secret: must be a long random string in production — never commit it

## Refresh Token Rotation

Refresh tokens are:
1. Generated as `secrets.token_urlsafe(48)` (cryptographically secure, 64-char opaque string)
2. Stored in the database as `SHA-256(raw_token)` — the raw token is never persisted
3. Single-use: revoked immediately when used to issue a new pair
4. Expired: valid for 7 days (configurable)

If a refresh token is reused after rotation, the server returns 401. This detects token theft.

## Rate Limiting

Implemented via `slowapi` (token bucket per IP):

| Endpoint | Limit |
|---|---|
| `POST /register` | 3 / minute |
| `POST /login` | 5 / minute |
| `POST /optimize` | 10 / minute |
| Everything else | 200 / minute |

## Authorization

Every portfolio endpoint checks ownership:

```python
owner = db.get_portfolio_owner(portfolio_id)
if owner != current_user.id:
    raise AuthorizationError("You don't own this portfolio.")
```

`owner is None` (legacy portfolios) is treated as "not owned by you" — there is no "public" portfolio.

## Audit Log

Every authentication event writes a row to `audit_logs`:
- `USER_REGISTERED` — email, IP
- `LOGIN_SUCCESS` — user_id, IP
- `LOGIN_FAILED` — email, IP (for brute-force detection)
- `TOKEN_REFRESHED` — user_id
- `LOGOUT` / `LOGOUT_ALL_SESSIONS` — user_id
- `PORTFOLIO_CREATED` / `PORTFOLIO_DELETED` — user_id, portfolio_id

## Environment Variables

Never commit secrets. Use `.env` (gitignored):

```ini
JWT_SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
```

The `.env` file is listed in `.gitignore`. CI uses GitHub Actions secrets.
