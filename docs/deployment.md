# Deployment

## Local Development (one command)

```bash
# Clone
git clone https://github.com/Vikas9892/nifty-portfolio-optimizer
cd nifty-portfolio-optimizer

# Backend
pip install -r requirements.txt
cp .env.example .env          # edit JWT_SECRET_KEY
python -m uvicorn backend.main:app --reload

# Frontend (new terminal)
cd frontend && npm install && npm run dev
```

Open http://localhost:3000

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```ini
APP_NAME="Nifty Portfolio Optimizer"
ENVIRONMENT=development

# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=<your-secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

DATABASE_URL=data/portfolio.db

RATE_LIMIT_LOGIN=5/minute
RATE_LIMIT_REGISTER=3/minute
RATE_LIMIT_OPTIMIZE=10/minute
```

Frontend `.env`:
```ini
VITE_API_URL=http://localhost:8000
```

## Production Checklist

- [ ] Generate a strong `JWT_SECRET_KEY` (32+ random bytes)
- [ ] Set `ENVIRONMENT=production`
- [ ] Run behind HTTPS (nginx, Caddy, or cloud LB)
- [ ] Set `allow_origins` in `backend/main.py` to your actual frontend domain
- [ ] Use a persistent volume for `data/portfolio.db`
- [ ] Set up log aggregation (the backend uses structured Python `logging`)

## Docker (coming in Phase 7)

A `docker-compose.yml` will be added in Phase 7 to bring up the full stack with one command:

```bash
docker-compose up --build
```
