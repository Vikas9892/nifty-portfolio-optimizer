"""APScheduler integration — market data refresh with distributed locking (M5)."""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.app.utils.logger import logger

_scheduler: AsyncIOScheduler | None = None


async def _refresh_market_data() -> None:
    """
    Pull latest close prices for Nifty 50 top holdings after market close.

    M5: acquires a distributed Redis lock so that only one replica refreshes
    market data at a time when multiple FastAPI instances are running.
    NSE closes at 15:30 IST; data is typically available by 13:30 UTC.
    """
    from backend.app.services.distributed_lock import acquire_lock

    # Lock TTL = 600s — comfortably covers the full refresh window
    with acquire_lock("market-refresh", ttl=600) as acquired:
        if not acquired:
            logger.info("SCHEDULER | skipped — another replica holds the market-refresh lock")
            return

        await _do_refresh()


async def _do_refresh() -> None:
    DEFAULT_TICKERS = [
        "RELIANCE.NS",
        "TCS.NS",
        "HDFCBANK.NS",
        "INFY.NS",
        "ICICIBANK.NS",
        "HINDUNILVR.NS",
        "KOTAKBANK.NS",
        "BHARTIARTL.NS",
        "ITC.NS",
        "AXISBANK.NS",
    ]
    try:
        import datetime

        from src.data_service import get_prices

        end = datetime.date.today().isoformat()
        start = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
        prices = get_prices(tickers=DEFAULT_TICKERS, start=start, end=end)
        logger.info(
            "SCHEDULER | market_refresh done — %d tickers, %d rows",
            len(prices.columns),
            len(prices),
        )
        from backend.app.services.cache_service import cache

        cache.delete("stocks:universe")
    except Exception as exc:
        logger.error("SCHEDULER | market_refresh failed: %s", exc, exc_info=True)


def start_scheduler(hour: int = 13, minute: int = 30) -> AsyncIOScheduler:
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="UTC")

    _scheduler.add_job(
        _refresh_market_data,
        "cron",
        day_of_week="mon-fri",
        hour=hour,
        minute=minute,
        id="market_refresh",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    logger.info("SCHEDULER | started — market refresh weekdays at %02d:%02d UTC", hour, minute)
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("SCHEDULER | stopped")
