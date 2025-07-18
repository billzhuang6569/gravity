#!/usr/bin/env python3
"""Simple test script to verify API functionality."""

import requests
import json
import time

# Test configuration
API_BASE_URL = "http://localhost:8001/api/v1"

def test_health_check():
    """Test the health check endpoint."""
    try:
        print("Testing health check endpoint...")
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_video_info():
    """Test the video info endpoint."""
    try:
        print("\nTesting video info endpoint...")
        data = {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
        response = requests.post(
            f"{API_BASE_URL}/downloads/info", 
            json=data, 
            timeout=10
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Video info test failed: {e}")
        return False

def test_download_submission():
    """Test the download submission endpoint."""
    try:
        print("\nTesting download submission...")
        data = {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "quality": "best",
            "format": "video"
        }
        response = requests.post(
            f"{API_BASE_URL}/downloads", 
            json=data, 
            timeout=10
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Download submission test failed: {e}")
        return False

if __name__ == "__main__":
    print("🌌 Gravity Video Downloader API Test")
    print("=" * 50)
    
    # Run tests
    health_ok = test_health_check()
    video_info_ok = test_video_info()
    download_ok = test_download_submission()
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"Health Check: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"Video Info: {'✅ PASS' if video_info_ok else '❌ FAIL'}")
    print(f"Download Submission: {'✅ PASS' if download_ok else '❌ FAIL'}")
    
    if health_ok and video_info_ok and download_ok:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed")