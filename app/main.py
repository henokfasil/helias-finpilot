"""
Application entry point.

Initialises the database, optionally seeds data, then starts the Telegram bot.
"""
from __future__ import annotations

import logging
import os
import sys

import structlog

from app.config import settings
from app.database import init_db


def configure_logging() -> None:
    level = getattr(logging, settings.app_log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main() -> None:
    configure_logging()
    logger = logging.getLogger(__name__)

    logger.info("Helias FinPilot starting up…")
    logger.info("Environment: %s", settings.app_env)
    logger.info("Database: %s", settings.database_url)

    # Create tables
    init_db()

    # Auto-seed if DB is empty (first run)
    _maybe_seed()

    # Start bot
    from app.bot.bot import run
    run()


def _maybe_seed() -> None:
    """Seed default company and categories if the DB is empty."""
    from app.database import get_db_context
    from app.models.company import Company

    with get_db_context() as db:
        if not db.query(Company).first():
            import logging
            logging.getLogger(__name__).info("No company found — running seed…")
            # Import and run seed inline
            from scripts.seed_data import seed
            seed(db)


if __name__ == "__main__":
    main()
