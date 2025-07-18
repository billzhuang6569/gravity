"""
URL validation and platform detection service for video downloads.

This module provides functionality to validate video URLs and detect
supported platforms (Bilibili, YouTube) with comprehensive error handling.
"""

import re
from enum import Enum
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs


class SupportedPlatform(str, Enum):
    """Enumeration of supported video platforms."""
    YOUTUBE = "youtube"
    BILIBILI = "bilibili"


class ValidationError(Exception):
    """Custom exception for URL validation errors."""
    
    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class URLValidator:
    """Service class for URL validation and platform detection."""
    
    # YouTube URL patterns - updated to be more flexible for detection but strict for validation
    YOUTUBE_PATTERNS = [
        r'^https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'^https?://(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
        r'^https?://youtu\.be/([a-zA-Z0-9_-]+)',
        r'^https?://(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]+)',
        r'^https?://(?:m\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
    ]
    
    # Bilibili URL patterns
    BILIBILI_PATTERNS = [
        r'^https?://(?:www\.)?bilibili\.com/video/([a-zA-Z0-9]+)',
        r'^https?://(?:www\.)?bilibili\.com/video/(av\d+)',
        r'^https?://(?:www\.)?bilibili\.com/video/(BV[a-zA-Z0-9]+)',
        r'^https?://(?:m\.)?bilibili\.com/video/([a-zA-Z0-9]+)',
        r'^https?://(?:b23\.tv)/([a-zA-Z0-9]+)',
    ]
    
    def __init__(self):
        """Initialize the URL validator."""
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for better performance."""
        self.youtube_compiled = [re.compile(pattern, re.IGNORECASE) for pattern in self.YOUTUBE_PATTERNS]
        self.bilibili_compiled = [re.compile(pattern, re.IGNORECASE) for pattern in self.BILIBILI_PATTERNS]
    
    def validate_url(self, url: str) -> Tuple[bool, Optional[SupportedPlatform], Optional[str]]:
        """
        Validate a video URL and detect its platform.
        
        Args:
            url: The URL to validate
            
        Returns:
            Tuple of (is_valid, platform, error_message)
            
        Raises:
            ValidationError: If URL validation fails with specific error details
        """
        if not url or not url.strip():
            raise ValidationError("URL cannot be empty", "EMPTY_URL")
        
        url = url.strip()
        
        # Basic URL format validation
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValidationError("Invalid URL format", "INVALID_FORMAT")
        except Exception:
            raise ValidationError("Invalid URL format", "INVALID_FORMAT")
        
        # Check for supported platforms
        platform = self.detect_platform(url)
        if platform is None:
            raise ValidationError(
                "Unsupported platform. Only YouTube and Bilibili are supported.",
                "UNSUPPORTED_PLATFORM"
            )
        
        # Platform-specific validation
        if platform == SupportedPlatform.YOUTUBE:
            if not self._validate_youtube_url(url):
                raise ValidationError("Invalid YouTube URL format", "INVALID_YOUTUBE_URL")
        elif platform == SupportedPlatform.BILIBILI:
            if not self._validate_bilibili_url(url):
                raise ValidationError("Invalid Bilibili URL format", "INVALID_BILIBILI_URL")
        
        return True, platform, None
    
    def detect_platform(self, url: str) -> Optional[SupportedPlatform]:
        """
        Detect the platform of a given URL.
        
        Args:
            url: The URL to analyze
            
        Returns:
            SupportedPlatform enum value or None if unsupported
        """
        if not url:
            return None
        
        url = url.strip().lower()
        
        # Check YouTube patterns
        for pattern in self.youtube_compiled:
            if pattern.search(url):
                return SupportedPlatform.YOUTUBE
        
        # Check Bilibili patterns
        for pattern in self.bilibili_compiled:
            if pattern.search(url):
                return SupportedPlatform.BILIBILI
        
        return None
    
    def _validate_youtube_url(self, url: str) -> bool:
        """
        Validate YouTube-specific URL format.
        
        Args:
            url: YouTube URL to validate
            
        Returns:
            True if valid YouTube URL, False otherwise
        """
        for pattern in self.youtube_compiled:
            match = pattern.search(url)
            if match:
                video_id = match.group(1)
                # YouTube video IDs are exactly 11 characters and contain only valid characters
                if len(video_id) == 11 and re.match(r'^[a-zA-Z0-9_-]+$', video_id):
                    return True
        return False
    
    def _validate_bilibili_url(self, url: str) -> bool:
        """
        Validate Bilibili-specific URL format.
        
        Args:
            url: Bilibili URL to validate
            
        Returns:
            True if valid Bilibili URL, False otherwise
        """
        for pattern in self.bilibili_compiled:
            match = pattern.search(url)
            if match:
                # Basic validation - if pattern matches, consider valid
                # More specific validation can be added here if needed
                return True
        return False
    
    def extract_video_id(self, url: str, platform: SupportedPlatform) -> Optional[str]:
        """
        Extract video ID from a validated URL.
        
        Args:
            url: The validated video URL
            platform: The detected platform
            
        Returns:
            Video ID string or None if extraction fails
        """
        if platform == SupportedPlatform.YOUTUBE:
            for pattern in self.youtube_compiled:
                match = pattern.search(url)
                if match:
                    return match.group(1)
        
        elif platform == SupportedPlatform.BILIBILI:
            for pattern in self.bilibili_compiled:
                match = pattern.search(url)
                if match:
                    video_id = match.group(1)
                    # For av URLs, extract just the numeric part
                    if video_id.startswith('av'):
                        return video_id[2:]  # Remove 'av' prefix
                    return video_id
        
        return None
    
    def is_supported_platform(self, url: str) -> bool:
        """
        Quick check if URL is from a supported platform.
        
        Args:
            url: URL to check
            
        Returns:
            True if platform is supported, False otherwise
        """
        return self.detect_platform(url) is not None
    
    def get_platform_name(self, platform: SupportedPlatform) -> str:
        """
        Get human-readable platform name.
        
        Args:
            platform: Platform enum value
            
        Returns:
            Human-readable platform name
        """
        platform_names = {
            SupportedPlatform.YOUTUBE: "YouTube",
            SupportedPlatform.BILIBILI: "Bilibili"
        }
        return platform_names.get(platform, "Unknown")


# Global validator instance
url_validator = URLValidator()


def validate_video_url(url: str) -> Tuple[bool, Optional[SupportedPlatform], Optional[str]]:
    """
    Convenience function for URL validation.
    
    Args:
        url: URL to validate
        
    Returns:
        Tuple of (is_valid, platform, error_message)
    """
    try:
        return url_validator.validate_url(url)
    except ValidationError as e:
        return False, None, e.message


def detect_video_platform(url: str) -> Optional[SupportedPlatform]:
    """
    Convenience function for platform detection.
    
    Args:
        url: URL to analyze
        
    Returns:
        SupportedPlatform enum value or None
    """
    return url_validator.detect_platform(url)