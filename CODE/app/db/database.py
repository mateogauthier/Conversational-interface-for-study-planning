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
            self.client = AsyncIOMotorClient(settings.mongo_uri)
            self.database = self.client[settings.mongo_database_name]

            # Verify connection
            await self.client.admin.command('ping')
            logger.info(f"Successfully connected to MongoDB database: {settings.mongo_database_name}")

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
