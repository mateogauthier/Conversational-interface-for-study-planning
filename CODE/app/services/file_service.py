"""File management service."""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from fastapi import UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from bson import ObjectId
import tempfile

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
        self.max_file_size = settings.max_file_size
        self.allowed_extensions = {ext.lower(): self._get_file_type_description(ext)
                                  for ext in settings.allowed_extensions}
        self.database = database
        self.files_collection = database[FILE_METADATA_COLLECTION] if database is not None else None
        # GridFS bucket for file storage
        self.fs_bucket = AsyncIOMotorGridFSBucket(database) if database is not None else None
    
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
        Save an uploaded file with user context and metadata using GridFS.

        Args:
            file: Uploaded file
            user: User uploading the file
            is_public: Whether file is public (admin) or private (student)

        Returns:
            tuple: (gridfs_file_id_str, file_metadata)
        """
        try:
            # Validate file
            self.validate_file(file)

            if self.fs_bucket is None or self.files_collection is None:
                raise FileProcessingException("Database not available")

            # Read file content
            content = await file.read()

            # Size check after reading
            if len(content) > self.max_file_size:
                raise FileTooLargeHTTPException(len(content), self.max_file_size)

            # Handle filename conflicts by checking MongoDB metadata
            actual_filename = file.filename
            counter = 1
            while await self.files_collection.find_one({"filename": actual_filename}):
                path = Path(file.filename)
                actual_filename = f"{path.stem}_{counter}{path.suffix}"
                counter += 1

            # Upload to GridFS with metadata
            file_id = await self.fs_bucket.upload_from_stream(
                actual_filename,
                content,
                metadata={
                    "user_id": str(user.id),
                    "auth0_id": user.auth0_id,
                    "is_public": is_public,
                    "file_type": Path(actual_filename).suffix.lower(),
                    "uploaded_at": datetime.utcnow()
                }
            )

            # Create file metadata document
            file_metadata = FileMetadataInDB(
                filename=actual_filename,
                user_id=str(user.id),
                auth0_id=user.auth0_id,
                is_public=is_public,
                file_size=len(content),
                file_type=Path(actual_filename).suffix.lower(),
                gridfs_file_id=str(file_id)  # Store GridFS file ID
            )

            # Store metadata in MongoDB
            await self.files_collection.insert_one(
                file_metadata.model_dump(by_alias=True, exclude={"id"})
            )

            logger.info(f"File saved to GridFS: {actual_filename} (id: {file_id}, user: {user.email}, public: {is_public})")
            return str(file_id), file_metadata

        except (FileTypeNotSupportedHTTPException, FileTooLargeHTTPException):
            raise
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise FileProcessingException(f"Error saving file: {str(e)}")
    
    async def get_file_from_gridfs(self, filename: str) -> Optional[bytes]:
        """
        Download file content from GridFS by filename.

        Args:
            filename: Name of file to retrieve

        Returns:
            File content as bytes, or None if not found
        """
        if self.fs_bucket is None:
            return None

        try:
            # Find file metadata to get GridFS ID
            file_metadata = await self.get_file_metadata_by_name(filename)
            if not file_metadata or not file_metadata.gridfs_file_id:
                return None

            # Download from GridFS
            file_id = ObjectId(file_metadata.gridfs_file_id)
            grid_out = await self.fs_bucket.open_download_stream(file_id)
            content = await grid_out.read()
            return content

        except Exception as e:
            logger.error(f"Error retrieving file from GridFS: {str(e)}")
            return None

    async def download_file_to_temp(self, filename: str) -> Optional[str]:
        """
        Download file from GridFS to a temporary file.
        Returns path to temporary file, or None if file not found.
        Caller is responsible for deleting the temporary file.

        Args:
            filename: Name of file to download

        Returns:
            Path to temporary file, or None if not found
        """
        content = await self.get_file_from_gridfs(filename)
        if content is None:
            return None

        try:
            # Create temporary file with same extension
            ext = Path(filename).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
                tmp_file.write(content)
                tmp_path = tmp_file.name

            return tmp_path

        except Exception as e:
            logger.error(f"Error creating temporary file: {str(e)}")
            return None
    
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
            if self.files_collection is None:
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

    async def list_all_files(self) -> List[Dict[str, Any]]:
        """
        List ALL files in database (admin utility for reindexing).

        Returns:
            List of file metadata dictionaries
        """
        try:
            if self.files_collection is None:
                return []

            cursor = self.files_collection.find({}).sort("uploaded_at", -1)
            files = []

            async for file_doc in cursor:
                files.append(file_doc)

            return files

        except Exception as e:
            logger.error(f"Error listing all files: {str(e)}")
            raise FileProcessingException(f"Error listing all files: {str(e)}")

    async def get_file_info(self, filename: str) -> FileInfo:
        """Get detailed information about a specific file from GridFS."""
        try:
            file_metadata = await self.get_file_metadata_by_name(filename)

            if not file_metadata:
                raise FileNotFoundHTTPException(filename)

            return FileInfo(
                filename=filename,
                file_path=f"gridfs://{file_metadata.gridfs_file_id}",
                file_type=self.get_file_type(filename),
                size_bytes=file_metadata.file_size,
                size_mb=round(file_metadata.file_size / (1024 * 1024), 2),
                created_at=file_metadata.uploaded_at.timestamp() if file_metadata.uploaded_at else 0,
                modified_at=file_metadata.uploaded_at.timestamp() if file_metadata.uploaded_at else 0,
                is_supported=self.is_supported_file(filename)
            )

        except FileNotFoundHTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            raise FileProcessingException(f"Error getting file info: {str(e)}")
    
    async def delete_file(self, filename: str, user: UserInDB) -> bool:
        """
        Delete a file from GridFS with permission checking.

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
            if self.files_collection is None or self.fs_bucket is None:
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

            # Delete from GridFS
            if file_metadata.get("gridfs_file_id"):
                try:
                    file_id = ObjectId(file_metadata["gridfs_file_id"])
                    await self.fs_bucket.delete(file_id)
                except Exception as e:
                    logger.warning(f"Error deleting from GridFS (may not exist): {str(e)}")

            # Delete metadata from MongoDB
            await self.files_collection.delete_one({"filename": filename})

            logger.info(f"File deleted from GridFS: {filename} by user {user.email}")
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
        if self.files_collection is None:
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
        if self.files_collection is None:
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

    async def track_file_usage(self, filename: str) -> None:
        """
        Track that a file was used in a conversation.
        Increments total_uses and updates last_used timestamp.

        Args:
            filename: Name of file to track
        """
        if self.files_collection is None:
            logger.warning("Database not available, cannot track file usage")
            return

        try:
            await self.files_collection.update_one(
                {"filename": filename},
                {
                    "$inc": {"feedback_stats.total_uses": 1},
                    "$set": {"feedback_stats.last_used": datetime.utcnow()}
                }
            )
            logger.debug(f"Tracked usage for file: {filename}")
        except Exception as e:
            logger.error(f"Error tracking file usage for {filename}: {str(e)}")

    async def track_file_view(self, filename: str) -> None:
        """
        Track that a file was viewed (opened/listed).
        Increments total_views counter.

        Args:
            filename: Name of file to track
        """
        if self.files_collection is None:
            logger.warning("Database not available, cannot track file view")
            return

        try:
            await self.files_collection.update_one(
                {"filename": filename},
                {"$inc": {"feedback_stats.total_views": 1}}
            )
            logger.debug(f"Tracked view for file: {filename}")
        except Exception as e:
            logger.error(f"Error tracking file view for {filename}: {str(e)}")

    async def update_file_feedback(
        self,
        filename: str,
        new_feedback: str,
        previous_feedback: Optional[str] = None
    ) -> None:
        """
        Update file feedback statistics.
        Handles incrementing/decrementing likes/dislikes when feedback changes.

        Args:
            filename: Name of file
            new_feedback: New feedback value ('like' or 'dislike')
            previous_feedback: Previous feedback value (if any)
        """
        if self.files_collection is None:
            logger.warning("Database not available, cannot update file feedback")
            return

        try:
            update_ops = {}

            # Handle removing previous feedback
            if previous_feedback == "like":
                update_ops["$inc"] = {"feedback_stats.total_likes": -1}
            elif previous_feedback == "dislike":
                update_ops["$inc"] = {"feedback_stats.total_dislikes": -1}

            # Handle adding new feedback
            if new_feedback == "like":
                if "$inc" in update_ops:
                    update_ops["$inc"]["feedback_stats.total_likes"] = \
                        update_ops["$inc"].get("feedback_stats.total_likes", 0) + 1
                else:
                    update_ops["$inc"] = {"feedback_stats.total_likes": 1}
            elif new_feedback == "dislike":
                if "$inc" in update_ops:
                    update_ops["$inc"]["feedback_stats.total_dislikes"] = \
                        update_ops["$inc"].get("feedback_stats.total_dislikes", 0) + 1
                else:
                    update_ops["$inc"] = {"feedback_stats.total_dislikes": 1}

            if update_ops:
                await self.files_collection.update_one(
                    {"filename": filename},
                    update_ops
                )
                logger.debug(f"Updated feedback for file {filename}: {new_feedback}")

        except Exception as e:
            logger.error(f"Error updating file feedback for {filename}: {str(e)}")

    async def extract_text_from_file(self, filename: str) -> Optional[str]:
        """
        Extract full text content from a file stored in GridFS.

        Args:
            filename: Name of file to extract text from

        Returns:
            Extracted text content, or None if extraction fails
        """
        try:
            # Download file to temporary location
            temp_path = await self.download_file_to_temp(filename)
            if not temp_path:
                logger.error(f"Could not download file {filename} to temp location")
                return None

            try:
                # Import document loaders
                from langchain_community.document_loaders import (
                    PyPDFLoader,
                    TextLoader,
                    UnstructuredWordDocumentLoader,
                    UnstructuredExcelLoader
                )

                # Determine loader based on file extension
                file_extension = Path(filename).suffix.lower()

                if file_extension == '.pdf':
                    loader = PyPDFLoader(temp_path)
                elif file_extension in ['.txt', '.md']:
                    loader = TextLoader(temp_path, encoding='utf-8')
                elif file_extension in ['.doc', '.docx']:
                    loader = UnstructuredWordDocumentLoader(temp_path)
                elif file_extension in ['.xls', '.xlsx']:
                    loader = UnstructuredExcelLoader(temp_path)
                else:
                    # Try to load as text file
                    loader = TextLoader(temp_path, encoding='utf-8')

                # Load documents
                documents = loader.load()

                # Combine all document text
                full_text = "\n\n".join([doc.page_content for doc in documents])

                logger.info(f"Extracted {len(full_text)} characters from {filename}")
                return full_text

            finally:
                # Clean up temporary file
                try:
                    os.remove(temp_path)
                except Exception as e:
                    logger.warning(f"Could not delete temp file {temp_path}: {e}")

        except Exception as e:
            logger.error(f"Error extracting text from {filename}: {str(e)}")
            return None


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

    if file_service is None or (database is not None and file_service.database is None):
        file_service = FileService(database)

    return file_service
