#!/usr/bin/env python3
"""Initialize MongoDB indexes for the Study Planning API."""

import asyncio
import logging
import sys
from motor.motor_asyncio import AsyncIOMotorClient

# Add parent directory to path to import app modules
sys.path.insert(0, '/app')

from app.core.config import get_settings
from app.db.collections import USERS_COLLECTION, FILE_METADATA_COLLECTION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_indexes():
    """Create MongoDB indexes for optimal performance."""
    settings = get_settings()

    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(settings.mongo_uri)
        db = client[settings.mongo_database_name]

        logger.info(f"Connected to MongoDB: {settings.mongo_database_name}")

        # Users collection indexes
        users_collection = db[USERS_COLLECTION]

        # Unique index on auth0_id for fast lookups
        await users_collection.create_index("auth0_id", unique=True)
        logger.info("✓ Created unique index on users.auth0_id")

        # Unique index on email
        await users_collection.create_index("email", unique=True)
        logger.info("✓ Created unique index on users.email")

        # Index on role for filtering
        await users_collection.create_index("role")
        logger.info("✓ Created index on users.role")

        # Index on created_at for sorting
        await users_collection.create_index("created_at")
        logger.info("✓ Created index on users.created_at")

        # File metadata collection indexes
        files_collection = db[FILE_METADATA_COLLECTION]

        # Unique index on filename
        await files_collection.create_index("filename", unique=True)
        logger.info("✓ Created unique index on file_metadata.filename")

        # Index on user_id for fast user file lookups
        await files_collection.create_index("user_id")
        logger.info("✓ Created index on file_metadata.user_id")

        # Index on is_public for filtering public files
        await files_collection.create_index("is_public")
        logger.info("✓ Created index on file_metadata.is_public")

        # Compound index for efficient queries (user_id + is_public)
        await files_collection.create_index([("user_id", 1), ("is_public", 1)])
        logger.info("✓ Created compound index on file_metadata.(user_id, is_public)")

        # Index on uploaded_at for sorting
        await files_collection.create_index("uploaded_at")
        logger.info("✓ Created index on file_metadata.uploaded_at")

        logger.info("\n✅ MongoDB indexes created successfully!")

        # Close connection
        client.close()

    except Exception as e:
        logger.error(f"❌ Error creating indexes: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(create_indexes())
