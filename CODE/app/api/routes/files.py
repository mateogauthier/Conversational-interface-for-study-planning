"""File management API routes."""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import List

from app.api.dependencies import get_file_service, get_rag_service
from app.services.file_service import FileService
from app.services.rag_service import RAGService
from app.models.responses import (
    FileUploadResponse, 
    FileListResponse, 
    FileInfo,
    BaseResponse
)
from app.core.exceptions import (
    FileNotFoundHTTPException,
    FileTypeNotSupportedHTTPException,
    FileTooLargeHTTPException,
    FileProcessingException,
    RAGException
)

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    file_service: FileService = Depends(get_file_service),
    rag_service: RAGService = Depends(get_rag_service)
):
    """Upload a document and process it for RAG."""
    try:
        # Save the file
        file_path = file_service.save_file(file)
        
        # Process the file for RAG
        processed_for_rag = False
        try:
            processed_for_rag = rag_service.process_document(file_path)
        except RAGException as e:
            # File saved but RAG processing failed
            pass
        
        # Get file info
        file_info = file_service.get_file_info(file.filename)
        
        return FileUploadResponse(
            message="File uploaded successfully",
            filename=file.filename,
            file_path=file_path,
            processed_for_rag=processed_for_rag,
            file_info=file_info
        )
        
    except (FileTypeNotSupportedHTTPException, FileTooLargeHTTPException, FileNotFoundHTTPException):
        raise
    except FileProcessingException as e:
        raise HTTPException(status_code=500, detail=str(e.message))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/", response_model=FileListResponse)
async def list_files(
    file_service: FileService = Depends(get_file_service)
):
    """List all uploaded files with metadata."""
    try:
        files = file_service.list_files()
        return FileListResponse(
            message="Files retrieved successfully",
            files=files,
            total_files=len(files)
        )
    except FileProcessingException as e:
        raise HTTPException(status_code=500, detail=str(e.message))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")


@router.get("/{filename}", response_model=FileInfo)
async def get_file_details(
    filename: str,
    file_service: FileService = Depends(get_file_service)
):
    """Get detailed information about a specific file."""
    try:
        file_info = file_service.get_file_info(filename)
        return file_info
    except FileNotFoundHTTPException:
        raise
    except FileProcessingException as e:
        raise HTTPException(status_code=500, detail=str(e.message))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting file details: {str(e)}")


@router.delete("/{filename}", response_model=BaseResponse)
async def delete_file(
    filename: str,
    file_service: FileService = Depends(get_file_service),
    rag_service: RAGService = Depends(get_rag_service)
):
    """Delete a specific file and its RAG data."""
    try:
        # Delete from RAG first (if exists)
        try:
            rag_service.delete_document_chunks(filename)
        except RAGException:
            pass  # Continue even if RAG deletion fails
        
        # Delete the file
        success = file_service.delete_file(filename)
        
        if success:
            return BaseResponse(
                message=f"File '{filename}' deleted successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to delete file")
            
    except FileNotFoundHTTPException:
        raise
    except FileProcessingException as e:
        raise HTTPException(status_code=500, detail=str(e.message))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")


@router.get("/supported/extensions")
async def get_supported_extensions(
    file_service: FileService = Depends(get_file_service)
):
    """Get supported file extensions and their descriptions."""
    return {
        "supported_extensions": file_service.get_supported_extensions(),
        "max_file_size_mb": file_service.max_file_size / (1024 * 1024)
    }
