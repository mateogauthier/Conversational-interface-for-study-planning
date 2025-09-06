import os
import logging
from typing import List, Dict, Any
from pathlib import Path
from fastapi import UploadFile, HTTPException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    '.pdf': 'PDF Document',
    '.txt': 'Text File',
    '.md': 'Markdown File',
    '.doc': 'Word Document',
    '.docx': 'Word Document',
    '.xls': 'Excel Spreadsheet',
    '.xlsx': 'Excel Spreadsheet'
}

def is_supported_file(filename: str) -> bool:
    """Check if the file extension is supported."""
    file_extension = Path(filename).suffix.lower()
    return file_extension in SUPPORTED_EXTENSIONS

def get_file_type(filename: str) -> str:
    """Get the file type description."""
    file_extension = Path(filename).suffix.lower()
    return SUPPORTED_EXTENSIONS.get(file_extension, 'Unknown')

def save_file(file: UploadFile) -> str:
    """Save an uploaded file to the uploads directory."""
    try:
        # Validate file extension
        if not is_supported_file(file.filename):
            supported_types = ", ".join(SUPPORTED_EXTENSIONS.keys())
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported types: {supported_types}"
            )
        
        # Create file path
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        
        # Check if file already exists
        if os.path.exists(file_path):
            base_name = Path(file.filename).stem
            extension = Path(file.filename).suffix
            counter = 1
            while os.path.exists(file_path):
                new_filename = f"{base_name}_{counter}{extension}"
                file_path = os.path.join(UPLOAD_DIR, new_filename)
                counter += 1
        
        # Save file
        with open(file_path, "wb") as f:
            content = file.file.read()
            f.write(content)
        
        logger.info(f"File saved: {file_path}")
        return file_path
        
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

def list_files() -> List[Dict[str, Any]]:
    """List all files in the uploads directory with metadata."""
    try:
        files_info = []
        
        if not os.path.exists(UPLOAD_DIR):
            return files_info
        
        for filename in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            if os.path.isfile(file_path):
                file_stat = os.stat(file_path)
                file_info = {
                    "filename": filename,
                    "file_path": file_path,
                    "file_type": get_file_type(filename),
                    "size_bytes": file_stat.st_size,
                    "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
                    "created_at": file_stat.st_ctime,
                    "modified_at": file_stat.st_mtime,
                    "is_supported": is_supported_file(filename)
                }
                files_info.append(file_info)
        
        # Sort by modification time (newest first)
        files_info.sort(key=lambda x: x["modified_at"], reverse=True)
        
        return files_info
        
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        return []

def delete_file(filename: str) -> bool:
    """Delete a file from the uploads directory."""
    try:
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        os.remove(file_path)
        logger.info(f"File deleted: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

def get_file_info(filename: str) -> Dict[str, Any]:
    """Get detailed information about a specific file."""
    try:
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        file_stat = os.stat(file_path)
        
        return {
            "filename": filename,
            "file_path": file_path,
            "file_type": get_file_type(filename),
            "size_bytes": file_stat.st_size,
            "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
            "created_at": file_stat.st_ctime,
            "modified_at": file_stat.st_mtime,
            "is_supported": is_supported_file(filename)
        }
        
    except Exception as e:
        logger.error(f"Error getting file info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting file info: {str(e)}")
