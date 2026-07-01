# Nifty Portfolio Optimizer

A production-grade, full-stack **mean-variance portfolio optimizer** for the Nifty 50 universe.

**Backend**: FastAPI 0.111 · Python 3.11 · SQLAlchemy Core · PostgreSQL · Redis · RQ Workers · APScheduler · Prometheus  
**Frontend**: React 18 · TypeScript · Vite · Recharts  
**Infra**: Docker Compose · Nginx · Grafana · Alertmanager · JWT Auth

---

## Demo

> **Watch the walkthrough** (5–10 min):
> - Login / Register → Portfolio dashboard → Select Nifty 50 stocks
> - Optimize (async job) → Efficient frontier chart → Save portfolio
> - Redis cache hit vs. miss → Scheduler market refresh
> - Prometheus metrics → Grafana dashboard → Alertmanager rules
> - SRE endpoints: circuit breakers, feature flags, DLQ
>
> **[▶ Add demo video link here]** — Record with OBS or Loom, upload to YouTube/Loom, paste URL.
>
> *(M8 of the system design milestones — pending recording)*

---

## Documentation

| Document | Description |
|---|---|
| [System Design](docs/system_design.md) | High-level architecture, request flows, auth flow, all 8 sequence diagrams |
| [Low-Level Design](docs/low_level_design.md) | 12 design patterns with WHY — Repository, Strategy, Circuit Breaker, etc. |
| [Design Decisions](docs/design_decisions.md) | 11 ADRs: FastAPI, Redis, JWT, RQ, PostgreSQL, Circuit Breaker, Feature Flags |
| [Benchmarks](docs/benchmarks.md) | Real latency numbers: DB, JWT, Pydantic, PyPfOpt — measured locally |
| [System Evolution](docs/evolution.md) | v1 single script → v10 distributed system — what changed and why |
| [Production Checklist](docs/production_checklist.md) | 10-section deploy gate: HTTPS, secrets, monitoring, backup, alerting |
| [API Reference](docs/api.md) | All REST endpoints with request/response schemas |
| [Architecture Overview](docs/architecture.md) | High-level component diagram |
| [Reliability](docs/reliability.md) | SLOs, failure scenarios, circuit breaker policy, DLQ runbook |
| [Load Testing](docs/load_testing.md) | Locust results at 10/50/100/500/1000 concurrent users |
| [Capacity Planning](docs/capacity_planning.md) | Resource projections for 100/1k/10k users |
| [Disaster Recovery](docs/disaster_recovery.md) | RTO/RPO, backup restoration runbook |
| [Chaos Testing](docs/chaos_testing.md) | Fault injection scenarios and expected behavior |
| [Security Audit](docs/security_audit.md) | OWASP checklist, threat model, mitigations |
| [Cost Estimate](docs/cost_estimate.md) | AWS/GCP cost breakdown for 3 tiers of scale |
| [Deployment](docs/deployment.md) | Docker Compose, environment variables, production setup |
| [Testing](docs/testing.md) | Test strategy, coverage config, how to run |
| **Design Decisions /** | |
| [Why FastAPI](docs/decisions/001-why-fastapi.md) | FastAPI vs Flask/Django/Tornado |
| [Why SQLAlchemy Core](docs/decisions/002-why-sqlalchemy-core.md) | Core vs ORM |
| [Why Redis](docs/decisions/003-why-redis.md) | Cache + Queue + Flags + DLQ |
| [Why Repository Pattern](docs/decisions/004-why-repository-pattern.md) | Separation of SQL from business logic |
| [Why JWT](docs/decisions/005-why-jwt.md) | Stateless auth for horizontal scaling |
| [Why Background Jobs](docs/decisions/006-why-background-jobs.md) | RQ over Celery for async optimization |

---

## Quick Start (Full Stack — Docker)

```bash
git clone https://github.com/Vikas9892/nifty-portfolio-optimizer.git
cd nifty-portfolio-optimizer
cp .env.example .env          # fill in SECRET_KEY and DB credentials
docker compose up --build -d

# Verify:
curl http://localhost:8000/health/ready
# → {"status": "ready", "db": "ok", "redis": "ok"}

# Open frontend:
open http://localhost:3000
```

Services started: `api`, `frontend`, `nginx`, `postgres`, `redis`, `worker`, `prometheus`, `grafana`, `alertmanager`.

---

## Motivation

Selecting stocks individually ignores the covariance structure of returns. Two high-return stocks that move in lockstep provide no diversification benefit — they merely double your exposure. **Markowitz Mean-Variance Optimization** formalizes this: it finds the weight vector that maximizes risk-adjusted return across the full joint distribution of the asset basket, not just the marginal statistics of individual stocks.

This project applies that framework to the Nifty 50 universe with one production-relevant addition: **Ledoit-Wolf covariance shrinkage**, which stabilizes the covariance estimate when the number of assets is large relative to the observation window.

---

## Mathematical Foundation

### Objective

Maximize the **Sharpe Ratio**:

```
maximize:   (w' μ - r_f) / sqrt(w' Σ w)

subject to: Σ w_i = 1
            0 ≤ w_i ≤ w_max   ∀ i
```

Where:
- `w` — weight vector (the decision variable)
- `μ` — vector of annualized expected returns
- `Σ` — annualized covariance matrix of returns
- `r_f` — risk-free rate
- `w_max` — maximum allowed weight per stock (default 30%)

This is a **quasi-convex** problem. PyPortfolioOpt transforms it into an equivalent convex quadratic program and solves it via CVXPY.

### Expected Returns

```
μ_i = mean(r_i_daily) × 252
```

Mean historical return annualized by 252 trading days. Simple and backward-looking — appropriate for a backtesting framework.

### Covariance Matrix — Ledoit-Wolf Shrinkage

The sample covariance estimator `S = (1/T) X'X` is unbiased but **ill-conditioned** when `n` (assets) is non-trivial relative to `T` (observations). With 50 stocks and ~1,250 trading days, small estimation errors in the sample matrix get amplified during inversion, causing the optimizer to take extreme, unstable positions.

**Ledoit-Wolf shrinkage** regularizes this by pulling the sample matrix toward a structured target (a scaled identity):

```
Σ_shrunk = (1 - α) S + α μ_S I
```

Where `α` (the shrinkage intensity) is analytically optimal — minimizing the expected Frobenius norm between the estimator and the true covariance. This produces a well-conditioned matrix without requiring subjective parameter tuning.

### Annualization

- Returns: `× 252`
- Volatility: `× √252` (variance scales linearly with time; standard deviation scales with its square root)

### Monte Carlo Frontier

10,000 random weight vectors are sampled from a uniform Dirichlet distribution (`w = u / sum(u)`, where `u ~ Uniform(0,1)^n`) and mapped to (volatility, return) space. This approximates the **feasible set** — the cloud of all achievable portfolios — and the efficient frontier emerges as its upper-left boundary. The optimized portfolio is overlaid as a red star; its position at the top of the Sharpe gradient validates the optimizer's output.

---

## Stock Universe

Full Nifty 50 across 14 sectors. Users build any basket from this universe via the dashboard sidebar.

| Sector | Tickers |
|---|---|
| IT | TCS, INFY, HCLTECH, WIPRO, TECHM |
| Banking | HDFCBANK, ICICIBANK, SBIN, KOTAKBANK, AXISBANK, INDUSINDBK |
| Financial Services | BAJFINANCE, BAJAJFINSV, HDFCLIFE, SBILIFE |
| Energy | RELIANCE, ONGC, BPCL, NTPC, POWERGRID, COALINDIA |
| FMCG | HINDUNILVR, ITC, NESTLEIND, BRITANNIA, TATACONSUM |
| Pharma | SUNPHARMA, DRREDDY, CIPLA, DIVISLAB |
| Auto | MARUTI, TATAMOTORS, BAJAJ-AUTO, HEROMOTOCO, EICHERMOT, M&M |
| Metals & Mining | TATASTEEL, JSWSTEEL, HINDALCO |
| Cement | ULTRACEMCO, SHREECEM, GRASIM |
| Conglomerate / Infra | LT, ADANIPORTS, ADANIENT |
| Telecom | BHARTIARTL |
| Consumer | ASIANPAINT, TITAN |
| Healthcare | APOLLOHOSP |
| Agro / Chemicals | UPL |

The **default basket** is a curated 15-stock cross-sector selection. All 50 are available via the sidebar picker.

---

## Pipeline

```
yfinance.download()
    └─> pct_change()                    daily returns
            ├─> mean_historical_return()    μ vector
            ├─> CovarianceShrinkage         Σ matrix (Ledoit-Wolf)
            │       └─> EfficientFrontier.max_sharpe()   optimal w*
            ├─> Monte Carlo simulation      10,000 random portfolios
            └─> compare_with_nifty()        realized return vs ^NSEI
                    └─> render_dashboard()  Streamlit UI
```

Data quality: stocks with less than 80% price history over the selected window are dropped automatically. Remaining gaps are forward-filled.

---

## Implementation

**`download_prices()`** — fetches OHLCV via yfinance, retains `Close`, drops sparse columns, forward-fills gaps.

**`calculate_returns()`** — `pct_change().dropna()`. Daily log-returns would be more theoretically correct but arithmetic returns are standard for mean-variance inputs in practice.

**`optimize_portfolio()`** — computes `μ` and `Σ` (Ledoit-Wolf), constructs the `EfficientFrontier` object, adds the weight-cap constraint as a linear inequality, calls `max_sharpe()`, and returns cleaned weights with sub-threshold allocations zeroed out.

**`simulate_portfolios()`** — vectorized Monte Carlo; each iteration samples a random weight vector, computes annualized return and volatility, stores Sharpe. Returns a DataFrame of 10,000 portfolios.

**`compare_with_nifty()`** — applies optimized weights to actual daily returns to produce a realized basket return, then compares to the Nifty 50 index (`^NSEI`) over the same period.

**`render_dashboard()`** — Streamlit layout: 5 metric cards, weights table sorted by allocation, donut chart, correlation heatmap (annotation toggled off above 15 stocks for readability), frontier scatter.

---

## Tech Stack

| Library | Role |
|---|---|
| `yfinance` | Historical OHLCV data (NSE tickers via `.NS` suffix) |
| `PyPortfolioOpt` | Mean-variance optimization, covariance models, CVXPY backend |
| `pandas` / `numpy` | Return computation, Monte Carlo vectorization |
| `matplotlib` / `seaborn` | Static plots, correlation heatmap |
| `streamlit` | Interactive dashboard, sidebar controls |

---

## Setup

```bash
git clone https://github.com/Vikas9892/nifty-portfolio-optimizer.git
cd nifty-portfolio-optimizer
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Running

```bash
# CLI — downloads data, optimizes, saves plots to plots/
python app.py

# Interactive Streamlit dashboard
streamlit run app.py
```

The sidebar lets you select any subset of the Nifty 50 by sector, set the date range, adjust the weight cap, and control the Monte Carlo sample size.

---

## Output

### Dashboard Overview
![Dashboard Overview](plots/dashboard_overview.png)

### Efficient Frontier
![Efficient Frontier](plots/efficient_frontier.png)

### Correlation Heatmap
![Correlation Heatmap](plots/correlation_heatmap.png)

### Portfolio Allocation
![Portfolio Allocation](plots/portfolio_allocation.png)

---

## Limitations and Honest Trade-offs

| Limitation | Why it exists | What a production system would do |
|---|---|---|
| Backward-looking returns | Historical mean used as μ proxy | Factor models (Fama-French), analyst forecasts, or Black-Litterman |
| Normality assumption | MVO assumes Gaussian returns | CVaR optimization, t-distribution, or robust MVO |
| Single-period model | No rebalancing | Multi-period dynamic optimization or rolling window rebalance |
| No transaction costs | Clean backtest | Turnover penalty in the objective, realistic slippage model |
| Small universe | 50 stocks | Full NSE universe with factor-based pre-screening |
| Sample period sensitivity | Results vary by window | Walk-forward validation, out-of-sample testing |

These are deliberate scope decisions for a self-contained project, not oversights.

---

## Extensions Worth Building

- **Black-Litterman model** — blend market equilibrium returns with subjective views; removes the sensitivity to μ estimation that plagues classical MVO
- **Rolling backtest** — reoptimize quarterly, measure realized Sharpe out-of-sample; this is the honest test of whether the optimizer adds value
- **Risk-parity allocation** — allocate by equal risk contribution rather than mean-variance; performs better when return estimates are unreliable
- **CVaR optimization** — minimize Conditional Value at Risk instead of variance; more appropriate for fat-tailed equity return distributions
