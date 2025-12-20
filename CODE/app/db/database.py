"""MongoDB database connection and session management."""

from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB connection singleton."""

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None

    async def connect(self):
        """Connect to MongoDB."""
        settings = get_settings()
        try:
            self.client = AsyncIOMotorClient(
                settings.mongo_uri,
                maxPoolSize=settings.mongo_max_pool_size,
                minPoolSize=settings.mongo_min_pool_size,
                serverSelectionTimeoutMS=5000
            )
            self.database = self.client[settings.mongo_database_name]

            # Verify connection
            await self.client.admin.command('ping')
            logger.info(
                f"Successfully connected to MongoDB database: {settings.mongo_database_name} "
                f"(pool size: {settings.mongo_min_pool_size}-{settings.mongo_max_pool_size})"
            )

        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    def get_database(self) -> AsyncIOMotorDatabase:
        """Get database instance."""
        if self.database is None:
            raise ConnectionError("Database not connected. Call connect() first.")
        return self.database


# Global MongoDB instance
mongodb = MongoDB()


async def get_database() -> AsyncIOMotorDatabase:
    """Dependency to get database instance."""
    return mongodb.get_database()


async def create_indexes():
    """Create database indexes for optimal query performance."""
    db = mongodb.get_database()

    try:
        # Academic system indexes
        logger.info("Creating indexes for academic collections...")

        # Degrees collection - unique degree_id
        await db.degrees.create_index("degree_id", unique=True)
        logger.info("✓ Created index on degrees.degree_id")

        # Degree subjects collection - composite index for degree + subject lookup
        await db.degree_subjects.create_index([("degree_id", 1), ("subject_id", 1)], unique=True)
        await db.degree_subjects.create_index([("degree_id", 1), ("semester_offered", 1)])
        logger.info("✓ Created indexes on degree_subjects")

        # Student schooling collection - composite index for student + degree lookup
        await db.student_schooling.create_index([("student_id", 1), ("degree_id", 1)], unique=True)
        await db.student_schooling.create_index("user_id")
        logger.info("✓ Created indexes on student_schooling")

        # Student plans collection - composite index for student + degree + active
        await db.student_plans.create_index([("student_id", 1), ("degree_id", 1), ("is_active", 1)], unique=True)
        await db.student_plans.create_index("user_id")
        logger.info("✓ Created indexes on student_plans")

        # Existing collections (if not already created)
        await db.users.create_index("auth0_id", unique=True)
        await db.file_metadata.create_index([("user_id", 1), ("filename", 1)], unique=True)
        await db.conversations.create_index([("auth0_id", 1), ("created_at", -1)])
        await db.messages.create_index([("conversation_id", 1), ("timestamp", 1)])

        logger.info("✅ All database indexes created successfully")

    except Exception as e:
        logger.warning(f"⚠️  Error creating indexes (may already exist): {e}")
