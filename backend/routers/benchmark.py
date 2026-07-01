from fastapi import APIRouter

from backend.schemas.benchmark import BenchmarkRequest, BenchmarkResponse
from backend.services.benchmark_service import BenchmarkService

router = APIRouter()
_service = BenchmarkService()


@router.post(
    "/",
    response_model=BenchmarkResponse,
    summary="Compare a custom basket against Nifty 50",
    description=(
        "Given a set of tickers and their weights, computes the annualized basket return "
        "and compares it against the Nifty 50 index (^NSEI). Returns alpha and whether the basket outperforms."
    ),
)
def compare(req: BenchmarkRequest) -> BenchmarkResponse:
    return _service.compare(req)
