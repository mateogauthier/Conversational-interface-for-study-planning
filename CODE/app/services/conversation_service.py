"""Conversation management service."""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.exceptions import (
    ForbiddenHTTPException,
    NotFoundHTTPException
)
from app.db.models import ConversationInDB, MessageInDB
from app.db.collections import CONVERSATIONS_COLLECTION, MESSAGES_COLLECTION

logger = logging.getLogger(__name__)
settings = get_settings()


class ConversationService:
    """Service for managing conversations and messages with multi-tenancy support."""

    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        self.database = database
        self.conversations_collection = database[CONVERSATIONS_COLLECTION] if database is not None else None
        self.messages_collection = database[MESSAGES_COLLECTION] if database is not None else None

        # Token estimation: ~4 characters per token (rough approximation)
        self.chars_per_token = 4

        # Calculate available tokens for history
        # Total context (llama2 default): ~8000 tokens
        # Reserve for: context chunks (~1500 chars / 4 = 375 tokens)
        #              system prompt (~300 tokens)
        #              response buffer (~500 tokens)
        #              current query (~200 tokens)
        # Remaining for history: ~6000 tokens = ~24000 chars
        self.max_history_tokens = 6000
        self.max_history_chars = self.max_history_tokens * self.chars_per_token

    def _generate_title_from_message(self, message: str) -> str:
        """Generate conversation title from first user message."""
        # Remove leading/trailing whitespace
        message = message.strip()

        # If message is very short, use it as-is
        if len(message) <= 50:
            return message

        # Truncate at word boundary
        truncated = message[:60]
        last_space = truncated.rfind(' ')

        if last_space > 40:  # Only truncate at space if it's not too early
            truncated = truncated[:last_space]
        else:
            truncated = message[:50]

        return truncated + "..."

    async def create_conversation(
        self,
        user_id: str,
        auth0_id: str,
        first_message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new conversation with auto-generated title.

        Args:
            user_id: MongoDB user ID
            auth0_id: Auth0 user ID
            first_message: First user message (used to generate title)
            metadata: Optional metadata (model, language, etc.)

        Returns:
            Conversation ID as string
        """
        title = self._generate_title_from_message(first_message)

        conversation = ConversationInDB(
            user_id=user_id,
            auth0_id=auth0_id,
            title=title,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            message_count=0,
            metadata=metadata or {}
        )

        # Insert into database
        result = await self.conversations_collection.insert_one(
            conversation.model_dump(by_alias=True, exclude={"id"})
        )

        conversation_id = str(result.inserted_id)
        logger.info(f"Created conversation {conversation_id} for user {auth0_id}")

        return conversation_id

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        model_used: Optional[str] = None,
        source_files: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a message to a conversation.

        Args:
            conversation_id: Conversation ID
            role: "user" or "assistant"
            content: Message content
            model_used: LLM model name (for assistant messages)
            source_files: List of source file names (for assistant messages)
            metadata: Optional metadata (sources, token count, etc.)

        Returns:
            Message ID as string
        """
        message = MessageInDB(
            conversation_id=conversation_id,
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            model_used=model_used,
            source_files=source_files or [],
            metadata=metadata or {}
        )

        # Insert message
        result = await self.messages_collection.insert_one(
            message.model_dump(by_alias=True, exclude={"id"})
        )

        # Update conversation's updated_at and message_count
        await self.conversations_collection.update_one(
            {"_id": ObjectId(conversation_id)},
            {
                "$set": {"updated_at": datetime.utcnow()},
                "$inc": {"message_count": 1}
            }
        )

        message_id = str(result.inserted_id)
        logger.debug(f"Added {role} message {message_id} to conversation {conversation_id}")

        return message_id

    async def get_conversation(
        self,
        conversation_id: str,
        user_auth0_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """
        Get conversation with all messages.

        Args:
            conversation_id: Conversation ID
            user_auth0_id: Requesting user's Auth0 ID
            user_role: Requesting user's role (admin or student)

        Returns:
            Dict with conversation and messages

        Raises:
            NotFoundHTTPException: If conversation doesn't exist
            ForbiddenHTTPException: If user doesn't have access
        """
        # Get conversation
        conversation = await self.conversations_collection.find_one(
            {"_id": ObjectId(conversation_id)}
        )

        if not conversation:
            raise NotFoundHTTPException("Conversation", conversation_id)

        # Check access: user must own conversation OR be admin
        if conversation["auth0_id"] != user_auth0_id and user_role != "admin":
            raise ForbiddenHTTPException("access this conversation")

        # Get all messages for this conversation
        messages_cursor = self.messages_collection.find(
            {"conversation_id": conversation_id}
        ).sort("timestamp", 1)  # Sort by timestamp ascending

        messages = await messages_cursor.to_list(length=None)

        # Convert ObjectIds to strings
        conversation["_id"] = str(conversation["_id"])
        for msg in messages:
            msg["_id"] = str(msg["_id"])

        return {
            "conversation": conversation,
            "messages": messages
        }

    async def get_conversation_history(
        self,
        conversation_id: str,
        max_chars: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Get conversation history formatted for LLM, truncated to fit context window.

        Args:
            conversation_id: Conversation ID
            max_chars: Maximum characters for history (defaults to max_history_chars)

        Returns:
            List of dicts with 'role' and 'content' keys, most recent messages first
        """
        if max_chars is None:
            max_chars = self.max_history_chars

        # Get messages sorted by timestamp descending (most recent first)
        messages_cursor = self.messages_collection.find(
            {"conversation_id": conversation_id}
        ).sort("timestamp", -1)

        messages = await messages_cursor.to_list(length=None)

        # Truncate to fit within max_chars
        truncated_messages = []
        total_chars = 0

        for msg in messages:
            msg_length = len(msg["content"])
            if total_chars + msg_length > max_chars:
                # Stop adding messages if we exceed limit
                break

            truncated_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
            total_chars += msg_length

        # Reverse to get chronological order (oldest to newest)
        truncated_messages.reverse()

        logger.debug(
            f"Retrieved {len(truncated_messages)} messages ({total_chars} chars) "
            f"from conversation {conversation_id}"
        )

        return truncated_messages

    async def get_user_conversations(
        self,
        user_auth0_id: str,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get list of user's conversations.

        Args:
            user_auth0_id: User's Auth0 ID
            limit: Maximum number of conversations to return
            skip: Number of conversations to skip (for pagination)

        Returns:
            List of conversation documents
        """
        cursor = self.conversations_collection.find(
            {"auth0_id": user_auth0_id}
        ).sort("updated_at", -1).skip(skip).limit(limit)

        conversations = await cursor.to_list(length=limit)

        # Convert ObjectIds to strings
        for conv in conversations:
            conv["_id"] = str(conv["_id"])

        return conversations

    async def delete_conversation(
        self,
        conversation_id: str,
        user_auth0_id: str,
        user_role: str
    ) -> None:
        """
        Delete a conversation and all its messages.

        Args:
            conversation_id: Conversation ID
            user_auth0_id: Requesting user's Auth0 ID
            user_role: Requesting user's role (admin or student)

        Raises:
            NotFoundHTTPException: If conversation doesn't exist
            ForbiddenHTTPException: If user doesn't have access
        """
        # Get conversation to check ownership
        conversation = await self.conversations_collection.find_one(
            {"_id": ObjectId(conversation_id)}
        )

        if not conversation:
            raise NotFoundHTTPException("Conversation", conversation_id)

        # Check access: user must own conversation OR be admin
        if conversation["auth0_id"] != user_auth0_id and user_role != "admin":
            raise ForbiddenHTTPException("delete this conversation")

        # Delete all messages in conversation
        delete_messages_result = await self.messages_collection.delete_many(
            {"conversation_id": conversation_id}
        )

        # Delete conversation
        await self.conversations_collection.delete_one(
            {"_id": ObjectId(conversation_id)}
        )

        logger.info(
            f"Deleted conversation {conversation_id} and {delete_messages_result.deleted_count} messages"
        )

    async def get_latest_conversation(
        self,
        user_auth0_id: str
    ) -> Optional[str]:
        """
        Get the most recently updated conversation ID for a user.

        Args:
            user_auth0_id: User's Auth0 ID

        Returns:
            Conversation ID as string, or None if no conversations exist
        """
        conversation = await self.conversations_collection.find_one(
            {"auth0_id": user_auth0_id},
            sort=[("updated_at", -1)]
        )

        if conversation:
            return str(conversation["_id"])

        return None

    async def get_message(self, message_id: str) -> Optional[MessageInDB]:
        """
        Get a specific message by ID.

        Args:
            message_id: Message ID

        Returns:
            MessageInDB object or None if not found
        """
        message_doc = await self.messages_collection.find_one(
            {"_id": ObjectId(message_id)}
        )

        if not message_doc:
            return None

        # Convert _id to string for Pydantic model
        message_doc["_id"] = str(message_doc["_id"])

        return MessageInDB(**message_doc)

    async def get_conversation_info(self, conversation_id: str) -> Optional[ConversationInDB]:
        """
        Get conversation information by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            ConversationInDB object or None if not found
        """
        conv_doc = await self.conversations_collection.find_one(
            {"_id": ObjectId(conversation_id)}
        )

        if not conv_doc:
            return None

        # Convert _id to string for Pydantic model
        conv_doc["_id"] = str(conv_doc["_id"])

        return ConversationInDB(**conv_doc)

    async def update_message_feedback(
        self,
        message_id: str,
        feedback: str
    ) -> None:
        """
        Update feedback for a message.

        Args:
            message_id: Message ID
            feedback: Feedback value ('like' or 'dislike')
        """
        await self.messages_collection.update_one(
            {"_id": ObjectId(message_id)},
            {"$set": {"feedback": feedback}}
        )

        logger.debug(f"Updated feedback for message {message_id} to '{feedback}'")

    async def get_files_used_in_conversation(
        self,
        conversation_id: str
    ) -> List[str]:
        """
        Get list of all unique files that have been used in this conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of unique filenames used in the conversation
        """
        # Get all assistant messages in this conversation (only they have source_files)
        messages_cursor = self.messages_collection.find(
            {
                "conversation_id": conversation_id,
                "role": "assistant"
            }
        )

        messages = await messages_cursor.to_list(length=None)

        # Collect all unique filenames
        all_files = set()
        for msg in messages:
            source_files = msg.get("source_files", [])
            all_files.update(source_files)

        return list(all_files)


# Global service instance (will be initialized with database in main.py)
conversation_service: Optional[ConversationService] = None


def get_conversation_service() -> ConversationService:
    """Dependency to get conversation service instance."""
    if conversation_service is None:
        raise RuntimeError("ConversationService not initialized")
    return conversation_service
