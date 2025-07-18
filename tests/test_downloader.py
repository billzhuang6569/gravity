"""
Unit tests for DownloaderService.

Tests cover video info extraction, download functionality, error handling,
and Chinese error message conversion.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from app.services.downloader import DownloaderService, VideoInfoError, DownloadError
from app.models.schemas import DownloadOptions, VideoFormat


class TestDownloaderService:
    """Test suite for DownloaderService class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def downloader_service(self, temp_dir):
        """Create DownloaderService instance with temporary directory."""
        return DownloaderService(download_dir=temp_dir)
    
    @pytest.fixture
    def mock_video_info(self):
        """Mock video info data from yt-dlp."""
        return {
            'title': '测试视频标题',
            'duration': 180,  # 3 minutes
            'uploader': '测试上传者',
            'upload_date': '20240116',
            'view_count': 12345,
            'description': '这是一个测试视频的描述',
            'formats': [
                {
                    'format_id': '137',
                    'ext': 'mp4',
                    'height': 1080,
                    'filesize': 50000000,
                    'format_note': '1080p'
                },
                {
                    'format_id': '136',
                    'ext': 'mp4',
                    'height': 720,
                    'filesize': 30000000,
                    'format_note': '720p'
                },
                {
                    'format_id': '140',
                    'ext': 'm4a',
                    'filesize': 5000000,
                    'format_note': 'audio'
                }
            ]
        }
    
    def test_init_creates_download_directory(self, temp_dir):
        """Test that DownloaderService creates download directory."""
        download_dir = Path(temp_dir) / "downloads"
        service = DownloaderService(download_dir=str(download_dir))
        
        assert download_dir.exists()
        assert download_dir.is_dir()
    
    def test_yt_dlp_version_constant(self, downloader_service):
        """Test that YT_DLP_VERSION is set correctly."""
        assert downloader_service.YT_DLP_VERSION == "2023.12.30"
    
    def test_error_messages_mapping(self, downloader_service):
        """Test that error messages are properly mapped to Chinese."""
        assert "视频不存在或已被删除" in downloader_service.ERROR_MESSAGES.values()
        assert "网络连接错误，请稍后重试" in downloader_service.ERROR_MESSAGES.values()
        assert "视频存在地区限制" in downloader_service.ERROR_MESSAGES.values()
    
    @patch('app.services.downloader.yt_dlp.YoutubeDL')
    def test_get_video_info_success(self, mock_ydl_class, downloader_service, mock_video_info):
        """Test successful video info extraction."""
        # Setup mock
        mock_ydl = Mock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = mock_video_info
        
        # Test
        result = downloader_service.get_video_info("https://www.youtube.com/watch?v=test")
        
        # Assertions
        assert result['title'] == '测试视频标题'
        assert result['duration'] == '03:00'
        assert result['uploader'] == '测试上传者'
        assert len(result['formats']) == 3
        
        # Check format parsing
        formats = result['formats']
        assert any(f['quality'] == '1080p' for f in formats)
        assert any(f['quality'] == '720p' for f in formats)
    
    @patch('app.services.downloader.yt_dlp.YoutubeDL')
    def test_get_video_info_no_info_returned(self, mock_ydl_class, downloader_service):
        """Test video info extraction when no info is returned."""
        # Setup mock
        mock_ydl = Mock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = None
        
        # Test
        with pytest.raises(VideoInfoError) as exc_info:
            downloader_service.get_video_info("https://www.youtube.com/watch?v=test")
        
        assert "无法获取视频信息" in str(exc_info.value)
    
    @patch('app.services.downloader.yt_dlp.YoutubeDL')
    def test_get_video_info_download_error(self, mock_ydl_class, downloader_service):
        """Test video info extraction with DownloadError."""
        from yt_dlp.utils import DownloadError as YtDlpDownloadError
        
        # Setup mock
        mock_ydl = Mock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.side_effect = YtDlpDownloadError("Video unavailable")
        
        # Test
        with pytest.raises(VideoInfoError) as exc_info:
            downloader_service.get_video_info("https://www.youtube.com/watch?v=test")
        
        assert "视频不存在或已被删除" in str(exc_info.value)
    
    def test_parse_formats(self, downloader_service):
        """Test format parsing from yt-dlp format data."""
        formats_data = [
            {
                'format_id': '137',
                'ext': 'mp4',
                'height': 1080,
                'filesize': 50000000,
                'format_note': '1080p'
            },
            {
                'format_id': '136',
                'ext': 'mp4',
                'height': 720,
                'filesize': 30000000,
                'format_note': '720p'
            }
        ]
        
        result = downloader_service._parse_formats(formats_data)
        
        assert len(result) == 2
        assert result[0].quality == '1080p'  # Should be sorted with best first
        assert result[1].quality == '720p'
        assert all(isinstance(f, VideoFormat) for f in result)
    
    def test_extract_quality(self, downloader_service):
        """Test quality extraction from format info."""
        # Test with height
        fmt_with_height = {'height': 1080, 'format_id': '137'}
        assert downloader_service._extract_quality(fmt_with_height) == '1080p'
        
        # Test with format_note
        fmt_with_note = {'format_note': '720p', 'format_id': '136'}
        assert downloader_service._extract_quality(fmt_with_note) == '720p'
        
        # Test fallback to format_id
        fmt_fallback = {'format_id': '140'}
        assert downloader_service._extract_quality(fmt_fallback) == '140'
    
    def test_quality_sort_key(self, downloader_service):
        """Test quality sorting key generation."""
        assert downloader_service._quality_sort_key('1080p') > downloader_service._quality_sort_key('720p')
        assert downloader_service._quality_sort_key('720p') > downloader_service._quality_sort_key('480p')
        assert downloader_service._quality_sort_key('unknown') == 0
    
    def test_build_download_options_video(self, downloader_service):
        """Test building yt-dlp options for video download."""
        options = DownloadOptions(quality="720p", format="video")
        result = downloader_service._build_download_options(options)
        
        assert 'format' in result
        assert 'best[height<=720]' in result['format']
        assert 'postprocessors' not in result
    
    def test_build_download_options_audio(self, downloader_service):
        """Test building yt-dlp options for audio download."""
        options = DownloadOptions(format="audio", audio_format="mp3")
        result = downloader_service._build_download_options(options)
        
        assert result['format'] == 'bestaudio/best'
        assert 'postprocessors' in result
        assert result['postprocessors'][0]['preferredcodec'] == 'mp3'
    
    def test_generate_filename(self, downloader_service):
        """Test filename generation with task_id."""
        options = DownloadOptions(format="video")
        
        # With task_id
        filename = downloader_service._generate_filename("测试视频", "task123", options)
        assert "测试视频_task123.%(ext)s" == filename
        
        # Without task_id
        filename = downloader_service._generate_filename("测试视频", None, options)
        assert "测试视频.%(ext)s" == filename
        
        # Audio format
        options_audio = DownloadOptions(format="audio")
        filename = downloader_service._generate_filename("测试音频", "task456", options_audio)
        assert "测试音频_task456.%(ext)s" == filename
    
    def test_sanitize_filename(self, downloader_service):
        """Test filename sanitization."""
        # Test invalid characters removal
        result = downloader_service._sanitize_filename('test<>:"/\\|?*video')
        assert result == 'testvideo'
        
        # Test whitespace replacement
        result = downloader_service._sanitize_filename('test   video   name')
        assert result == 'test_video_name'
        
        # Test length limiting
        long_name = 'a' * 150
        result = downloader_service._sanitize_filename(long_name)
        assert len(result) == 100
        
        # Test empty string fallback
        result = downloader_service._sanitize_filename('')
        assert result == 'video'
    
    def test_format_duration(self, downloader_service):
        """Test duration formatting."""
        # Test hours, minutes, seconds
        assert downloader_service._format_duration(3661) == "01:01:01"
        
        # Test minutes and seconds only
        assert downloader_service._format_duration(125) == "02:05"
        
        # Test seconds only
        assert downloader_service._format_duration(45) == "00:45"
    
    def test_parse_error_specific_messages(self, downloader_service):
        """Test error message parsing for specific error types."""
        # Test video unavailable
        result = downloader_service._parse_error("Video unavailable")
        assert result == "视频不存在或已被删除"
        
        # Test geographic restriction
        result = downloader_service._parse_error("not available in your country")
        assert result == "视频存在地区限制，无法访问"
        
        # Test HTTP errors
        result = downloader_service._parse_error("HTTP Error 404")
        assert result == "视频不存在或链接无效"
        
        # Test network errors
        result = downloader_service._parse_error("Connection timeout")
        assert result == "网络连接错误，请稍后重试"
        
        # Test unknown error
        result = downloader_service._parse_error("Some random error")
        assert result == "未知错误，请稍后重试"
    
    @patch('app.services.downloader.yt_dlp.YoutubeDL')
    def test_download_video_success(self, mock_ydl_class, downloader_service, mock_video_info, temp_dir):
        """Test successful video download."""
        # Setup mock
        mock_ydl = Mock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = mock_video_info
        mock_ydl.download.return_value = None
        
        # Create a fake downloaded file
        test_file = Path(temp_dir) / "测试视频标题_task123.mp4"
        test_file.touch()
        
        # Mock file finding
        with patch.object(downloader_service, '_find_downloaded_file', return_value=test_file):
            options = DownloadOptions(quality="720p", format="video")
            result = downloader_service.download_video(
                "https://www.youtube.com/watch?v=test",
                options,
                task_id="task123"
            )
        
        # Check the new return format
        assert isinstance(result, dict)
        assert result['file_path'] == str(test_file)
        assert result['title'] == '测试视频标题'
        assert 'download_url' in result
        assert 'file_size_mb' in result
        assert 'filename' in result
        assert 'extension' in result
    
    @patch('app.services.downloader.yt_dlp.YoutubeDL')
    def test_download_video_with_progress_callback(self, mock_ydl_class, downloader_service, mock_video_info, temp_dir):
        """Test video download with progress callback."""
        # Setup mock
        mock_ydl = Mock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = mock_video_info
        
        # Create a fake downloaded file
        test_file = Path(temp_dir) / "测试视频标题_task123.mp4"
        test_file.touch()
        
        # Mock progress callback
        progress_callback = Mock()
        
        with patch.object(downloader_service, '_find_downloaded_file', return_value=test_file):
            options = DownloadOptions(quality="720p", format="video")
            downloader_service.download_video(
                "https://www.youtube.com/watch?v=test",
                options,
                progress_callback=progress_callback,
                task_id="task123"
            )
        
        # Verify progress callback was added to options
        call_args = mock_ydl_class.call_args_list
        assert len(call_args) >= 1
        ydl_opts = call_args[-1][0][0]  # Get the options from the last call
        assert 'progress_hooks' in ydl_opts
        assert progress_callback in ydl_opts['progress_hooks']
    
    @patch('app.services.downloader.yt_dlp.YoutubeDL')
    def test_download_video_no_info(self, mock_ydl_class, downloader_service):
        """Test download failure when no video info is available."""
        # Setup mock
        mock_ydl = Mock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = None
        
        options = DownloadOptions(quality="720p", format="video")
        
        with pytest.raises(DownloadError) as exc_info:
            downloader_service.download_video(
                "https://www.youtube.com/watch?v=test",
                options,
                task_id="task123"
            )
        
        assert "无法获取视频信息" in str(exc_info.value)
    
    @patch('app.services.downloader.yt_dlp.YoutubeDL')
    def test_download_video_file_not_found(self, mock_ydl_class, downloader_service, mock_video_info):
        """Test download failure when downloaded file is not found."""
        # Setup mock
        mock_ydl = Mock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = mock_video_info
        mock_ydl.download.return_value = None
        
        # Mock file finding to return None (file not found)
        with patch.object(downloader_service, '_find_downloaded_file', return_value=None):
            options = DownloadOptions(quality="720p", format="video")
            
            with pytest.raises(DownloadError) as exc_info:
                downloader_service.download_video(
                    "https://www.youtube.com/watch?v=test",
                    options,
                    task_id="task123"
                )
        
        assert "下载完成但无法找到文件" in str(exc_info.value)
    
    def test_find_downloaded_file(self, downloader_service, temp_dir):
        """Test finding downloaded files."""
        # Create test files
        test_file1 = Path(temp_dir) / "test_video_task123.mp4"
        test_file2 = Path(temp_dir) / "test_video_task123.webm"
        test_file1.touch()
        test_file2.touch()
        
        # Test finding file
        result = downloader_service._find_downloaded_file("test_video_task123.%(ext)s")
        assert result is not None
        assert result.name in ["test_video_task123.mp4", "test_video_task123.webm"]
        
        # Test file not found
        result = downloader_service._find_downloaded_file("nonexistent.%(ext)s")
        assert result is None


class TestVideoInfoError:
    """Test VideoInfoError exception class."""
    
    def test_video_info_error_creation(self):
        """Test VideoInfoError creation with message and original error."""
        original_error = Exception("Original error")
        error = VideoInfoError("Test message", original_error)
        
        assert error.message == "Test message"
        assert error.original_error == original_error
        assert str(error) == "Test message"
    
    def test_video_info_error_without_original(self):
        """Test VideoInfoError creation without original error."""
        error = VideoInfoError("Test message")
        
        assert error.message == "Test message"
        assert error.original_error is None


class TestDownloadError:
    """Test DownloadError exception class."""
    
    def test_download_error_creation(self):
        """Test DownloadError creation with message and original error."""
        original_error = Exception("Original error")
        error = DownloadError("Test message", original_error)
        
        assert error.message == "Test message"
        assert error.original_error == original_error
        assert str(error) == "Test message"
    
    def test_download_error_without_original(self):
        """Test DownloadError creation without original error."""
        error = DownloadError("Test message")
        
        assert error.message == "Test message"
        assert error.original_error is None


if __name__ == "__main__":
    pytest.main([__file__])