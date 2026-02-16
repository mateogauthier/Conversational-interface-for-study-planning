"""Auto-seeding service for academic data.

Loads pre-processed JSON seed files into MongoDB on startup.
Idempotent: skips seeding if data already exists.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import BulkWriteError

logger = logging.getLogger(__name__)

DEGREE_ID = "LIC-SIS-2019"
LEGACY_DEGREE_ID = "CS-ENG-2024"
SEED_DIR = Path(__file__).parent.parent.parent / "seed_data"


def _convert_datetimes(doc: dict) -> dict:
    """Convert ISO datetime strings to datetime objects in a document."""
    for key in ("created_at", "updated_at", "enrollment_date",
                "expected_graduation", "completion_date"):
        if key in doc and isinstance(doc[key], str):
            try:
                doc[key] = datetime.fromisoformat(doc[key])
            except (ValueError, TypeError):
                pass

    # Handle nested subject records
    for list_key in ("completed_subjects", "in_progress_subjects"):
        if list_key in doc and isinstance(doc[list_key], list):
            for record in doc[list_key]:
                if "completion_date" in record and isinstance(record["completion_date"], str):
                    try:
                        record["completion_date"] = datetime.fromisoformat(record["completion_date"])
                    except (ValueError, TypeError):
                        pass

    # Handle nested statistics
    if "statistics" in doc and isinstance(doc["statistics"], dict):
        stats = doc["statistics"]
        if "last_activity" in stats and isinstance(stats["last_activity"], str):
            try:
                stats["last_activity"] = datetime.fromisoformat(stats["last_activity"])
            except (ValueError, TypeError):
                pass

    return doc


async def cleanup_legacy_data(db: AsyncIOMotorDatabase) -> None:
    """Remove the legacy fake CS-ENG-2024 degree data if present."""
    existing = await db.degrees.find_one({"degree_id": LEGACY_DEGREE_ID})
    if not existing:
        return

    logger.info(f"Removing legacy {LEGACY_DEGREE_ID} fake degree data...")
    result_degree = await db.degrees.delete_one({"degree_id": LEGACY_DEGREE_ID})
    result_subjects = await db.degree_subjects.delete_many({"degree_id": LEGACY_DEGREE_ID})
    result_schooling = await db.student_schooling.delete_many({"degree_id": LEGACY_DEGREE_ID})
    result_plans = await db.student_plans.delete_many({"degree_id": LEGACY_DEGREE_ID})

    logger.info(
        f"Removed legacy data: {result_degree.deleted_count} degree, "
        f"{result_subjects.deleted_count} subjects, "
        f"{result_schooling.deleted_count} schooling records, "
        f"{result_plans.deleted_count} plans"
    )


async def seed_academic_data(db: AsyncIOMotorDatabase) -> None:
    """Seed academic data from JSON files if not already present.

    This function is idempotent: it checks if the LIC-SIS-2019 degree
    exists before seeding. Safe to call on every startup.
    """
    # Idempotency check
    existing = await db.degrees.find_one({"degree_id": DEGREE_ID})
    if existing:
        logger.info(f"Academic data already seeded (found degree {DEGREE_ID})")
        return

    if not SEED_DIR.exists():
        logger.warning(f"Seed data directory not found at {SEED_DIR}, skipping seed")
        return

    logger.info("Seeding academic data from JSON files...")

    try:
        # 1. Insert degree
        degree_path = SEED_DIR / "degree.json"
        if degree_path.exists():
            with open(degree_path, "r", encoding="utf-8") as f:
                degree_data = _convert_datetimes(json.load(f))
            await db.degrees.insert_one(degree_data)
            logger.info(f"Inserted degree: {DEGREE_ID}")
        else:
            logger.warning("degree.json not found, skipping degree seed")
            return

        # 2. Insert subjects
        subjects_path = SEED_DIR / "subjects.json"
        if subjects_path.exists():
            with open(subjects_path, "r", encoding="utf-8") as f:
                subjects = [_convert_datetimes(s) for s in json.load(f)]
            if subjects:
                await db.degree_subjects.insert_many(subjects)
                logger.info(f"Inserted {len(subjects)} subjects")
        else:
            logger.warning("subjects.json not found, skipping subjects seed")

        # 3. Insert users (skip duplicates with ordered=False)
        users_path = SEED_DIR / "users.json"
        if users_path.exists():
            with open(users_path, "r", encoding="utf-8") as f:
                users = [_convert_datetimes(u) for u in json.load(f)]
            if users:
                try:
                    result = await db.users.insert_many(users, ordered=False)
                    logger.info(f"Inserted {len(result.inserted_ids)} users")
                except BulkWriteError as e:
                    inserted = e.details.get("nInserted", 0)
                    logger.info(f"Inserted {inserted} users ({len(users) - inserted} already existed)")
        else:
            logger.warning("users.json not found, skipping users seed")

        # 4. Insert student schooling records
        schooling_path = SEED_DIR / "student_schooling.json"
        if schooling_path.exists():
            with open(schooling_path, "r", encoding="utf-8") as f:
                schooling = [_convert_datetimes(s) for s in json.load(f)]
            if schooling:
                try:
                    result = await db.student_schooling.insert_many(schooling, ordered=False)
                    logger.info(f"Inserted {len(result.inserted_ids)} student schooling records")
                except BulkWriteError as e:
                    inserted = e.details.get("nInserted", 0)
                    logger.info(
                        f"Inserted {inserted} schooling records "
                        f"({len(schooling) - inserted} already existed)"
                    )
        else:
            logger.warning("student_schooling.json not found, skipping schooling seed")

        logger.info("Academic data seeding complete!")

    except FileNotFoundError as e:
        logger.warning(f"Seed file not found: {e}")
    except Exception as e:
        logger.error(f"Error seeding academic data: {e}", exc_info=True)
