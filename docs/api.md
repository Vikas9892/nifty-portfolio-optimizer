# API Reference

Base URL: `http://localhost:8000`  
Versioned prefix: `/api/v1/`  
Interactive docs: `http://localhost:8000/docs`

All protected endpoints require:
```
Authorization: Bearer <access_token>
```

All responses follow the envelope:
```json
{ "success": true, "message": "...", "data": { ... } }
```

Error responses:
```json
{ "success": false, "message": "...", "error_code": "AUTH_001" }
```

---

## Auth

### POST /api/v1/auth/register
Register a new user.

**Body**
```json
{ "name": "Alice", "email": "alice@example.com", "password": "Pass1234" }
```
Password rules: min 8 chars, at least one letter, at least one digit.

**Response 201**
```json
{
  "data": {
    "user": { "id": 1, "name": "Alice", "email": "alice@example.com", "is_active": true, "created_at": "..." },
    "tokens": { "access_token": "...", "refresh_token": "...", "token_type": "bearer", "expires_in": 900 }
  }
}
```

**Errors:** 409 Conflict (email taken) · 422 Validation error

---

### POST /api/v1/auth/login
```json
{ "email": "alice@example.com", "password": "Pass1234" }
```
**Response 200** — same shape as `/register`  
**Errors:** 401 (bad credentials) · 422

---

### GET /api/v1/auth/me
Returns the currently authenticated user.  
**Response 200** — `data: UserResponse`  
**Errors:** 401

---

### POST /api/v1/auth/refresh
```json
{ "refresh_token": "<rt>" }
```
**Response 200** — `data: TokenResponse` (new access + refresh pair)  
**Errors:** 401 (token invalid, expired, or reused)

---

### POST /api/v1/auth/logout
Revokes the refresh token for this session.
```json
{ "refresh_token": "<rt>" }
```
**Response 200**  
**Errors:** 401

---

## Portfolio

### POST /api/v1/portfolio/optimize  *(protected)*
Run a Markowitz mean-variance optimization.

**Body**
```json
{
  "stocks": ["TCS.NS", "INFY.NS", "RELIANCE.NS"],
  "start": "2020-01-01",
  "end": "2024-01-01",
  "max_weight": 0.30
}
```
- `stocks`: min 2 unique NSE tickers
- `max_weight`: 0.10–0.50 (max allocation per stock)
- Date range must be ≥ 1 year and not in the future

**Response 201**
```json
{
  "data": {
    "portfolio_id": 42,
    "expected_return": 0.187,
    "volatility": 0.213,
    "sharpe": 0.878,
    "basket_return": 0.19,
    "nifty_return": 0.12,
    "alpha": 0.07,
    "weights": { "TCS.NS": 0.35, "INFY.NS": 0.30, "RELIANCE.NS": 0.35 },
    "stocks_in_basket": 3,
    "stocks_with_weight": 3
  }
}
```

---

### GET /api/v1/portfolio/history  *(protected)*
All your saved optimizations, newest first.  
**Response 200** — `data: PortfolioListItem[]`

---

### GET /api/v1/portfolio/{id}  *(protected)*
Portfolio detail including weights.  
**Errors:** 403 (not owner) · 404

---

### DELETE /api/v1/portfolio/{id}  *(protected)*
**Errors:** 403 (not owner) · 404

---

## Stocks

### GET /api/v1/stocks
Returns all 50 available Nifty stocks with metadata.  
**Response 200** — `data: StockInfo[]`

---

## Benchmark

### POST /api/v1/benchmark/compare
Compare a custom portfolio against Nifty 50.

**Body**
```json
{
  "stocks": ["TCS.NS", "INFY.NS"],
  "weights": { "TCS.NS": 0.6, "INFY.NS": 0.4 },
  "start": "2020-01-01",
  "end": "2024-01-01"
}
```

---

## Observability

| Endpoint | Description |
|---|---|
| `GET /health` | Liveness — returns 200 if process is running |
| `GET /ready` | Readiness — returns 200 if DB is reachable |
| `GET /version` | Build version and environment |
