# Contributing

Thank you for your interest in contributing. This guide gets you productive in under 10 minutes.

## Setup

```bash
git clone https://github.com/Vikas9892/nifty-portfolio-optimizer
cd nifty-portfolio-optimizer

# Install Python dependencies (includes dev tools)
pip install -r requirements.txt
pip install pytest pytest-cov httpx ruff black isort pre-commit

# Install pre-commit hooks (runs linting on every commit)
pre-commit install

# Install frontend dependencies
cd frontend && npm install && cd ..

# Copy environment file
cp .env.example .env
# Open .env and set JWT_SECRET_KEY to a random string
```

## Running the project

```bash
# Backend (port 8000)
python -m uvicorn backend.main:app --reload

# Frontend (port 3000, in a separate terminal)
cd frontend && npm run dev
```

## Running tests

```bash
# Backend — all tests + coverage
python -m pytest tests/ --cov=backend/app -q

# Frontend — all tests
cd frontend && npm test
```

Tests must pass before opening a PR. CI will enforce this automatically.

## Code style

| Tool | Command | What it does |
|---|---|---|
| ruff | `python -m ruff check backend/app/` | Linting |
| black | `python -m black backend/app/` | Formatting |
| isort | `python -m isort backend/app/` | Import order |
| tsc | `cd frontend && npm run lint` | TypeScript types |

Pre-commit runs all of these automatically on every `git commit`.

## Making a change

1. Create a branch: `git checkout -b feat/my-feature`
2. Write code + tests (tests first is preferred)
3. Run the full test suite locally
4. Commit (pre-commit hooks run automatically)
5. Push and open a pull request

## Pull request checklist

- [ ] New functionality has tests
- [ ] All existing tests pass (`pytest tests/ -q`)
- [ ] Linting is clean (`ruff check backend/app/`)
- [ ] The PR description explains *why*, not just *what*
- [ ] API changes are reflected in `docs/api.md`
- [ ] Breaking changes are noted in `CHANGELOG.md`

## Adding a new API endpoint

1. Add Pydantic schemas in `backend/app/schemas/`
2. Add business logic in `backend/app/services/`
3. Add DB queries in `backend/app/repositories/` (never raw SQL in services)
4. Wire up the FastAPI router in `backend/app/routers/`
5. Write unit tests for the service and integration tests for the route
6. Update `docs/api.md`

## Project structure

```
nifty-portfolio-optimizer/
├── backend/app/          # FastAPI application
│   ├── core/             # Config, security, JWT, dependencies
│   ├── middleware/        # Request logging
│   ├── models/           # SQLite DB layer
│   ├── repositories/     # Data access (called by services)
│   ├── routers/          # FastAPI route handlers
│   ├── schemas/          # Pydantic models
│   ├── services/         # Business logic
│   └── utils/            # Exceptions, logger
├── frontend/src/         # React + TypeScript
│   ├── components/       # Reusable UI
│   ├── context/          # Global state
│   ├── hooks/            # Custom hooks
│   ├── pages/            # Route-level components
│   └── services/         # API clients
├── tests/                # Backend test suite
├── docs/                 # Documentation
└── .github/workflows/    # CI/CD
```

## Questions?

Open a [GitHub Discussion](https://github.com/Vikas9892/nifty-portfolio-optimizer/discussions) or file an issue.
