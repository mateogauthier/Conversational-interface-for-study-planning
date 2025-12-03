"""File management API routes with authentication."""

import logging
import os
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse
from typing import List

from app.api.dependencies import (
    get_file_service,
    get_rag_service,
    get_current_user,
    get_user_service_dep
)
from app.services.file_service import FileService
from app.services.rag_service import RAGService
from app.services.user_service import UserService
from app.db.models import UserInDB, FileMetadataInDB
from app.models.user import FileOwnershipInfo
from app.models.responses import BaseResponse
from app.core.config import get_settings
from app.core.exceptions import (
    FileNotFoundHTTPException,
    FileTypeNotSupportedHTTPException,
    FileTooLargeHTTPException,
    FileProcessingException,
    ForbiddenHTTPException,
    RAGException
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["files"])
settings = get_settings()


@router.post("/upload", response_model=dict)
async def upload_file(
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
    rag_service: RAGService = Depends(get_rag_service),
    user_service: UserService = Depends(get_user_service_dep)
):
    """
    Upload a document and process it for RAG.

    - Students: Files are uploaded as private
    - Admins: Files are uploaded as public
    """
    try:
        # Determine if file should be public based on user role
        is_public = (current_user.role == settings.admin_role)

        # Save the file with user context
        file_path, file_metadata = await file_service.save_file(
            file=file,
            user=current_user,
            is_public=is_public
        )

        # Process the file for RAG (from GridFS)
        chunk_count = 0
        processed_for_rag = False
        try:
            chunk_count = await rag_service.process_document_from_gridfs(
                filename=file_metadata.filename,
                user_id=str(current_user.id),
                is_public=is_public
            )
            processed_for_rag = chunk_count > 0

            # Update file metadata with processing status
            await file_service.update_file_processed_status(
                filename=file_metadata.filename,
                processed=processed_for_rag,
                chunk_count=chunk_count
            )
        except RAGException as e:
            logger.warning(f"RAG processing failed for {file_metadata.filename}: {e}")
            # File saved but RAG processing failed - continue

        # Update user statistics
        await user_service.increment_upload_count(
            user_id=str(current_user.id),
            file_size=file_metadata.file_size
        )

        return {
            "message": "File uploaded successfully",
            "filename": file_metadata.filename,
            "gridfs_file_id": file_path,  # This is now the GridFS file ID
            "is_public": is_public,
            "processed_for_rag": processed_for_rag,
            "chunk_count": chunk_count,
            "file_size": file_metadata.file_size,
            "uploaded_by": current_user.email
        }

    except (FileTypeNotSupportedHTTPException, FileTooLargeHTTPException, FileNotFoundHTTPException):
        raise
    except FileProcessingException as e:
        raise HTTPException(status_code=500, detail=str(e.message))
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/", response_model=List[FileOwnershipInfo])
async def list_files(
    current_user: UserInDB = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
):
    """
    List files based on user role.

    - Students: See their private files + all public files
    - Admins: See only public files
    """
    try:
        files = await file_service.list_files(user=current_user)

        # Convert to FileOwnershipInfo response
        from app.models.user import FileFeedbackStatsInfo
        file_info_list = []
        for file_metadata in files:
            # Get user email (would need to query users collection - simplified here)
            file_info = FileOwnershipInfo(
                filename=file_metadata.filename,
                user_id=file_metadata.user_id,
                user_email=file_metadata.auth0_id,  # Simplified: using auth0_id
                is_public=file_metadata.is_public,
                uploaded_at=file_metadata.uploaded_at,
                file_size=file_metadata.file_size,
                chunk_count=file_metadata.chunk_count,
                feedback_stats=FileFeedbackStatsInfo(
                    total_uses=file_metadata.feedback_stats.total_uses,
                    total_likes=file_metadata.feedback_stats.total_likes,
                    total_dislikes=file_metadata.feedback_stats.total_dislikes,
                    last_used=file_metadata.feedback_stats.last_used
                )
            )
            file_info_list.append(file_info)

        return file_info_list

    except FileProcessingException as e:
        raise HTTPException(status_code=500, detail=str(e.message))
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")


@router.get("/{filename}", response_model=FileOwnershipInfo)
async def get_file_details(
    filename: str,
    current_user: UserInDB = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
):
    """Get detailed information about a specific file (if user has access)."""
    try:
        # Check if user can access this file
        can_access = await file_service.can_user_access_file(filename, current_user)

        if not can_access:
            raise ForbiddenHTTPException("You do not have permission to access this file")

        # Get file metadata
        file_metadata = await file_service.get_file_metadata_by_name(filename)

        if not file_metadata:
            raise FileNotFoundHTTPException(filename)

        from app.models.user import FileFeedbackStatsInfo
        return FileOwnershipInfo(
            filename=file_metadata.filename,
            user_id=file_metadata.user_id,
            user_email=file_metadata.auth0_id,
            is_public=file_metadata.is_public,
            uploaded_at=file_metadata.uploaded_at,
            file_size=file_metadata.file_size,
            chunk_count=file_metadata.chunk_count,
            feedback_stats=FileFeedbackStatsInfo(
                total_uses=file_metadata.feedback_stats.total_uses,
                total_likes=file_metadata.feedback_stats.total_likes,
                total_dislikes=file_metadata.feedback_stats.total_dislikes,
                last_used=file_metadata.feedback_stats.last_used
            )
        )

    except (FileNotFoundHTTPException, ForbiddenHTTPException):
        raise
    except FileProcessingException as e:
        raise HTTPException(status_code=500, detail=str(e.message))
    except Exception as e:
        logger.error(f"Error getting file details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting file details: {str(e)}")


@router.get("/{filename}/download")
async def download_file(
    filename: str,
    current_user: UserInDB = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
):
    """Download a file from GridFS (if user has access)."""
    try:
        # Check if user can access this file
        can_access = await file_service.can_user_access_file(filename, current_user)

        if not can_access:
            raise ForbiddenHTTPException("You do not have permission to download this file")

        # Get file metadata to ensure it exists
        file_metadata = await file_service.get_file_metadata_by_name(filename)

        if not file_metadata:
            raise FileNotFoundHTTPException(filename)

        # Download file from GridFS
        file_content = await file_service.get_file_from_gridfs(filename)

        if not file_content:
            logger.error(f"File {filename} exists in DB but not in GridFS")
            raise FileNotFoundHTTPException(f"File {filename} not found in storage")

        # Track file view
        await file_service.track_file_view(filename)

        # Return file as streaming response
        from fastapi.responses import StreamingResponse
        import io

        return StreamingResponse(
            io.BytesIO(file_content),
            media_type='application/octet-stream',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )

    except (FileNotFoundHTTPException, ForbiddenHTTPException):
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")


@router.delete("/{filename}", response_model=BaseResponse)
async def delete_file(
    filename: str,
    current_user: UserInDB = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
    rag_service: RAGService = Depends(get_rag_service),
    user_service: UserService = Depends(get_user_service_dep)
):
    """
    Delete a specific file and its RAG data.

    - Students: Can only delete their own private files
    - Admins: Can only delete public files
    """
    try:
        # Get file metadata first (for size info before deletion)
        file_metadata = await file_service.get_file_metadata_by_name(filename)

        if not file_metadata:
            raise FileNotFoundHTTPException(filename)

        # Delete from RAG first (if exists)
        try:
            await rag_service.delete_document_chunks_async(
                filename=filename,
                user_id=file_metadata.user_id
            )
        except RAGException as e:
            logger.warning(f"RAG deletion failed for {filename}: {e}")
            # Continue even if RAG deletion fails

        # Delete the file (with permission check inside)
        success = await file_service.delete_file(filename, current_user)

        if success:
            # Update user statistics
            await user_service.decrement_upload_count(
                user_id=file_metadata.user_id,
                file_size=file_metadata.file_size
            )

            return BaseResponse(
                message=f"File '{filename}' deleted successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to delete file")

    except (FileNotFoundHTTPException, ForbiddenHTTPException):
        raise
    except FileProcessingException as e:
        raise HTTPException(status_code=500, detail=str(e.message))
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")


@router.get("/{filename}/content")
async def get_file_content(
    filename: str,
    current_user: UserInDB = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
):
    """
    Extract and return full text content from a file.

    This endpoint is used by the agent to read complete file content
    when search chunks are insufficient to answer a question.
    """
    try:
        # Check if user can access this file
        can_access = await file_service.can_user_access_file(filename, current_user)

        if not can_access:
            raise ForbiddenHTTPException("You do not have permission to access this file")

        # Get file metadata
        file_metadata = await file_service.get_file_metadata_by_name(filename)

        if not file_metadata:
            raise FileNotFoundHTTPException(filename)

        # Extract text content
        content = await file_service.extract_text_from_file(filename)

        if content is None:
            raise FileProcessingException(f"Could not extract text from {filename}")

        # Track file view
        await file_service.track_file_view(filename)

        return {
            "filename": filename,
            "content": content,
            "file_size": file_metadata.file_size,
            "chunk_count": file_metadata.chunk_count
        }

    except (FileNotFoundHTTPException, ForbiddenHTTPException):
        raise
    except FileProcessingException as e:
        raise HTTPException(status_code=500, detail=str(e.message))
    except Exception as e:
        logger.error(f"Error getting file content: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting file content: {str(e)}")


@router.get("/supported/extensions")
async def get_supported_extensions(
    current_user: UserInDB = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
):
    """Get supported file extensions and their descriptions (authenticated users only)."""
    return {
        "supported_extensions": file_service.get_supported_extensions(),
        "max_file_size_mb": file_service.max_file_size / (1024 * 1024)
    }
