"""User service for user management and statistics."""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.db.models import UserInDB, UserStatistics, FileMetadataInDB
from app.db.collections import USERS_COLLECTION, FILE_METADATA_COLLECTION
from app.core.exceptions import UserNotFoundException

logger = logging.getLogger(__name__)


class UserService:
    """Service for user-related operations."""

    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.users_collection = database[USERS_COLLECTION]
        self.files_collection = database[FILE_METADATA_COLLECTION]

    async def get_user_by_id(self, user_id: str) -> UserInDB:
        """
        Get user by MongoDB ID.

        Args:
            user_id: MongoDB user ID (ObjectId as string)

        Returns:
            UserInDB: User document

        Raises:
            UserNotFoundException: If user not found
        """
        try:
            object_id = ObjectId(user_id)
        except Exception:
            raise UserNotFoundException(f"Invalid user ID format: {user_id}")

        user_doc = await self.users_collection.find_one({"_id": object_id})

        if not user_doc:
            raise UserNotFoundException(f"User with ID {user_id} not found")

        return UserInDB(**user_doc)

    async def get_user_by_auth0_id(self, auth0_id: str) -> Optional[UserInDB]:
        """
        Get user by Auth0 ID.

        Args:
            auth0_id: Auth0 user ID (sub claim)

        Returns:
            UserInDB or None if not found
        """
        user_doc = await self.users_collection.find_one({"auth0_id": auth0_id})

        if not user_doc:
            return None

        return UserInDB(**user_doc)

    async def list_all_users(self, skip: int = 0, limit: int = 100) -> List[UserInDB]:
        """
        List all users (admin only).

        Args:
            skip: Number of users to skip
            limit: Maximum number of users to return

        Returns:
            List of UserInDB documents
        """
        cursor = self.users_collection.find().skip(skip).limit(limit).sort("created_at", -1)
        users = []

        async for user_doc in cursor:
            users.append(UserInDB(**user_doc))

        return users

    async def get_total_user_count(self) -> int:
        """Get total number of users."""
        return await self.users_collection.count_documents({})

    async def update_user_profile(
        self,
        user_id: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UserInDB:
        """
        Update user profile.

        Args:
            user_id: MongoDB user ID
            name: Updated name (optional)
            metadata: Updated metadata (optional)

        Returns:
            Updated UserInDB document

        Raises:
            UserNotFoundException: If user not found
        """
        try:
            object_id = ObjectId(user_id)
        except Exception:
            raise UserNotFoundException(f"Invalid user ID format: {user_id}")

        update_data = {"updated_at": datetime.utcnow()}

        if name is not None:
            update_data["name"] = name

        if metadata is not None:
            update_data["metadata"] = metadata

        result = await self.users_collection.find_one_and_update(
            {"_id": object_id},
            {"$set": update_data},
            return_document=True
        )

        if not result:
            raise UserNotFoundException(f"User with ID {user_id} not found")

        return UserInDB(**result)

    async def increment_upload_count(self, user_id: str, file_size: int):
        """
        Increment user's upload count and storage.

        Args:
            user_id: MongoDB user ID
            file_size: Size of uploaded file in bytes
        """
        try:
            object_id = ObjectId(user_id)
        except Exception:
            logger.error(f"Invalid user ID format: {user_id}")
            return

        await self.users_collection.update_one(
            {"_id": object_id},
            {
                "$inc": {
                    "statistics.total_uploads": 1,
                    "statistics.total_storage_bytes": file_size
                },
                "$set": {
                    "statistics.last_activity": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        logger.debug(f"Incremented upload count for user {user_id}")

    async def decrement_upload_count(self, user_id: str, file_size: int):
        """
        Decrement user's upload count and storage (when file is deleted).

        Args:
            user_id: MongoDB user ID
            file_size: Size of deleted file in bytes
        """
        try:
            object_id = ObjectId(user_id)
        except Exception:
            logger.error(f"Invalid user ID format: {user_id}")
            return

        await self.users_collection.update_one(
            {"_id": object_id},
            {
                "$inc": {
                    "statistics.total_uploads": -1,
                    "statistics.total_storage_bytes": -file_size
                },
                "$set": {
                    "updated_at": datetime.utcnow()
                }
            }
        )
        logger.debug(f"Decremented upload count for user {user_id}")

    async def increment_query_count(self, user_id: str):
        """
        Increment user's query count.

        Args:
            user_id: MongoDB user ID
        """
        try:
            object_id = ObjectId(user_id)
        except Exception:
            logger.error(f"Invalid user ID format: {user_id}")
            return

        await self.users_collection.update_one(
            {"_id": object_id},
            {
                "$inc": {"statistics.total_queries": 1},
                "$set": {
                    "statistics.last_activity": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        logger.debug(f"Incremented query count for user {user_id}")

    async def get_user_statistics(self, user_id: str) -> UserStatistics:
        """
        Get user statistics.

        Args:
            user_id: MongoDB user ID

        Returns:
            UserStatistics document

        Raises:
            UserNotFoundException: If user not found
        """
        user = await self.get_user_by_id(user_id)
        return user.statistics

    async def get_user_file_count(self, user_id: str) -> int:
        """
        Get number of files owned by user.

        Args:
            user_id: MongoDB user ID

        Returns:
            Number of files
        """
        return await self.files_collection.count_documents({"user_id": user_id})

    async def get_system_statistics(self) -> Dict[str, Any]:
        """
        Get system-wide statistics (admin only).

        Returns:
            Dictionary with system statistics
        """
        total_users = await self.users_collection.count_documents({})
        total_students = await self.users_collection.count_documents({"role": "student"})
        total_admins = await self.users_collection.count_documents({"role": "admin"})
        total_files = await self.files_collection.count_documents({})
        total_public_files = await self.files_collection.count_documents({"is_public": True})
        total_private_files = await self.files_collection.count_documents({"is_public": False})

        # Aggregate total storage
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_storage": {"$sum": "$file_size"}
                }
            }
        ]
        storage_result = await self.files_collection.aggregate(pipeline).to_list(1)
        total_storage = storage_result[0]["total_storage"] if storage_result else 0

        # Aggregate total queries
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_queries": {"$sum": "$statistics.total_queries"}
                }
            }
        ]
        query_result = await self.users_collection.aggregate(pipeline).to_list(1)
        total_queries = query_result[0]["total_queries"] if query_result else 0

        return {
            "total_users": total_users,
            "total_students": total_students,
            "total_admins": total_admins,
            "total_files": total_files,
            "total_public_files": total_public_files,
            "total_private_files": total_private_files,
            "total_storage_bytes": total_storage,
            "total_queries": total_queries
        }


# Singleton instance
_user_service_instance: Optional[UserService] = None


def get_user_service(database: AsyncIOMotorDatabase) -> UserService:
    """
    Get or create user service instance.

    Args:
        database: MongoDB database instance

    Returns:
        UserService instance
    """
    global _user_service_instance

    if _user_service_instance is None:
        _user_service_instance = UserService(database)

    return _user_service_instance
