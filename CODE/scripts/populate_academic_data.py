"""Script to populate academic data from seed files.

Seeds the Licenciatura en Sistemas (Plan 2019) degree, subjects,
and student records from pre-processed JSON files.

Usage:
    docker exec study-planning-api python scripts/populate_academic_data.py
    # or locally:
    python scripts/populate_academic_data.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import mongodb
from app.services.seed_service import cleanup_legacy_data, seed_academic_data
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Populate database with real academic data."""
    try:
        await mongodb.connect()
        db = mongodb.get_database()

        # Remove old fake degree if present
        await cleanup_legacy_data(db)

        # Seed real data
        await seed_academic_data(db)

        logger.info("Done!")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise
    finally:
        await mongodb.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
