"""Conversation API routes with authentication."""

import logging
from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import (
    get_conversation_service_dep,
    get_current_user
)
from app.services.conversation_service import ConversationService
from app.db.models import UserInDB
from app.models.responses import (
    ConversationListResponse,
    ConversationDetailResponse,
    ConversationInfo,
    MessageInfo,
    BaseResponse
)
from app.core.exceptions import (
    NotFoundHTTPException,
    ForbiddenHTTPException
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = 50,
    skip: int = 0,
    current_user: UserInDB = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service_dep)
):
    """
    Get list of user's conversations.

    - Returns conversations sorted by most recently updated
    - Supports pagination with limit and skip parameters
    """
    try:
        conversations = await conversation_service.get_user_conversations(
            user_auth0_id=current_user.auth0_id,
            limit=limit,
            skip=skip
        )

        # Convert to response models
        conversation_infos = [
            ConversationInfo(
                _id=conv["_id"],
                title=conv["title"],
                created_at=conv["created_at"],
                updated_at=conv["updated_at"],
                message_count=conv["message_count"]
            )
            for conv in conversations
        ]

        # Debug logging to verify serialization
        if conversation_infos:
            logger.info(f"First conversation ID: {conversation_infos[0].id}")
            logger.info(f"First conversation dict: {conversation_infos[0].model_dump()}")

        return ConversationListResponse(
            message="Conversations retrieved successfully",
            conversations=conversation_infos,
            total=len(conversation_infos)
        )

    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list conversations: {str(e)}")


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    current_user: UserInDB = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service_dep)
):
    """
    Get a specific conversation with all its messages.

    - Users can only access their own conversations
    - Admins can access any conversation
    """
    try:
        result = await conversation_service.get_conversation(
            conversation_id=conversation_id,
            user_auth0_id=current_user.auth0_id,
            user_role=current_user.role
        )

        conversation = result["conversation"]
        messages = result["messages"]

        # Convert to response models
        conversation_info = ConversationInfo(
            _id=conversation["_id"],
            title=conversation["title"],
            created_at=conversation["created_at"],
            updated_at=conversation["updated_at"],
            message_count=conversation["message_count"]
        )

        message_infos = [
            MessageInfo(
                _id=msg["_id"],
                role=msg["role"],
                content=msg["content"],
                timestamp=msg["timestamp"],
                model_used=msg.get("model_used")
            )
            for msg in messages
        ]

        return ConversationDetailResponse(
            message="Conversation retrieved successfully",
            conversation=conversation_info,
            messages=message_infos
        )

    except (NotFoundHTTPException, ForbiddenHTTPException):
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversation {conversation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve conversation: {str(e)}")


@router.delete("/{conversation_id}", response_model=BaseResponse)
async def delete_conversation(
    conversation_id: str,
    current_user: UserInDB = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service_dep)
):
    """
    Delete a conversation and all its messages.

    - Users can only delete their own conversations
    - Admins can delete any conversation
    """
    try:
        await conversation_service.delete_conversation(
            conversation_id=conversation_id,
            user_auth0_id=current_user.auth0_id,
            user_role=current_user.role
        )

        return BaseResponse(
            success=True,
            message=f"Conversation {conversation_id} deleted successfully"
        )

    except (NotFoundHTTPException, ForbiddenHTTPException):
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation {conversation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")
