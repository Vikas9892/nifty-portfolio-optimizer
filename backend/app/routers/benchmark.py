from fastapi import APIRouter, Depends

from backend.app.core.dependencies import get_current_user
from backend.app.schemas.auth import UserResponse
from backend.app.schemas.benchmark import BenchmarkRequest, BenchmarkResponse
from backend.app.schemas.response import SuccessResponse
from backend.app.services.benchmark_service import BenchmarkService

router = APIRouter(prefix="/api/v1/benchmark", tags=["Benchmark"])
_service = BenchmarkService()


@router.post(
    "/",
    response_model=SuccessResponse[BenchmarkResponse],
    summary="Compare a basket against Nifty 50",
    description="Given tickers + weights, computes annualized return vs Nifty 50 and alpha.",
)
def compare(
    req: BenchmarkRequest,
    _: UserResponse = Depends(get_current_user),
) -> SuccessResponse[BenchmarkResponse]:
    data = _service.compare(req)
    return SuccessResponse(message="Benchmark comparison complete.", data=data)
