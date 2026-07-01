from fastapi import APIRouter

from backend.schemas.portfolio import (
    DeleteResponse,
    OptimizeRequest,
    OptimizeResponse,
    PortfolioDetail,
    PortfolioListItem,
)
from backend.services.portfolio_service import PortfolioService

router = APIRouter()
_service = PortfolioService()


@router.post(
    "/optimize",
    response_model=OptimizeResponse,
    summary="Run portfolio optimization",
    description=(
        "Fetches price data (from cache where available), runs mean-variance optimization "
        "with Ledoit-Wolf covariance shrinkage, benchmarks against Nifty 50, and persists the result."
    ),
)
def optimize(req: OptimizeRequest) -> OptimizeResponse:
    return _service.optimize(req)


@router.get(
    "/history",
    response_model=list[PortfolioListItem],
    summary="List all past optimizations",
    description="Returns every saved optimization run, newest first. Weights are omitted for brevity.",
)
def history() -> list[PortfolioListItem]:
    return _service.get_history()


@router.get(
    "/portfolio/{portfolio_id}",
    response_model=PortfolioDetail,
    summary="Get a portfolio by ID",
    description="Returns the full detail of one optimization run, including per-ticker weights.",
)
def get_portfolio(portfolio_id: int) -> PortfolioDetail:
    return _service.get_by_id(portfolio_id)


@router.delete(
    "/portfolio/{portfolio_id}",
    response_model=DeleteResponse,
    summary="Delete a saved portfolio",
)
def delete_portfolio(portfolio_id: int) -> DeleteResponse:
    return _service.delete(portfolio_id)
