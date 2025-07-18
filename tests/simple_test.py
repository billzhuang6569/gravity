#!/usr/bin/env python3
"""Simple test without health check dependencies."""

import requests
import json

def test_simple():
    """Test a simple endpoint."""
    try:
        # Test root endpoint
        response = requests.get("http://localhost:8001/", timeout=5)
        print(f"Root endpoint: Status {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
        # Test docs endpoint
        response = requests.get("http://localhost:8001/docs", timeout=5)
        print(f"Docs endpoint: Status {response.status_code}")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_simple()