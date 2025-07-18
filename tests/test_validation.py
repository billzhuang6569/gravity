"""
Unit tests for URL validation and platform detection service.

This module contains comprehensive tests for the validation service,
covering all supported platforms, error cases, and edge conditions.
"""

import pytest
from app.services.validation import (
    URLValidator,
    SupportedPlatform,
    ValidationError,
    validate_video_url,
    detect_video_platform,
    url_validator
)


class TestURLValidator:
    """Test cases for the URLValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = URLValidator()
    
    def test_init_compiles_patterns(self):
        """Test that URLValidator initializes and compiles regex patterns."""
        validator = URLValidator()
        assert len(validator.youtube_compiled) > 0
        assert len(validator.bilibili_compiled) > 0
    
    def test_validate_url_empty_string(self):
        """Test validation with empty string raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_url("")
        assert exc_info.value.error_code == "EMPTY_URL"
        assert "cannot be empty" in exc_info.value.message
    
    def test_validate_url_none(self):
        """Test validation with None raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_url(None)
        assert exc_info.value.error_code == "EMPTY_URL"
    
    def test_validate_url_whitespace_only(self):
        """Test validation with whitespace-only string raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_url("   ")
        assert exc_info.value.error_code == "EMPTY_URL"
    
    def test_validate_url_invalid_format(self):
        """Test validation with invalid URL format raises ValidationError."""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",
            "://missing-scheme",
            "http://",
            "just-text"
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValidationError) as exc_info:
                self.validator.validate_url(url)
            assert exc_info.value.error_code in ["INVALID_FORMAT", "UNSUPPORTED_PLATFORM"]
    
    def test_validate_url_unsupported_platform(self):
        """Test validation with unsupported platform raises ValidationError."""
        unsupported_urls = [
            "https://vimeo.com/123456789",
            "https://dailymotion.com/video/x123456",
            "https://twitch.tv/videos/123456789",
            "https://facebook.com/watch/?v=123456789"
        ]
        
        for url in unsupported_urls:
            with pytest.raises(ValidationError) as exc_info:
                self.validator.validate_url(url)
            assert exc_info.value.error_code == "UNSUPPORTED_PLATFORM"
            assert "Only YouTube and Bilibili are supported" in exc_info.value.message


class TestYouTubeValidation:
    """Test cases for YouTube URL validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = URLValidator()
    
    def test_validate_youtube_standard_url(self):
        """Test validation of standard YouTube URLs."""
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "http://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "http://youtube.com/watch?v=dQw4w9WgXcQ"
        ]
        
        for url in valid_urls:
            is_valid, platform, error = self.validator.validate_url(url)
            assert is_valid is True
            assert platform == SupportedPlatform.YOUTUBE
            assert error is None
    
    def test_validate_youtube_short_url(self):
        """Test validation of YouTube short URLs."""
        valid_urls = [
            "https://youtu.be/dQw4w9WgXcQ",
            "http://youtu.be/dQw4w9WgXcQ"
        ]
        
        for url in valid_urls:
            is_valid, platform, error = self.validator.validate_url(url)
            assert is_valid is True
            assert platform == SupportedPlatform.YOUTUBE
            assert error is None
    
    def test_validate_youtube_embed_url(self):
        """Test validation of YouTube embed URLs."""
        valid_urls = [
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "http://www.youtube.com/embed/dQw4w9WgXcQ"
        ]
        
        for url in valid_urls:
            is_valid, platform, error = self.validator.validate_url(url)
            assert is_valid is True
            assert platform == SupportedPlatform.YOUTUBE
            assert error is None
    
    def test_validate_youtube_mobile_url(self):
        """Test validation of YouTube mobile URLs."""
        valid_urls = [
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
            "http://m.youtube.com/watch?v=dQw4w9WgXcQ"
        ]
        
        for url in valid_urls:
            is_valid, platform, error = self.validator.validate_url(url)
            assert is_valid is True
            assert platform == SupportedPlatform.YOUTUBE
            assert error is None
    
    def test_validate_youtube_v_url(self):
        """Test validation of YouTube /v/ URLs."""
        valid_urls = [
            "https://www.youtube.com/v/dQw4w9WgXcQ",
            "http://www.youtube.com/v/dQw4w9WgXcQ"
        ]
        
        for url in valid_urls:
            is_valid, platform, error = self.validator.validate_url(url)
            assert is_valid is True
            assert platform == SupportedPlatform.YOUTUBE
            assert error is None
    
    def test_validate_youtube_invalid_video_id(self):
        """Test validation with invalid YouTube video IDs."""
        # URLs that are detected as YouTube but have invalid video IDs
        invalid_youtube_urls = [
            "https://www.youtube.com/watch?v=short",  # Too short
            "https://www.youtube.com/watch?v=toolongvideoid123",  # Too long
            "https://youtu.be/invalid@id"  # Invalid characters
        ]
        
        for url in invalid_youtube_urls:
            with pytest.raises(ValidationError) as exc_info:
                self.validator.validate_url(url)
            assert exc_info.value.error_code == "INVALID_YOUTUBE_URL"
        
        # URLs that don't match YouTube patterns at all
        unsupported_urls = [
            "https://www.youtube.com/watch?v=",  # Empty video ID - doesn't match pattern
        ]
        
        for url in unsupported_urls:
            with pytest.raises(ValidationError) as exc_info:
                self.validator.validate_url(url)
            assert exc_info.value.error_code == "UNSUPPORTED_PLATFORM"
    
    def test_extract_youtube_video_id(self):
        """Test extraction of YouTube video IDs."""
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ")
        ]
        
        for url, expected_id in test_cases:
            video_id = self.validator.extract_video_id(url, SupportedPlatform.YOUTUBE)
            assert video_id == expected_id


class TestBilibiliValidation:
    """Test cases for Bilibili URL validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = URLValidator()
    
    def test_validate_bilibili_bv_url(self):
        """Test validation of Bilibili BV URLs."""
        valid_urls = [
            "https://www.bilibili.com/video/BV1xx411c7mD",
            "http://www.bilibili.com/video/BV1xx411c7mD",
            "https://bilibili.com/video/BV1xx411c7mD"
        ]
        
        for url in valid_urls:
            is_valid, platform, error = self.validator.validate_url(url)
            assert is_valid is True
            assert platform == SupportedPlatform.BILIBILI
            assert error is None
    
    def test_validate_bilibili_av_url(self):
        """Test validation of Bilibili AV URLs."""
        valid_urls = [
            "https://www.bilibili.com/video/av123456",
            "http://www.bilibili.com/video/av123456",
            "https://bilibili.com/video/av123456"
        ]
        
        for url in valid_urls:
            is_valid, platform, error = self.validator.validate_url(url)
            assert is_valid is True
            assert platform == SupportedPlatform.BILIBILI
            assert error is None
    
    def test_validate_bilibili_mobile_url(self):
        """Test validation of Bilibili mobile URLs."""
        valid_urls = [
            "https://m.bilibili.com/video/BV1xx411c7mD",
            "http://m.bilibili.com/video/BV1xx411c7mD"
        ]
        
        for url in valid_urls:
            is_valid, platform, error = self.validator.validate_url(url)
            assert is_valid is True
            assert platform == SupportedPlatform.BILIBILI
            assert error is None
    
    def test_validate_bilibili_short_url(self):
        """Test validation of Bilibili short URLs."""
        valid_urls = [
            "https://b23.tv/abc123",
            "http://b23.tv/abc123"
        ]
        
        for url in valid_urls:
            is_valid, platform, error = self.validator.validate_url(url)
            assert is_valid is True
            assert platform == SupportedPlatform.BILIBILI
            assert error is None
    
    def test_extract_bilibili_video_id(self):
        """Test extraction of Bilibili video IDs."""
        test_cases = [
            ("https://www.bilibili.com/video/BV1xx411c7mD", "BV1xx411c7mD"),
            ("https://www.bilibili.com/video/av123456", "123456"),
            ("https://b23.tv/abc123", "abc123")
        ]
        
        for url, expected_id in test_cases:
            video_id = self.validator.extract_video_id(url, SupportedPlatform.BILIBILI)
            assert video_id == expected_id


class TestPlatformDetection:
    """Test cases for platform detection functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = URLValidator()
    
    def test_detect_youtube_platform(self):
        """Test detection of YouTube platform."""
        youtube_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        ]
        
        for url in youtube_urls:
            platform = self.validator.detect_platform(url)
            assert platform == SupportedPlatform.YOUTUBE
    
    def test_detect_bilibili_platform(self):
        """Test detection of Bilibili platform."""
        bilibili_urls = [
            "https://www.bilibili.com/video/BV1xx411c7mD",
            "https://www.bilibili.com/video/av123456",
            "https://b23.tv/abc123"
        ]
        
        for url in bilibili_urls:
            platform = self.validator.detect_platform(url)
            assert platform == SupportedPlatform.BILIBILI
    
    def test_detect_unsupported_platform(self):
        """Test detection returns None for unsupported platforms."""
        unsupported_urls = [
            "https://vimeo.com/123456789",
            "https://dailymotion.com/video/x123456",
            "https://example.com/video/123"
        ]
        
        for url in unsupported_urls:
            platform = self.validator.detect_platform(url)
            assert platform is None
    
    def test_detect_platform_empty_url(self):
        """Test detection with empty URL returns None."""
        assert self.validator.detect_platform("") is None
        assert self.validator.detect_platform(None) is None
    
    def test_is_supported_platform(self):
        """Test is_supported_platform method."""
        supported_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.bilibili.com/video/BV1xx411c7mD"
        ]
        
        unsupported_urls = [
            "https://vimeo.com/123456789",
            "https://example.com/video/123"
        ]
        
        for url in supported_urls:
            assert self.validator.is_supported_platform(url) is True
        
        for url in unsupported_urls:
            assert self.validator.is_supported_platform(url) is False
    
    def test_get_platform_name(self):
        """Test get_platform_name method."""
        assert self.validator.get_platform_name(SupportedPlatform.YOUTUBE) == "YouTube"
        assert self.validator.get_platform_name(SupportedPlatform.BILIBILI) == "Bilibili"


class TestConvenienceFunctions:
    """Test cases for convenience functions."""
    
    def test_validate_video_url_success(self):
        """Test validate_video_url convenience function with valid URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        is_valid, platform, error = validate_video_url(url)
        
        assert is_valid is True
        assert platform == SupportedPlatform.YOUTUBE
        assert error is None
    
    def test_validate_video_url_failure(self):
        """Test validate_video_url convenience function with invalid URL."""
        url = "https://vimeo.com/123456789"
        is_valid, platform, error = validate_video_url(url)
        
        assert is_valid is False
        assert platform is None
        assert error is not None
        assert "Only YouTube and Bilibili are supported" in error
    
    def test_detect_video_platform_success(self):
        """Test detect_video_platform convenience function."""
        youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        bilibili_url = "https://www.bilibili.com/video/BV1xx411c7mD"
        
        assert detect_video_platform(youtube_url) == SupportedPlatform.YOUTUBE
        assert detect_video_platform(bilibili_url) == SupportedPlatform.BILIBILI
    
    def test_detect_video_platform_failure(self):
        """Test detect_video_platform convenience function with unsupported URL."""
        unsupported_url = "https://vimeo.com/123456789"
        assert detect_video_platform(unsupported_url) is None


class TestGlobalValidator:
    """Test cases for the global validator instance."""
    
    def test_global_validator_instance(self):
        """Test that global validator instance is properly initialized."""
        assert url_validator is not None
        assert isinstance(url_validator, URLValidator)
        assert len(url_validator.youtube_compiled) > 0
        assert len(url_validator.bilibili_compiled) > 0
    
    def test_global_validator_functionality(self):
        """Test that global validator instance works correctly."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        is_valid, platform, error = url_validator.validate_url(url)
        
        assert is_valid is True
        assert platform == SupportedPlatform.YOUTUBE
        assert error is None


class TestEdgeCases:
    """Test cases for edge cases and special scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = URLValidator()
    
    def test_url_with_additional_parameters(self):
        """Test URLs with additional query parameters."""
        urls_with_params = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLrAXtmRdnEQy8VJqQzNYaYzOzZyYzOzYz",
            "https://www.bilibili.com/video/BV1xx411c7mD?p=1&t=30"
        ]
        
        for url in urls_with_params:
            platform = self.validator.detect_platform(url)
            assert platform is not None
    
    def test_case_insensitive_detection(self):
        """Test that platform detection is case insensitive."""
        mixed_case_urls = [
            "HTTPS://WWW.YOUTUBE.COM/WATCH?V=dQw4w9WgXcQ",
            "https://WWW.BILIBILI.COM/video/BV1xx411c7mD",
            "HTTPS://YOUTU.BE/dQw4w9WgXcQ"
        ]
        
        for url in mixed_case_urls:
            platform = self.validator.detect_platform(url)
            assert platform is not None
    
    def test_url_with_whitespace(self):
        """Test URLs with leading/trailing whitespace."""
        url_with_whitespace = "  https://www.youtube.com/watch?v=dQw4w9WgXcQ  "
        is_valid, platform, error = self.validator.validate_url(url_with_whitespace)
        
        assert is_valid is True
        assert platform == SupportedPlatform.YOUTUBE
        assert error is None


if __name__ == "__main__":
    pytest.main([__file__])