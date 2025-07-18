#!/usr/bin/env python3
"""Simple Celery worker for testing."""

import os
import sys
from celery import Celery

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Create simple Celery app with minimal configuration
app = Celery('gravity_test')

# Very simple configuration for testing
app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    include=['app.tasks.download_tasks'],
    # Simplified broker transport options
    broker_transport_options={},
    # Disable prefetch to avoid memory issues
    worker_prefetch_multiplier=1,
    # Simple task routing
    task_routes={}
)

if __name__ == '__main__':
    app.start()