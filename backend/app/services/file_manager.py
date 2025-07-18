"""
File management service for handling file operations and URL generation.

This module provides functionality for file management, cleanup, and download URL generation
for the Gravity video downloader application.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import quote

from app.config import settings

logger = logging.getLogger(__name__)


class FileManager:
    """
    File management service for handling file operations and URL generation.
    
    This class provides methods for:
    - Generating download URLs for files
    - Validating file existence
    - File path management
    - Security checks for file access
    """
    
    def __init__(self):
        """Initialize the FileManager with configured paths."""
        self.downloads_path = Path(settings.downloads_path)
        self.temp_path = Path(settings.temp_path)
        
        # Ensure directories exist
        self.downloads_path.mkdir(parents=True, exist_ok=True)
        self.temp_path.mkdir(parents=True, exist_ok=True)
    
    def generate_download_url(self, file_path: str) -> Optional[str]:
        """
        Generate a download URL for a given file path.
        
        Args:
            file_path: Absolute path to the file
            
        Returns:
            Download URL string or None if file doesn't exist or is invalid
        """
        try:
            file_path_obj = Path(file_path)
            
            # Check if file exists
            if not file_path_obj.exists():
                logger.warning(f"File not found for URL generation: {file_path}")
                return None
            
            # Check if file is within the downloads directory (security check)
            if not self._is_file_in_downloads(file_path_obj):
                logger.warning(f"File outside downloads directory: {file_path}")
                return None
            
            # Generate relative path from downloads directory
            relative_path = file_path_obj.relative_to(self.downloads_path)
            
            # URL encode the filename to handle special characters
            encoded_filename = quote(str(relative_path), safe='/')
            
            # Generate download URL
            download_url = f"/api/v1/downloads/{encoded_filename}"
            
            logger.info(f"Generated download URL: {download_url}")
            return download_url
            
        except Exception as e:
            logger.error(f"Error generating download URL for {file_path}: {e}")
            return None
    
    def _is_file_in_downloads(self, file_path: Path) -> bool:
        """
        Check if a file is within the downloads directory (security check).
        
        Args:
            file_path: Path object to check
            
        Returns:
            True if file is within downloads directory, False otherwise
        """
        try:
            # Resolve both paths to handle symlinks and relative paths
            file_path_resolved = file_path.resolve()
            downloads_path_resolved = self.downloads_path.resolve()
            
            # Check if the file path starts with the downloads path
            return str(file_path_resolved).startswith(str(downloads_path_resolved))
            
        except Exception as e:
            logger.error(f"Error checking file location: {e}")
            return False
    
    def validate_file_exists(self, file_path: str) -> bool:
        """
        Validate that a file exists and is accessible.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            True if file exists and is accessible, False otherwise
        """
        try:
            file_path_obj = Path(file_path)
            return file_path_obj.exists() and file_path_obj.is_file()
            
        except Exception as e:
            logger.error(f"Error validating file existence: {e}")
            return False
    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary containing file information or None if file doesn't exist
        """
        try:
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                return None
            
            stat_info = file_path_obj.stat()
            
            return {
                'size': stat_info.st_size,
                'size_mb': round(stat_info.st_size / (1024 * 1024), 2),
                'modified_time': stat_info.st_mtime,
                'extension': file_path_obj.suffix,
                'filename': file_path_obj.name
            }
            
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            return None
    
    def cleanup_file(self, file_path: str) -> bool:
        """
        Clean up (delete) a file.
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            True if file was deleted successfully, False otherwise
        """
        try:
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                logger.warning(f"File not found for cleanup: {file_path}")
                return True  # File doesn't exist, consider it cleaned up
            
            # Security check - only delete files in downloads or temp directories
            if not (self._is_file_in_downloads(file_path_obj) or 
                    self._is_file_in_temp(file_path_obj)):
                logger.error(f"Security violation: attempt to delete file outside allowed directories: {file_path}")
                return False
            
            file_path_obj.unlink()
            logger.info(f"File cleaned up successfully: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up file {file_path}: {e}")
            return False
    
    def _is_file_in_temp(self, file_path: Path) -> bool:
        """
        Check if a file is within the temp directory.
        
        Args:
            file_path: Path object to check
            
        Returns:
            True if file is within temp directory, False otherwise
        """
        try:
            # Resolve both paths to handle symlinks and relative paths
            file_path_resolved = file_path.resolve()
            temp_path_resolved = self.temp_path.resolve()
            
            # Check if the file path starts with the temp path
            return str(file_path_resolved).startswith(str(temp_path_resolved))
            
        except Exception as e:
            logger.error(f"Error checking temp file location: {e}")
            return False
    
    def get_download_directory_info(self) -> Dict[str, Any]:
        """
        Get information about the downloads directory.
        
        Returns:
            Dictionary containing directory information
        """
        try:
            if not self.downloads_path.exists():
                return {
                    'exists': False,
                    'path': str(self.downloads_path),
                    'total_files': 0,
                    'total_size_mb': 0
                }
            
            total_files = 0
            total_size = 0
            
            # Count files and calculate total size
            for file_path in self.downloads_path.rglob("*"):
                if file_path.is_file():
                    total_files += 1
                    total_size += file_path.stat().st_size
            
            return {
                'exists': True,
                'path': str(self.downloads_path),
                'total_files': total_files,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'available_space_gb': self._get_available_space_gb(self.downloads_path)
            }
            
        except Exception as e:
            logger.error(f"Error getting download directory info: {e}")
            return {
                'exists': False,
                'path': str(self.downloads_path),
                'total_files': 0,
                'total_size_mb': 0,
                'error': str(e)
            }
    
    def _get_available_space_gb(self, path: Path) -> float:
        """
        Get available disk space in GB for a given path.
        
        Args:
            path: Path to check disk space for
            
        Returns:
            Available space in GB
        """
        try:
            import shutil
            _, _, free = shutil.disk_usage(path)
            return round(free / (1024 * 1024 * 1024), 2)
            
        except Exception as e:
            logger.error(f"Error getting disk space: {e}")
            return 0.0
    
    def create_download_result(self, file_path: str, title: str = "") -> Dict[str, Any]:
        """
        Create a download result dictionary with file path and download URL.
        
        Args:
            file_path: Path to the downloaded file
            title: Video title (optional)
            
        Returns:
            Dictionary containing file_path, download_url, and title
        """
        try:
            download_url = self.generate_download_url(file_path)
            file_info = self.get_file_info(file_path)
            
            result = {
                'file_path': file_path,
                'download_url': download_url,
                'title': title
            }
            
            # Add file info if available
            if file_info:
                result.update({
                    'file_size_mb': file_info['size_mb'],
                    'filename': file_info['filename'],
                    'extension': file_info['extension']
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating download result: {e}")
            return {
                'file_path': file_path,
                'download_url': None,
                'title': title,
                'error': str(e)
            }