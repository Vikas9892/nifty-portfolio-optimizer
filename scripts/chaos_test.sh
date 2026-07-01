#!/usr/bin/env bash
# chaos_test.sh — automated smoke tests for failure scenarios (Phase 9 M9)
# Usage: bash scripts/chaos_test.sh <backend_url> <auth_token>

set -euo pipefail

BACKEND_URL="${1:-http://localhost:8000}"
TOKEN="${2:-}"
PASS=0
FAIL=0

log_pass() { echo "[PASS] $1"; ((PASS++)); }
log_fail() { echo "[FAIL] $1"; ((FAIL++)); }

check() {
    local desc="$1" url="$2" expected_status="$3"
    actual=$(curl -s -o /dev/null -w "%{http_code}" \
        ${TOKEN:+-H "Authorization: Bearer $TOKEN"} "$url")
    if [ "$actual" = "$expected_status" ]; then
        log_pass "$desc (HTTP $actual)"
    else
        log_fail "$desc — expected $expected_status, got $actual"
    fi
}

echo "=== Nifty Portfolio Chaos Tests ==="
echo "Target: $BACKEND_URL"
echo

# ── Scenario 0: Baseline ─────────────────────────────────────────────────────
echo "--- Scenario 0: Baseline health check"
check "GET /health returns 200" "$BACKEND_URL/health" "200"
check "GET /ready returns 200 (DB ok)" "$BACKEND_URL/ready" "200"

# ── Scenario 1: Kill Redis ────────────────────────────────────────────────────
echo
echo "--- Scenario 1: Redis failure (stop + verify + restore)"
docker compose stop redis 2>/dev/null || true
sleep 3

check "GET /health returns 200 (liveness unaffected)" "$BACKEND_URL/health" "200"
check "GET /ready returns 200 (Redis not a readiness dep)" "$BACKEND_URL/ready" "200"

docker compose start redis 2>/dev/null || true
sleep 5
echo "Redis restored."

# ── Scenario 2: SQLite missing ────────────────────────────────────────────────
echo
echo "--- Scenario 2: Database failure"
if [ -f "data/portfolio.db" ]; then
    mv data/portfolio.db data/portfolio.db.bak
    sleep 2
    check "GET /ready returns 503 (DB unreachable)" "$BACKEND_URL/ready" "503"
    check "GET /health returns 200 (liveness unaffected)" "$BACKEND_URL/health" "200"
    mv data/portfolio.db.bak data/portfolio.db
    echo "Database restored."
else
    echo "[SKIP] SQLite file not found — skipping DB failure test"
fi

# ── Scenario 3: DLQ endpoint (requires auth) ──────────────────────────────────
echo
echo "--- Scenario 3: DLQ endpoint"
if [ -n "$TOKEN" ]; then
    check "GET /api/v1/sre/dlq returns 200" "$BACKEND_URL/api/v1/sre/dlq" "200"
    check "GET /api/v1/sre/circuit-breakers returns 200" "$BACKEND_URL/api/v1/sre/circuit-breakers" "200"
    check "GET /api/v1/sre/feature-flags returns 200" "$BACKEND_URL/api/v1/sre/feature-flags" "200"
else
    echo "[SKIP] No TOKEN provided — skipping authenticated SRE endpoint tests"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo
echo "=== Results ==="
echo "Passed: $PASS"
echo "Failed: $FAIL"
[ "$FAIL" -eq 0 ] && echo "All chaos scenarios passed." && exit 0
echo "FAILURES DETECTED — investigate above." && exit 1
