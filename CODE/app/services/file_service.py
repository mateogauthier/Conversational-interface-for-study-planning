"""File management service."""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from fastapi import UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.exceptions import (
    FileValidationException,
    FileProcessingException,
    FileNotFoundHTTPException,
    FileTypeNotSupportedHTTPException,
    FileTooLargeHTTPException,
    ForbiddenHTTPException
)
from app.models.responses import FileInfo
from app.db.models import FileMetadataInDB, UserInDB
from app.db.collections import FILE_METADATA_COLLECTION

logger = logging.getLogger(__name__)
settings = get_settings()


class FileService:
    """Service for handling file operations with multi-tenancy support."""

    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        self.upload_dir = settings.upload_dir
        self.max_file_size = settings.max_file_size
        self.allowed_extensions = {ext.lower(): self._get_file_type_description(ext)
                                  for ext in settings.allowed_extensions}
        self.database = database
        self.files_collection = database[FILE_METADATA_COLLECTION] if database else None

        # Ensure upload directory exists
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
    
    def _get_file_type_description(self, extension: str) -> str:
        """Get human-readable description for file extension."""
        descriptions = {
            '.pdf': 'PDF Document',
            '.txt': 'Text File',
            '.md': 'Markdown File',
            '.doc': 'Word Document',
            '.docx': 'Word Document',
            '.xls': 'Excel Spreadsheet',
            '.xlsx': 'Excel Spreadsheet'
        }
        return descriptions.get(extension.lower(), 'Unknown File Type')
    
    def is_supported_file(self, filename: str) -> bool:
        """Check if the file extension is supported."""
        file_extension = Path(filename).suffix.lower()
        return file_extension in self.allowed_extensions
    
    def get_file_type(self, filename: str) -> str:
        """Get the file type description."""
        file_extension = Path(filename).suffix.lower()
        return self.allowed_extensions.get(file_extension, 'Unknown')
    
    def validate_file(self, file: UploadFile) -> None:
        """Validate uploaded file."""
        # Check file extension
        if not self.is_supported_file(file.filename):
            supported_types = list(self.allowed_extensions.keys())
            raise FileTypeNotSupportedHTTPException(
                Path(file.filename).suffix.lower(),
                supported_types
            )
        
        # Check file size if available
        if hasattr(file, 'size') and file.size:
            if file.size > self.max_file_size:
                raise FileTooLargeHTTPException(file.size, self.max_file_size)
    
    async def save_file(
        self,
        file: UploadFile,
        user: UserInDB,
        is_public: bool
    ) -> tuple[str, FileMetadataInDB]:
        """
        Save an uploaded file with user context and metadata.

        Args:
            file: Uploaded file
            user: User uploading the file
            is_public: Whether file is public (admin) or private (student)

        Returns:
            tuple: (file_path, file_metadata)
        """
        try:
            # Validate file
            self.validate_file(file)

            # Create file path
            file_path = os.path.join(self.upload_dir, file.filename)

            # Handle file name conflicts
            actual_filename = file.filename
            if os.path.exists(file_path):
                file_path = self._get_unique_filename(file_path)
                actual_filename = Path(file_path).name

            # Save file
            with open(file_path, "wb") as f:
                content = file.file.read()

                # Additional size check after reading
                if len(content) > self.max_file_size:
                    raise FileTooLargeHTTPException(len(content), self.max_file_size)

                f.write(content)

            # Create file metadata
            file_metadata = FileMetadataInDB(
                filename=actual_filename,
                user_id=str(user.id),
                auth0_id=user.auth0_id,
                is_public=is_public,
                file_size=len(content),
                file_type=Path(actual_filename).suffix.lower()
            )

            # Store in MongoDB
            if self.files_collection:
                await self.files_collection.insert_one(
                    file_metadata.model_dump(by_alias=True, exclude={"id"})
                )

            logger.info(f"File saved: {file_path} (user: {user.email}, public: {is_public})")
            return file_path, file_metadata

        except (FileTypeNotSupportedHTTPException, FileTooLargeHTTPException):
            raise
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise FileProcessingException(f"Error saving file: {str(e)}")
    
    def _get_unique_filename(self, file_path: str) -> str:
        """Generate a unique filename if the file already exists."""
        path = Path(file_path)
        base_name = path.stem
        extension = path.suffix
        directory = path.parent
        
        counter = 1
        while os.path.exists(file_path):
            new_filename = f"{base_name}_{counter}{extension}"
            file_path = directory / new_filename
            counter += 1
        
        return str(file_path)
    
    async def list_files(self, user: UserInDB) -> List[FileMetadataInDB]:
        """
        List files based on user role and permissions.

        Students: See their private files + all public files
        Admins: See only public files (no access to student private files)

        Args:
            user: Current user

        Returns:
            List of FileMetadataInDB documents
        """
        try:
            if not self.files_collection:
                return []

            # Build query based on role
            if user.role == settings.student_role:
                # Students see: their private files + all public files
                query = {
                    "$or": [
                        {"user_id": str(user.id)},  # Their files
                        {"is_public": True}  # All public files
                    ]
                }
            elif user.role == settings.admin_role:
                # Admins see: only public files
                query = {"is_public": True}
            else:
                # Unknown role, no access
                return []

            cursor = self.files_collection.find(query).sort("uploaded_at", -1)
            files = []

            async for file_doc in cursor:
                files.append(FileMetadataInDB(**file_doc))

            return files

        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            raise FileProcessingException(f"Error listing files: {str(e)}")
    
    def get_file_info(self, filename: str) -> FileInfo:
        """Get detailed information about a specific file."""
        try:
            file_path = os.path.join(self.upload_dir, filename)
            
            if not os.path.exists(file_path):
                raise FileNotFoundHTTPException(filename)
            
            return self._get_file_metadata(filename, file_path)
            
        except FileNotFoundHTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            raise FileProcessingException(f"Error getting file info: {str(e)}")
    
    def _get_file_metadata(self, filename: str, file_path: str) -> FileInfo:
        """Get file metadata."""
        file_stat = os.stat(file_path)
        
        return FileInfo(
            filename=filename,
            file_path=file_path,
            file_type=self.get_file_type(filename),
            size_bytes=file_stat.st_size,
            size_mb=round(file_stat.st_size / (1024 * 1024), 2),
            created_at=file_stat.st_ctime,
            modified_at=file_stat.st_mtime,
            is_supported=self.is_supported_file(filename)
        )
    
    async def delete_file(self, filename: str, user: UserInDB) -> bool:
        """
        Delete a file with permission checking.

        Students can only delete their own private files.
        Admins can only delete public files.

        Args:
            filename: Name of file to delete
            user: Current user

        Returns:
            bool: True if deleted successfully

        Raises:
            FileNotFoundHTTPException: If file not found
            ForbiddenHTTPException: If user doesn't have permission
        """
        try:
            # Get file metadata from MongoDB
            if not self.files_collection:
                raise FileProcessingException("Database not available")

            file_metadata = await self.files_collection.find_one({"filename": filename})

            if not file_metadata:
                raise FileNotFoundHTTPException(filename)

            # Check permissions
            if user.role == settings.student_role:
                # Students can only delete their own files
                if file_metadata["user_id"] != str(user.id):
                    raise ForbiddenHTTPException("You can only delete your own files")

            elif user.role == settings.admin_role:
                # Admins can only delete public files
                if not file_metadata["is_public"]:
                    raise ForbiddenHTTPException("Admins cannot delete student private files")

            # Delete from filesystem
            file_path = os.path.join(self.upload_dir, filename)

            if os.path.exists(file_path):
                os.remove(file_path)

            # Delete from MongoDB
            await self.files_collection.delete_one({"filename": filename})

            logger.info(f"File deleted: {filename} by user {user.email}")
            return True

        except (FileNotFoundHTTPException, ForbiddenHTTPException):
            raise
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            raise FileProcessingException(f"Error deleting file: {str(e)}")
    
    async def get_file_metadata_by_name(self, filename: str) -> Optional[FileMetadataInDB]:
        """
        Get file metadata from MongoDB by filename.

        Args:
            filename: Name of file

        Returns:
            FileMetadataInDB or None if not found
        """
        if not self.files_collection:
            return None

        file_doc = await self.files_collection.find_one({"filename": filename})

        if not file_doc:
            return None

        return FileMetadataInDB(**file_doc)

    async def can_user_access_file(self, filename: str, user: UserInDB) -> bool:
        """
        Check if user has permission to access a file.

        Args:
            filename: Name of file
            user: Current user

        Returns:
            bool: True if user can access the file
        """
        file_metadata = await self.get_file_metadata_by_name(filename)

        if not file_metadata:
            return False

        # Public files are accessible to everyone
        if file_metadata.is_public:
            return True

        # Students can access their own private files
        if user.role == settings.student_role and file_metadata.user_id == str(user.id):
            return True

        # Admins cannot access student private files
        return False

    async def update_file_processed_status(
        self,
        filename: str,
        processed: bool,
        chunk_count: int = 0
    ):
        """
        Update file's processed status and chunk count.

        Args:
            filename: Name of file
            processed: Whether file has been processed
            chunk_count: Number of chunks generated
        """
        if not self.files_collection:
            return

        await self.files_collection.update_one(
            {"filename": filename},
            {
                "$set": {
                    "processed": processed,
                    "chunk_count": chunk_count
                }
            }
        )

    def get_supported_extensions(self) -> Dict[str, str]:
        """Get supported file extensions and their descriptions."""
        return self.allowed_extensions.copy()


# Global file service instance (will be initialized with database in main.py)
file_service: Optional[FileService] = None


def get_file_service_instance(database: Optional[AsyncIOMotorDatabase] = None) -> FileService:
    """
    Get or create file service instance with database support.

    Args:
        database: MongoDB database instance

    Returns:
        FileService instance
    """
    global file_service

    if file_service is None:
        file_service = FileService(database)

    return file_service
