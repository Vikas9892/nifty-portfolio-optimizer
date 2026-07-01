"""
Nifty Portfolio Optimizer — Load Test (Milestone 17)
=====================================================

Measures API performance under realistic concurrent load.

Usage:
    locust -f locustfile.py --host=http://localhost:8000

Then open http://localhost:8089 to control the swarm.

CLI (headless):
    locust -f locustfile.py --host=http://localhost:8000 \\
           --users=100 --spawn-rate=10 --run-time=60s --headless

Targets (based on Milestone 17):
  100 users  — p95 latency <  200 ms on GET endpoints
  500 users  — p95 latency <  500 ms on GET endpoints
  1000 users — error rate  <  1 %
"""
from __future__ import annotations

import random
import uuid

from locust import HttpUser, between, events, task


NIFTY_TICKERS = [
    "TCS.NS", "INFY.NS", "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "WIPRO.NS", "AXISBANK.NS", "HINDUNILVR.NS", "ITC.NS", "BHARTIARTL.NS",
    "KOTAKBANK.NS", "HCLTECH.NS", "LT.NS", "SBIN.NS", "MARUTI.NS",
]


class PortfolioUser(HttpUser):
    """Simulates a real user: register → browse → optimize → check history."""

    wait_time = between(1, 3)

    _access_token: str | None = None
    _portfolio_ids: list[int]

    def on_start(self) -> None:
        """Called once per simulated user at spawn time."""
        self._portfolio_ids = []
        email = f"load_{uuid.uuid4().hex[:8]}@locust.io"

        r = self.client.post(
            "/api/v1/auth/register",
            json={"name": "Locust User", "email": email, "password": "Locust123"},
            name="/api/v1/auth/register",
        )
        if r.status_code == 201:
            tokens = r.json().get("data", {}).get("tokens", {})
            self._access_token = tokens.get("access_token")

    def _auth(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}"} if self._access_token else {}

    # ── Read-heavy endpoints (weighted high) ───────────────────────────────────

    @task(8)
    def health(self) -> None:
        self.client.get("/health", name="/health")

    @task(5)
    def get_history(self) -> None:
        self.client.get("/api/v1/portfolio/history", headers=self._auth(), name="/api/v1/portfolio/history")

    @task(4)
    def get_stocks(self) -> None:
        self.client.get("/api/v1/stocks/universe", headers=self._auth(), name="/api/v1/stocks/universe")

    @task(2)
    def get_metrics(self) -> None:
        self.client.get("/api/v1/admin/metrics", headers=self._auth(), name="/api/v1/admin/metrics")

    # ── Write endpoints (weighted lower — expensive) ───────────────────────────

    @task(1)
    def queue_optimize(self) -> None:
        stocks = random.sample(NIFTY_TICKERS, k=random.randint(3, 6))
        r = self.client.post(
            "/api/v1/jobs/optimize",
            json={
                "stocks": stocks,
                "start": "2020-01-01",
                "end": "2023-12-31",
                "max_weight": 0.30,
            },
            headers=self._auth(),
            name="/api/v1/jobs/optimize",
        )
        if r.status_code == 202:
            job_id = r.json().get("data", {}).get("job_id")
            if job_id:
                # Poll once (don't spin — this is load testing, not a real client)
                self.client.get(
                    f"/api/v1/jobs/{job_id}",
                    headers=self._auth(),
                    name="/api/v1/jobs/{job_id}",
                )


# ── Events — print summary stats ──────────────────────────────────────────────

@events.quitting.add_listener
def on_quit(environment, **_kwargs) -> None:
    stats = environment.runner.stats
    total = stats.total
    print("\n" + "=" * 60)
    print(f"  Requests : {total.num_requests}")
    print(f"  Failures : {total.num_failures}")
    print(f"  RPS      : {total.current_rps:.1f}")
    print(f"  p50 ms   : {total.get_response_time_percentile(0.50):.0f}")
    print(f"  p95 ms   : {total.get_response_time_percentile(0.95):.0f}")
    print(f"  p99 ms   : {total.get_response_time_percentile(0.99):.0f}")
    print("=" * 60)
