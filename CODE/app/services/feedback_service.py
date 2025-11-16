"""Feedback management service."""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.exceptions import NotFoundHTTPException, ForbiddenHTTPException
from app.db.models import FeedbackInDB
from app.db.collections import FEEDBACK_COLLECTION, CONVERSATIONS_COLLECTION, MESSAGES_COLLECTION
from app.services.llm_service import LLMService, llm_service

logger = logging.getLogger(__name__)
settings = get_settings()


class FeedbackService:
    """Service for managing user feedback with LLM summarization."""

    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        self.database = database
        self.feedback_collection = database[FEEDBACK_COLLECTION] if database is not None else None
        self.conversations_collection = database[CONVERSATIONS_COLLECTION] if database is not None else None
        self.messages_collection = database[MESSAGES_COLLECTION] if database is not None else None
        self.llm_service = llm_service

    async def submit_feedback(
        self,
        user_id: str,
        auth0_id: str,
        user_email: str,
        comment: str,
        rating: Optional[str] = None,
        message_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        files_referenced: Optional[List[str]] = None
    ) -> str:
        """
        Submit written feedback from a user.

        Args:
            user_id: MongoDB user ID
            auth0_id: Auth0 user ID
            user_email: User email for display
            comment: Written feedback text
            rating: Optional like/dislike rating
            message_id: Optional message ID if tied to specific message
            conversation_id: Optional conversation ID
            files_referenced: Optional list of files referenced

        Returns:
            Feedback ID as string
        """
        feedback = FeedbackInDB(
            user_id=user_id,
            auth0_id=auth0_id,
            user_email=user_email,
            message_id=message_id,
            conversation_id=conversation_id,
            rating=rating,
            comment=comment,
            files_referenced=files_referenced or [],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # Insert into database
        result = await self.feedback_collection.insert_one(
            feedback.model_dump(by_alias=True, exclude={"id"})
        )

        feedback_id = str(result.inserted_id)
        logger.info(f"Created feedback {feedback_id} from user {auth0_id}")

        return feedback_id

    async def get_all_feedback(
        self,
        skip: int = 0,
        limit: int = 50,
        rating_filter: Optional[str] = None,
        user_filter: Optional[str] = None,
        file_filter: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get paginated list of all feedback (admin only).

        Args:
            skip: Number of items to skip
            limit: Maximum number of items to return
            rating_filter: Filter by rating ("like" or "dislike")
            user_filter: Filter by user auth0_id
            file_filter: Filter by file name
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            Dict with feedback items, total count, and pagination info
        """
        # Build filter query
        query = {}

        if rating_filter:
            query["rating"] = rating_filter

        if user_filter:
            query["auth0_id"] = user_filter

        if file_filter:
            query["files_referenced"] = file_filter

        if start_date or end_date:
            query["created_at"] = {}
            if start_date:
                query["created_at"]["$gte"] = start_date
            if end_date:
                query["created_at"]["$lte"] = end_date

        # Get total count
        total = await self.feedback_collection.count_documents(query)

        # Get feedback items
        cursor = self.feedback_collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        feedback_items = await cursor.to_list(length=limit)

        # Convert ObjectIds and datetime objects to strings
        for item in feedback_items:
            item["_id"] = str(item["_id"])
            if "created_at" in item and item["created_at"]:
                item["created_at"] = item["created_at"].isoformat()
            if "updated_at" in item and item["updated_at"]:
                item["updated_at"] = item["updated_at"].isoformat()

        return {
            "items": feedback_items,
            "total": total,
            "skip": skip,
            "limit": limit,
            "page": (skip // limit) + 1 if limit > 0 else 1,
            "pages": (total + limit - 1) // limit if limit > 0 else 1
        }

    async def get_feedback_stats(self) -> Dict[str, Any]:
        """
        Get aggregated feedback statistics (admin only).

        Returns:
            Dict with aggregated statistics
        """
        total_feedback = await self.feedback_collection.count_documents({})

        # Count by rating
        total_likes = await self.feedback_collection.count_documents({"rating": "like"})
        total_dislikes = await self.feedback_collection.count_documents({"rating": "dislike"})
        total_neutral = await self.feedback_collection.count_documents({"rating": None})

        # Get feedback with comments
        total_with_comments = await self.feedback_collection.count_documents(
            {"comment": {"$exists": True, "$ne": ""}}
        )

        # Aggregate by user
        pipeline = [
            {
                "$group": {
                    "_id": "$auth0_id",
                    "count": {"$sum": 1},
                    "user_email": {"$first": "$user_email"}
                }
            },
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        top_users = await self.feedback_collection.aggregate(pipeline).to_list(10)

        # Aggregate by file
        pipeline = [
            {"$unwind": "$files_referenced"},
            {
                "$group": {
                    "_id": "$files_referenced",
                    "feedback_count": {"$sum": 1},
                    "likes": {
                        "$sum": {"$cond": [{"$eq": ["$rating", "like"]}, 1, 0]}
                    },
                    "dislikes": {
                        "$sum": {"$cond": [{"$eq": ["$rating", "dislike"]}, 1, 0]}
                    }
                }
            },
            {"$sort": {"feedback_count": -1}},
            {"$limit": 10}
        ]
        top_files = await self.feedback_collection.aggregate(pipeline).to_list(10)

        # Recent feedback
        recent_feedback = await self.feedback_collection.find().sort("created_at", -1).limit(5).to_list(5)
        for item in recent_feedback:
            item["_id"] = str(item["_id"])
            if "created_at" in item and item["created_at"]:
                item["created_at"] = item["created_at"].isoformat()
            if "updated_at" in item and item["updated_at"]:
                item["updated_at"] = item["updated_at"].isoformat()

        return {
            "total_feedback": total_feedback,
            "total_likes": total_likes,
            "total_dislikes": total_dislikes,
            "total_neutral": total_neutral,
            "total_with_comments": total_with_comments,
            "top_users": top_users,
            "top_files": top_files,
            "recent_feedback": recent_feedback
        }

    async def get_feedback_by_file(self, filename: str) -> List[Dict[str, Any]]:
        """
        Get all feedback for a specific file.

        Args:
            filename: File name to filter by

        Returns:
            List of feedback documents
        """
        cursor = self.feedback_collection.find(
            {"files_referenced": filename}
        ).sort("created_at", -1)

        feedback_items = await cursor.to_list(length=None)

        # Convert ObjectIds and datetime objects to strings
        for item in feedback_items:
            item["_id"] = str(item["_id"])
            if "created_at" in item and item["created_at"]:
                item["created_at"] = item["created_at"].isoformat()
            if "updated_at" in item and item["updated_at"]:
                item["updated_at"] = item["updated_at"].isoformat()

        return feedback_items

    async def get_feedback_by_user(self, auth0_id: str) -> List[Dict[str, Any]]:
        """
        Get all feedback from a specific user.

        Args:
            auth0_id: Auth0 user ID

        Returns:
            List of feedback documents
        """
        cursor = self.feedback_collection.find(
            {"auth0_id": auth0_id}
        ).sort("created_at", -1)

        feedback_items = await cursor.to_list(length=None)

        # Convert ObjectIds and datetime objects to strings
        for item in feedback_items:
            item["_id"] = str(item["_id"])
            if "created_at" in item and item["created_at"]:
                item["created_at"] = item["created_at"].isoformat()
            if "updated_at" in item and item["updated_at"]:
                item["updated_at"] = item["updated_at"].isoformat()

        return feedback_items

    async def generate_feedback_summary(
        self,
        rating_filter: Optional[str] = None,
        user_filter: Optional[str] = None,
        file_filter: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_items: int = 100,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Generate LLM-based summary of feedback.

        Args:
            rating_filter: Filter by rating
            user_filter: Filter by user
            file_filter: Filter by file
            start_date: Filter by start date
            end_date: Filter by end date
            max_items: Maximum number of feedback items to summarize

        Returns:
            Dict with summary text and metadata
        """
        # Build filter query
        query = {}

        if rating_filter:
            query["rating"] = rating_filter

        if user_filter:
            query["auth0_id"] = user_filter

        if file_filter:
            query["files_referenced"] = file_filter

        if start_date or end_date:
            query["created_at"] = {}
            if start_date:
                query["created_at"]["$gte"] = start_date
            if end_date:
                query["created_at"]["$lte"] = end_date

        # Get feedback items
        cursor = self.feedback_collection.find(query).sort("created_at", -1).limit(max_items)
        feedback_items = await cursor.to_list(length=max_items)

        if not feedback_items:
            return {
                "summary": "No feedback found matching the specified criteria.",
                "item_count": 0,
                "generated_at": datetime.utcnow().isoformat(),
                "filters_applied": {
                    "rating": rating_filter,
                    "user": user_filter,
                    "file": file_filter,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            }

        # Aggregate feedback text
        feedback_texts = []
        for item in feedback_items:
            rating_str = f"[{item.get('rating', 'neutral').upper()}]" if item.get('rating') else "[NEUTRAL]"
            comment = item.get('comment', '')
            user_email = item.get('user_email', 'Unknown')
            created_at = item.get('created_at', datetime.utcnow()).strftime('%Y-%m-%d')

            feedback_texts.append(f"{rating_str} ({user_email} on {created_at}): {comment}")

        aggregated_feedback = "\n\n".join(feedback_texts)

        # Construct prompt for LLM (in Spanish or English based on language parameter)
        if language == "es":
            prompt = f"""Eres un asistente ayudando a administradores a comprender los comentarios de estudiantes en una plataforma educativa.

A continuación hay una colección de {len(feedback_items)} comentarios de estudiantes. Cada entrada de comentarios incluye una calificación (LIKE/DISLIKE/NEUTRAL) y comentarios escritos.

Por favor analiza estos comentarios y proporciona:
1. **Sentimiento General**: ¿Cuál es el sentimiento general (positivo, negativo, mixto)?
2. **Temas Principales**: ¿Cuáles son los 3-5 temas o tópicos principales que discuten los estudiantes?
3. **Elogios Comunes**: ¿Qué les gusta o aprecian los estudiantes?
4. **Quejas Comunes**: ¿Qué problemas o dificultades mencionan los estudiantes?
5. **Sugerencias Accionables**: ¿Qué mejoras específicas se podrían hacer basándose en estos comentarios?

Mantén tu resumen conciso pero completo. Enfócate en insights accionables para los administradores.

COMENTARIOS DE ESTUDIANTES:
---
{aggregated_feedback}
---

Por favor proporciona tu análisis:"""
        else:
            prompt = f"""You are an assistant helping administrators understand student feedback on an educational platform.

Below is a collection of {len(feedback_items)} student feedback submissions. Each feedback entry includes a rating (LIKE/DISLIKE/NEUTRAL) and written comments.

Please analyze this feedback and provide:
1. **Overall Sentiment**: What is the general sentiment (positive, negative, mixed)?
2. **Key Themes**: What are the 3-5 main themes or topics students are discussing?
3. **Common Praise**: What do students like or appreciate?
4. **Common Complaints**: What issues or problems do students mention?
5. **Actionable Suggestions**: What specific improvements could be made based on this feedback?

Keep your summary concise but comprehensive. Focus on actionable insights for administrators.

STUDENT FEEDBACK:
---
{aggregated_feedback}
---

Please provide your analysis:"""

        # Call LLM service
        try:
            response = await self.llm_service.generate_response(prompt)
            summary_text = response.get("response", "No summary generated")
        except Exception as e:
            logger.error(f"Failed to generate LLM summary: {e}")
            summary_text = f"Error generating summary: {str(e)}"

        return {
            "summary": summary_text,
            "item_count": len(feedback_items),
            "generated_at": datetime.utcnow().isoformat(),
            "filters_applied": {
                "rating": rating_filter,
                "user": user_filter,
                "file": file_filter,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            }
        }

    async def delete_feedback(self, feedback_id: str) -> None:
        """
        Delete a feedback entry (admin only).

        Args:
            feedback_id: Feedback ID to delete

        Raises:
            NotFoundHTTPException: If feedback doesn't exist
        """
        result = await self.feedback_collection.delete_one(
            {"_id": ObjectId(feedback_id)}
        )

        if result.deleted_count == 0:
            raise NotFoundHTTPException("Feedback", feedback_id)

        logger.info(f"Deleted feedback {feedback_id}")


# Global service instance (will be initialized with database in main.py)
feedback_service: Optional[FeedbackService] = None


def get_feedback_service() -> FeedbackService:
    """Dependency to get feedback service instance."""
    if feedback_service is None:
        raise RuntimeError("FeedbackService not initialized")
    return feedback_service
