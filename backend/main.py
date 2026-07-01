from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.routers import benchmark, portfolio, stocks


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Nifty Portfolio Optimizer API",
    description=(
        "REST API for mean-variance portfolio optimization over the Nifty 50 universe.\n\n"
        "Business logic is fully decoupled from the frontend — the same endpoints can power "
        "the Streamlit dashboard, a React app, a mobile client, or a CLI tool."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks.router, prefix="/stocks", tags=["Stocks"])
app.include_router(portfolio.router, tags=["Portfolio"])
app.include_router(benchmark.router, prefix="/benchmark", tags=["Benchmark"])


@app.get("/", tags=["Health"], summary="Health check")
def health():
    return {"status": "ok", "version": "1.0.0", "docs": "/docs"}
