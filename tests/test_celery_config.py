#!/usr/bin/env python3
"""Test script to verify Celery configuration and worker setup."""

import os
import sys
import time
import logging
import multiprocessing
from pathlib import Path

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.celery_app import celery_app, get_celery_worker_status
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_celery_configuration():
    """Test Celery configuration settings."""
    logger.info("Testing Celery configuration...")
    
    # Test basic configuration
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.enable_utc is True
    
    # Test worker configuration
    expected_concurrency = settings.celery_worker_concurrency or (multiprocessing.cpu_count() * 2)
    assert celery_app.conf.worker_concurrency == expected_concurrency
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.worker_max_tasks_per_child == 50
    assert celery_app.conf.worker_max_memory_per_child == 200000
    
    # Test timeout configuration
    assert celery_app.conf.task_soft_time_limit == settings.celery_task_soft_time_limit
    assert celery_app.conf.task_time_limit == settings.celery_task_time_limit
    assert celery_app.conf.task_default_retry_delay == settings.celery_default_retry_delay
    assert celery_app.conf.task_max_retries == settings.celery_max_retries
    
    # Test task routing
    expected_routes = {
        "app.tasks.download_tasks.*": {"queue": "downloads"},
        "app.tasks.cleanup_tasks.*": {"queue": "maintenance"},
        "app.tasks.download_tasks.health_check_task": {"queue": "health"},
    }
    assert celery_app.conf.task_routes == expected_routes
    
    # Test beat schedule
    beat_schedule = celery_app.conf.beat_schedule
    assert "cleanup-old-files" in beat_schedule
    assert "cleanup-old-tasks" in beat_schedule
    assert "system-health-check" in beat_schedule
    assert "optimize-redis-memory" in beat_schedule
    
    # Test new configurations
    assert celery_app.conf.task_track_started is True
    assert celery_app.conf.task_compression == 'gzip'
    assert celery_app.conf.result_compression == 'gzip'
    assert celery_app.conf.broker_pool_limit == 10
    assert celery_app.conf.task_queue_max_priority == 10
    assert celery_app.conf.task_default_priority == 5
    assert celery_app.conf.beat_max_loop_interval == 300
    
    # Test security key
    assert celery_app.conf.security_key == settings.celery_security_key
    
    # Test broker and result backend transport options
    broker_options = celery_app.conf.broker_transport_options
    assert broker_options.get('max_connections') == 20
    assert broker_options.get('socket_timeout') == 5
    assert broker_options.get('socket_connect_timeout') == 5
    
    result_options = celery_app.conf.result_backend_transport_options
    assert result_options.get('max_connections') == 20
    assert result_options.get('socket_timeout') == 5
    assert result_options.get('socket_connect_timeout') == 5
    
    logger.info("✅ Celery configuration test passed")


def test_redis_connection():
    """Test Redis broker and result backend connection."""
    logger.info("Testing Redis connection...")
    
    try:
        # Test broker connection configuration (without actually connecting)
        broker_url = celery_app.conf.broker_url
        result_backend = celery_app.conf.result_backend
        
        assert broker_url == settings.celery_broker_url
        assert result_backend == settings.celery_result_backend
        
        # Test actual Redis connection if possible
        try:
            import redis
            client = redis.Redis.from_url(settings.redis_url)
            ping_result = client.ping()
            if ping_result:
                logger.info("✅ Redis connection test successful")
            else:
                logger.warning("⚠️ Redis ping returned False")
        except ImportError:
            logger.warning("⚠️ Redis package not available, skipping connection test")
        except Exception as e:
            logger.warning(f"⚠️ Redis connection test failed: {e}")
        
        logger.info("✅ Redis configuration test passed")
        logger.info(f"Broker URL: {broker_url}")
        logger.info(f"Result Backend: {result_backend}")
        
    except Exception as e:
        logger.error(f"❌ Redis configuration test failed: {e}")
        return False
    
    return True


def test_task_registration():
    """Test that tasks are properly registered."""
    logger.info("Testing task registration...")
    
    try:
        # Force task discovery
        celery_app.autodiscover_tasks(["app.tasks"])
        
        # Get registered tasks
        registered_tasks = list(celery_app.tasks.keys())
        logger.info(f"Found {len(registered_tasks)} registered tasks")
        
        # Expected tasks
        expected_tasks = [
            "app.tasks.download_tasks.download_video_task",
            "app.tasks.download_tasks.get_video_info_task", 
            "app.tasks.download_tasks.health_check_task",
            "app.tasks.cleanup_tasks.cleanup_old_files",
            "app.tasks.cleanup_tasks.cleanup_old_tasks",
            "app.tasks.cleanup_tasks.system_health_check",
            "app.tasks.cleanup_tasks.optimize_redis_memory",
        ]
        
        found_tasks = 0
        for task_name in expected_tasks:
            if task_name in registered_tasks:
                logger.info(f"✅ Task registered: {task_name}")
                found_tasks += 1
            else:
                logger.warning(f"⚠️ Task not registered: {task_name}")
        
        # Check if we have the core debug task at least
        if "app.celery_app.debug_task" in registered_tasks:
            logger.info("✅ Debug task registered")
            found_tasks += 1
        
        if found_tasks > 0:
            logger.info(f"✅ Task registration test passed ({found_tasks} tasks found)")
            return True
        else:
            logger.error("❌ No expected tasks found")
            return False
            
    except Exception as e:
        logger.error(f"❌ Task registration test failed: {e}")
        return False


def test_debug_task():
    """Test debug task configuration."""
    logger.info("Testing debug task configuration...")
    
    try:
        # Check if debug task is available
        debug_task = celery_app.tasks.get('app.celery_app.debug_task')
        
        if debug_task:
            logger.info("✅ Debug task configuration test passed")
            return True
        else:
            logger.warning("⚠️ Debug task not found, but this is not critical")
            return True
            
    except Exception as e:
        logger.error(f"❌ Debug task configuration test failed: {e}")
        return False


def test_worker_status():
    """Test worker status monitoring function."""
    logger.info("Testing worker status monitoring function...")
    
    try:
        # Test that the function exists and can be called
        # (without requiring actual workers to be running)
        status = get_celery_worker_status()
        
        # Should return a dict with status key
        if isinstance(status, dict) and 'status' in status:
            logger.info(f"✅ Worker status function test passed: {status['status']}")
            return True
        else:
            logger.error(f"❌ Worker status function returned invalid format: {status}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Worker status function test failed: {e}")
        return False


def test_beat_schedule():
    """Test beat schedule configuration."""
    logger.info("Testing beat schedule configuration...")
    
    try:
        beat_schedule = celery_app.conf.beat_schedule
        
        # Test each scheduled task
        for task_name, config in beat_schedule.items():
            assert "task" in config
            assert "schedule" in config
            logger.info(f"✅ Beat task configured: {task_name}")
        
        # Test beat scheduler settings
        assert celery_app.conf.beat_max_loop_interval == 300
        assert celery_app.conf.beat_schedule_filename == "celerybeat-schedule"
        
        logger.info("✅ Beat schedule test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Beat schedule test failed: {e}")
        return False


def test_worker_startup_script():
    """Test worker startup script."""
    logger.info("Testing worker startup script...")
    
    try:
        # Check if worker.py exists
        worker_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "worker.py")
        assert os.path.exists(worker_path), "worker.py not found"
        
        # Check if it's executable
        assert os.access(worker_path, os.X_OK), "worker.py is not executable"
        
        logger.info("✅ Worker startup script test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Worker startup script test failed: {e}")
        return False


def test_beat_startup_script():
    """Test beat startup script."""
    logger.info("Testing beat startup script...")
    
    try:
        # Check if beat.py exists
        beat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "beat.py")
        assert os.path.exists(beat_path), "beat.py not found"
        
        # Check if it's executable
        assert os.access(beat_path, os.X_OK), "beat.py is not executable"
        
        logger.info("✅ Beat startup script test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Beat startup script test failed: {e}")
        return False


def test_directory_structure():
    """Test directory structure for Celery operation."""
    logger.info("Testing directory structure...")
    
    try:
        # Check if required directories exist or can be created
        directories = [
            settings.downloads_path,
            settings.temp_path,
            os.path.join(os.getcwd(), "logs"),
            os.path.join(os.getcwd(), "beat")
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            assert os.path.exists(directory), f"Directory {directory} could not be created"
            logger.info(f"✅ Directory exists or created: {directory}")
        
        logger.info("✅ Directory structure test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Directory structure test failed: {e}")
        return False


def main():
    """Run all Celery configuration tests."""
    logger.info("Starting Celery configuration tests...")
    
    tests = [
        ("Configuration", test_celery_configuration),
        ("Redis Connection", test_redis_connection),
        ("Task Registration", test_task_registration),
        ("Beat Schedule", test_beat_schedule),
        ("Worker Status", test_worker_status),
        ("Worker Startup Script", test_worker_startup_script),
        ("Beat Startup Script", test_beat_startup_script),
        ("Directory Structure", test_directory_structure),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} Test ---")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"❌ {test_name} test failed with exception: {e}")
            failed += 1
    
    # Summary
    logger.info(f"\n--- Test Summary ---")
    logger.info(f"✅ Passed: {passed}")
    logger.info(f"❌ Failed: {failed}")
    logger.info(f"Total: {passed + failed}")
    
    if failed == 0:
        logger.info("🎉 All Celery configuration tests passed!")
        return True
    else:
        logger.error("💥 Some Celery configuration tests failed!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)