"""File management service."""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from fastapi import UploadFile

from app.core.config import get_settings
from app.core.exceptions import (
    FileValidationException,
    FileProcessingException,
    FileNotFoundHTTPException,
    FileTypeNotSupportedHTTPException,
    FileTooLargeHTTPException
)
from app.models.responses import FileInfo

logger = logging.getLogger(__name__)
settings = get_settings()


class FileService:
    """Service for handling file operations."""
    
    def __init__(self):
        self.upload_dir = settings.upload_dir
        self.max_file_size = settings.max_file_size
        self.allowed_extensions = {ext.lower(): self._get_file_type_description(ext) 
                                  for ext in settings.allowed_extensions}
        
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
    
    def save_file(self, file: UploadFile) -> str:
        """Save an uploaded file to the uploads directory."""
        try:
            # Validate file
            self.validate_file(file)
            
            # Create file path
            file_path = os.path.join(self.upload_dir, file.filename)
            
            # Handle file name conflicts
            if os.path.exists(file_path):
                file_path = self._get_unique_filename(file_path)
            
            # Save file
            with open(file_path, "wb") as f:
                content = file.file.read()
                
                # Additional size check after reading
                if len(content) > self.max_file_size:
                    raise FileTooLargeHTTPException(len(content), self.max_file_size)
                
                f.write(content)
            
            logger.info(f"File saved: {file_path}")
            return file_path
            
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
    
    def list_files(self) -> List[FileInfo]:
        """List all files in the uploads directory with metadata."""
        try:
            files_info = []
            
            if not os.path.exists(self.upload_dir):
                return files_info
            
            for filename in os.listdir(self.upload_dir):
                file_path = os.path.join(self.upload_dir, filename)
                
                if os.path.isfile(file_path):
                    file_info = self._get_file_metadata(filename, file_path)
                    files_info.append(file_info)
            
            # Sort by modification time (newest first)
            files_info.sort(key=lambda x: x.modified_at, reverse=True)
            
            return files_info
            
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
    
    def delete_file(self, filename: str) -> bool:
        """Delete a file from the uploads directory."""
        try:
            file_path = os.path.join(self.upload_dir, filename)
            
            if not os.path.exists(file_path):
                raise FileNotFoundHTTPException(filename)
            
            os.remove(file_path)
            logger.info(f"File deleted: {file_path}")
            return True
            
        except FileNotFoundHTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            raise FileProcessingException(f"Error deleting file: {str(e)}")
    
    def get_supported_extensions(self) -> Dict[str, str]:
        """Get supported file extensions and their descriptions."""
        return self.allowed_extensions.copy()


# Global file service instance
file_service = FileService()
