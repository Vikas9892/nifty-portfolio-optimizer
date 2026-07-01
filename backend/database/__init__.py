from src import database as _db


def init_db() -> None:
    """Create all tables on startup if they don't already exist."""
    _db.create_tables()
