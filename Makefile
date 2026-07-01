# ── Nifty Portfolio Optimizer — Developer Makefile ───────────────────────────
# make          → show help
# make dev      → start full stack (Docker, SQLite + Redis)
# make prod     → start production stack (PostgreSQL + Redis + Nginx)
# make test     → run all tests
# make lint     → lint + format checks

.PHONY: help dev up down build logs prod test lint clean backup

COMPOSE     = docker compose
COMPOSE_PROD = docker compose -f docker-compose.yml -f docker-compose.prod.yml

# ── Default: print help ───────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  Nifty Portfolio Optimizer"
	@echo ""
	@echo "  make dev         Start full stack locally (SQLite + Redis)"
	@echo "  make up          Start detached"
	@echo "  make down        Stop all containers"
	@echo "  make build       Rebuild images"
	@echo "  make logs        Tail logs"
	@echo "  make prod        Production stack (PostgreSQL + Nginx + Redis)"
	@echo "  make test        Run backend + frontend tests"
	@echo "  make lint        Ruff + black + tsc checks"
	@echo "  make clean       Remove containers + volumes"
	@echo "  make backup      Run manual DB backup"
	@echo ""

# ── Development ───────────────────────────────────────────────────────────────
dev:
	$(COMPOSE) up --build

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f

# ── Production ────────────────────────────────────────────────────────────────
prod:
	$(COMPOSE_PROD) up -d --build

prod-down:
	$(COMPOSE_PROD) down

prod-logs:
	$(COMPOSE_PROD) logs -f

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
	python -m pytest tests/ -q
	cd frontend && npm test

test-backend:
	python -m pytest tests/ -q --tb=short

test-frontend:
	cd frontend && npm test

test-cov:
	python -m pytest tests/ --cov=backend/app --cov-report=term-missing -q

# ── Lint ──────────────────────────────────────────────────────────────────────
lint:
	python -m ruff check backend/app/
	python -m black --check backend/app/ backend/main.py
	python -m isort --check-only backend/app/ backend/main.py
	cd frontend && npm run lint

# ── Maintenance ───────────────────────────────────────────────────────────────
clean:
	$(COMPOSE) down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true

backup:
	@./scripts/backup_db.sh
