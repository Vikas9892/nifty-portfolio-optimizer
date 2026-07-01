from fastapi import APIRouter, Depends, status

from backend.app.core.dependencies import get_current_user
from backend.app.schemas.auth import UserResponse
from backend.app.schemas.portfolio import (
    DeleteResponse,
    OptimizeRequest,
    OptimizeResponse,
    PortfolioDetail,
    PortfolioListItem,
)
from backend.app.schemas.response import SuccessResponse
from backend.app.services.portfolio_service import PortfolioService

router = APIRouter(prefix="/api/v1/portfolio", tags=["Portfolio"])
_service = PortfolioService()


@router.post(
    "/optimize",
    response_model=SuccessResponse[OptimizeResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Run portfolio optimization",
    description=(
        "Fetches price data (SQLite cache first, Yahoo Finance on miss), "
        "runs Markowitz mean-variance optimization with Ledoit-Wolf covariance, "
        "benchmarks against Nifty 50, and persists the result linked to your account."
    ),
)
def optimize(
    req: OptimizeRequest,
    current_user: UserResponse = Depends(get_current_user),
) -> SuccessResponse[OptimizeResponse]:
    data = _service.optimize(req, current_user)
    return SuccessResponse(message="Portfolio optimized successfully.", data=data)


@router.get(
    "/history",
    response_model=SuccessResponse[list[PortfolioListItem]],
    summary="List your past optimizations",
    description="Returns all your saved optimization runs, newest first.",
)
def history(
    current_user: UserResponse = Depends(get_current_user),
) -> SuccessResponse[list[PortfolioListItem]]:
    data = _service.get_history(current_user)
    return SuccessResponse(message=f"{len(data)} portfolio(s) found.", data=data)


@router.get(
    "/{portfolio_id}",
    response_model=SuccessResponse[PortfolioDetail],
    summary="Get a portfolio by ID",
    description="Returns full detail including weights. Only accessible by the owner.",
)
def get_portfolio(
    portfolio_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> SuccessResponse[PortfolioDetail]:
    data = _service.get_by_id(portfolio_id, current_user)
    return SuccessResponse(message="Portfolio fetched.", data=data)


@router.delete(
    "/{portfolio_id}",
    response_model=SuccessResponse[DeleteResponse],
    summary="Delete a portfolio",
    description="Permanently deletes a portfolio. Only the owner can delete.",
)
def delete_portfolio(
    portfolio_id: int,
    current_user: UserResponse = Depends(get_current_user),
) -> SuccessResponse[DeleteResponse]:
    data = _service.delete(portfolio_id, current_user)
    return SuccessResponse(message=data.message, data=data)
