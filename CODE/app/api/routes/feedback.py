"""Feedback API routes."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Literal

from app.models.requests import MessageFeedbackRequest, FeedbackSubmitRequest
from app.models.responses import BaseResponse
from app.db.models import UserInDB
from app.api.dependencies import (
    get_current_user,
    get_file_service_dep,
    get_conversation_service_dep,
    get_database
)
from app.services.file_service import FileService
from app.services.conversation_service import ConversationService
from app.services.feedback_service import FeedbackService
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("/message", response_model=BaseResponse)
async def submit_message_feedback(
    request: MessageFeedbackRequest,
    current_user: UserInDB = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service_dep),
    file_service: FileService = Depends(get_file_service_dep),
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Submit like/dislike feedback (with optional comment) for a message.

    This endpoint:
    1. Validates the feedback type (like/dislike)
    2. Updates the message with the feedback
    3. Updates file statistics for all source files used in the response
    4. If comment is provided, stores separate feedback document
    """
    try:
        # Validate feedback type
        if request.feedback not in ["like", "dislike"]:
            raise HTTPException(status_code=400, detail="Feedback must be 'like' or 'dislike'")

        # Get the message to validate ownership and get source files
        message = await conversation_service.get_message(request.message_id)

        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        # Verify the message belongs to a conversation owned by the current user
        conversation = await conversation_service.get_conversation_info(message.conversation_id)
        if not conversation or conversation.user_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to provide feedback on this message")

        # Only assistant messages can receive feedback
        if message.role != "assistant":
            raise HTTPException(status_code=400, detail="Can only provide feedback on assistant messages")

        # Get previous feedback to handle changes
        previous_feedback = message.feedback

        # Update message feedback
        await conversation_service.update_message_feedback(
            message_id=request.message_id,
            feedback=request.feedback
        )

        # Update file statistics for all source files
        if message.source_files:
            for filename in message.source_files:
                await file_service.update_file_feedback(
                    filename=filename,
                    new_feedback=request.feedback,
                    previous_feedback=previous_feedback
                )

        # If comment is provided, store it as separate feedback document
        feedback_id = None
        if request.comment and request.comment.strip():
            feedback_service = FeedbackService(database)
            feedback_id = await feedback_service.submit_feedback(
                user_id=str(current_user.id),
                auth0_id=current_user.auth0_id,
                user_email=current_user.email,
                comment=request.comment,
                rating=request.feedback,
                message_id=request.message_id,
                conversation_id=message.conversation_id,
                files_referenced=message.source_files
            )

        logger.info(f"Feedback '{request.feedback}' submitted for message {request.message_id} by user {current_user.auth0_id}")

        return BaseResponse(
            success=True,
            message=f"Feedback '{request.feedback}' recorded successfully" + (f" with comment (ID: {feedback_id})" if feedback_id else "")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")


@router.post("/", response_model=BaseResponse)
async def submit_general_feedback(
    request: FeedbackSubmitRequest,
    current_user: UserInDB = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service_dep),
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Submit general written feedback (not necessarily tied to a specific message).

    This allows students to provide feedback about:
    - The overall system
    - Specific features
    - Suggestions for improvement
    - General comments
    """
    try:
        # Validate comment is not empty
        if not request.comment or not request.comment.strip():
            raise HTTPException(status_code=400, detail="Comment cannot be empty")

        # Validate rating if provided
        if request.rating and request.rating not in ["like", "dislike"]:
            raise HTTPException(status_code=400, detail="Rating must be 'like' or 'dislike' if provided")

        # Get files referenced if message_id is provided
        files_referenced = []
        if request.message_id:
            message = await conversation_service.get_message(request.message_id)
            if message:
                files_referenced = message.source_files

        # Submit feedback
        feedback_service = FeedbackService(database)
        feedback_id = await feedback_service.submit_feedback(
            user_id=str(current_user.id),
            auth0_id=current_user.auth0_id,
            user_email=current_user.email,
            comment=request.comment,
            rating=request.rating,
            message_id=request.message_id,
            conversation_id=request.conversation_id,
            files_referenced=files_referenced
        )

        logger.info(f"General feedback submitted (ID: {feedback_id}) by user {current_user.auth0_id}")

        return BaseResponse(
            success=True,
            message=f"Feedback submitted successfully (ID: {feedback_id})"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit general feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")
