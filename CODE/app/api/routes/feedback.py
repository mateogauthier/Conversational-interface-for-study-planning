"""Feedback API routes."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Literal

from app.models.requests import MessageFeedbackRequest
from app.models.responses import BaseResponse
from app.db.models import UserInDB
from app.api.dependencies import get_current_user, get_file_service_dep, get_conversation_service_dep
from app.services.file_service import FileService
from app.services.conversation_service import ConversationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("/message", response_model=BaseResponse)
async def submit_message_feedback(
    request: MessageFeedbackRequest,
    current_user: UserInDB = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service_dep),
    file_service: FileService = Depends(get_file_service_dep)
):
    """
    Submit like/dislike feedback for a message.

    This endpoint:
    1. Validates the feedback type (like/dislike)
    2. Updates the message with the feedback
    3. Updates file statistics for all source files used in the response
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

        logger.info(f"Feedback '{request.feedback}' submitted for message {request.message_id} by user {current_user.auth0_id}")

        return BaseResponse(
            success=True,
            message=f"Feedback '{request.feedback}' recorded successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")
