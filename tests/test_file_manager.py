"""Tests for file manager service."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
import pytest

from app.services.file_manager import FileManager


class TestFileManager:
    """Test cases for FileManager service."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def file_manager(self, temp_dir):
        """Create a FileManager instance with temporary directories."""
        with patch('app.services.file_manager.settings') as mock_settings:
            mock_settings.downloads_path = temp_dir
            mock_settings.temp_path = os.path.join(temp_dir, 'temp')
            yield FileManager()
    
    def test_init_creates_directories(self, file_manager):
        """Test that FileManager creates necessary directories."""
        assert file_manager.downloads_path.exists()
        assert file_manager.temp_path.exists()
    
    def test_generate_download_url_success(self, file_manager, temp_dir):
        """Test successful download URL generation."""
        # Create a test file
        test_file = Path(temp_dir) / "test_video.mp4"
        test_file.touch()
        
        # Generate download URL
        download_url = file_manager.generate_download_url(str(test_file))
        
        assert download_url == "/downloads/test_video.mp4"
    
    def test_generate_download_url_nonexistent_file(self, file_manager, temp_dir):
        """Test download URL generation for non-existent file."""
        nonexistent_file = Path(temp_dir) / "nonexistent.mp4"
        
        download_url = file_manager.generate_download_url(str(nonexistent_file))
        
        assert download_url is None
    
    def test_generate_download_url_outside_downloads(self, file_manager, temp_dir):
        """Test download URL generation for file outside downloads directory."""
        # Create a file outside the downloads directory
        outside_file = Path(temp_dir).parent / "outside.mp4"
        outside_file.touch()
        
        try:
            download_url = file_manager.generate_download_url(str(outside_file))
            assert download_url is None
        finally:
            # Clean up
            if outside_file.exists():
                outside_file.unlink()
    
    def test_generate_download_url_with_special_characters(self, file_manager, temp_dir):
        """Test download URL generation with special characters in filename."""
        # Create a test file with special characters
        test_file = Path(temp_dir) / "测试视频 (1080p).mp4"
        test_file.touch()
        
        # Generate download URL
        download_url = file_manager.generate_download_url(str(test_file))
        
        # Check that special characters are URL encoded
        assert download_url is not None
        assert "测试视频" in download_url or "%E6%B5%8B%E8%AF%95%E8%A7%86%E9%A2%91" in download_url
    
    def test_validate_file_exists_success(self, file_manager, temp_dir):
        """Test file existence validation for existing file."""
        test_file = Path(temp_dir) / "test_file.mp4"
        test_file.touch()
        
        assert file_manager.validate_file_exists(str(test_file)) is True
    
    def test_validate_file_exists_nonexistent(self, file_manager, temp_dir):
        """Test file existence validation for non-existent file."""
        nonexistent_file = Path(temp_dir) / "nonexistent.mp4"
        
        assert file_manager.validate_file_exists(str(nonexistent_file)) is False
    
    def test_get_file_info_success(self, file_manager, temp_dir):
        """Test getting file information."""
        test_file = Path(temp_dir) / "test_file.mp4"
        test_file.write_text("test content")
        
        file_info = file_manager.get_file_info(str(test_file))
        
        assert file_info is not None
        assert file_info['filename'] == "test_file.mp4"
        assert file_info['extension'] == ".mp4"
        assert file_info['size'] > 0
        assert file_info['size_mb'] >= 0
        assert 'modified_time' in file_info
    
    def test_get_file_info_nonexistent(self, file_manager, temp_dir):
        """Test getting file information for non-existent file."""
        nonexistent_file = Path(temp_dir) / "nonexistent.mp4"
        
        file_info = file_manager.get_file_info(str(nonexistent_file))
        
        assert file_info is None
    
    def test_cleanup_file_success(self, file_manager, temp_dir):
        """Test successful file cleanup."""
        test_file = Path(temp_dir) / "test_file.mp4"
        test_file.touch()
        
        # Verify file exists
        assert test_file.exists()
        
        # Clean up file
        result = file_manager.cleanup_file(str(test_file))
        
        assert result is True
        assert not test_file.exists()
    
    def test_cleanup_file_nonexistent(self, file_manager, temp_dir):
        """Test cleanup of non-existent file."""
        nonexistent_file = Path(temp_dir) / "nonexistent.mp4"
        
        result = file_manager.cleanup_file(str(nonexistent_file))
        
        assert result is True  # Should return True for non-existent files
    
    def test_cleanup_file_outside_allowed_directories(self, file_manager, temp_dir):
        """Test cleanup prevention for files outside allowed directories."""
        # Create a file outside allowed directories
        outside_file = Path(temp_dir).parent / "outside.mp4"
        outside_file.touch()
        
        try:
            result = file_manager.cleanup_file(str(outside_file))
            assert result is False  # Should prevent cleanup of files outside allowed directories
        finally:
            # Clean up manually
            if outside_file.exists():
                outside_file.unlink()
    
    def test_get_download_directory_info(self, file_manager, temp_dir):
        """Test getting download directory information."""
        # Create some test files
        test_file1 = Path(temp_dir) / "file1.mp4"
        test_file2 = Path(temp_dir) / "file2.mp4"
        test_file1.write_text("test content 1")
        test_file2.write_text("test content 2")
        
        dir_info = file_manager.get_download_directory_info()
        
        assert dir_info['exists'] is True
        assert dir_info['path'] == temp_dir
        assert dir_info['total_files'] == 2
        assert dir_info['total_size_mb'] >= 0
        assert 'available_space_gb' in dir_info
    
    def test_create_download_result_success(self, file_manager, temp_dir):
        """Test creating download result dictionary."""
        test_file = Path(temp_dir) / "test_video.mp4"
        test_file.write_text("test content")
        
        result = file_manager.create_download_result(str(test_file), "Test Video")
        
        assert result['file_path'] == str(test_file)
        assert result['title'] == "Test Video"
        assert result['download_url'] == "/downloads/test_video.mp4"
        assert result['file_size_mb'] >= 0
        assert result['filename'] == "test_video.mp4"
        assert result['extension'] == ".mp4"
    
    def test_create_download_result_nonexistent_file(self, file_manager, temp_dir):
        """Test creating download result for non-existent file."""
        nonexistent_file = Path(temp_dir) / "nonexistent.mp4"
        
        result = file_manager.create_download_result(str(nonexistent_file), "Test Video")
        
        assert result['file_path'] == str(nonexistent_file)
        assert result['title'] == "Test Video"
        assert result['download_url'] is None
        assert 'error' not in result  # No error should be present, just None values
    
    def test_is_file_in_downloads_security_check(self, file_manager, temp_dir):
        """Test security check for file location."""
        # Test file within downloads directory
        inside_file = Path(temp_dir) / "inside.mp4"
        assert file_manager._is_file_in_downloads(inside_file) is True
        
        # Test file outside downloads directory
        outside_file = Path(temp_dir).parent / "outside.mp4"
        assert file_manager._is_file_in_downloads(outside_file) is False
    
    def test_is_file_in_temp_security_check(self, file_manager, temp_dir):
        """Test security check for temp file location."""
        # Test file within temp directory
        temp_file = file_manager.temp_path / "temp_file.mp4"
        assert file_manager._is_file_in_temp(temp_file) is True
        
        # Test file outside temp directory
        outside_file = Path(temp_dir).parent / "outside.mp4"
        assert file_manager._is_file_in_temp(outside_file) is False