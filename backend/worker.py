#!/usr/bin/env python3
"""Celery worker startup script with proper initialization and shutdown handling."""

import os
import sys
import signal
import logging
import multiprocessing
import psutil
import time
from pathlib import Path

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.celery_app import celery_app
from app.config import settings

# Configure logging
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logs_path = "/opt/gravity/logs" if os.path.exists("/opt/gravity") else os.path.join(os.getcwd(), "logs")
log_file = os.path.join(logs_path, "worker.log")

# Ensure logs directory exists
Path(logs_path).mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger(__name__)


def ensure_directories():
    """Ensure required directories exist."""
    directories = [
        settings.downloads_path,
        settings.temp_path,
        logs_path,
        os.path.join(logs_path, "celery")
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")


def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        signal_name = {
            signal.SIGTERM: "SIGTERM",
            signal.SIGINT: "SIGINT",
            signal.SIGHUP: "SIGHUP"
        }.get(signum, f"Signal {signum}")
        
        logger.info(f"Received {signal_name}, initiating graceful shutdown...")
        
        # Give tasks time to complete or terminate
        logger.info("Waiting for running tasks to complete (max 30 seconds)...")
        time.sleep(30)
        
        # Celery will handle the graceful shutdown
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)


def get_worker_concurrency():
    """Calculate optimal worker concurrency based on CPU cores and system resources."""
    cpu_count = multiprocessing.cpu_count()
    
    # Default to CPU count * 2 as per requirement
    concurrency = cpu_count * 2
    
    # Check available memory
    mem = psutil.virtual_memory()
    available_mem_gb = mem.available / (1024 * 1024 * 1024)
    
    # Estimate memory per worker (conservative estimate: 200MB per worker)
    mem_per_worker_gb = 0.2
    
    # Calculate max workers based on available memory (leaving 20% for system)
    mem_based_concurrency = int(available_mem_gb * 0.8 / mem_per_worker_gb)
    
    # Take the minimum of CPU-based and memory-based concurrency
    concurrency = min(concurrency, mem_based_concurrency)
    
    # Respect max concurrent downloads setting
    if concurrency > settings.max_concurrent_downloads:
        concurrency = settings.max_concurrent_downloads
    
    # Ensure at least 2 workers
    concurrency = max(concurrency, 2)
    
    logger.info(f"System resources: {cpu_count} CPU cores, {available_mem_gb:.2f}GB available memory")
    logger.info(f"Calculated worker concurrency: {concurrency}")
    
    return concurrency


def check_redis_connection():
    """Check Redis connection before starting workers."""
    import redis
    try:
        client = redis.Redis.from_url(settings.redis_url)
        if client.ping():
            logger.info("Redis connection check: SUCCESS")
            return True
        else:
            logger.error("Redis connection check: FAILED - Ping returned False")
            return False
    except Exception as e:
        logger.error(f"Redis connection check: FAILED - {str(e)}")
        return False


def main():
    """Main worker startup function."""
    logger.info("Starting Gravity Video Downloader Celery Worker")
    logger.info(f"Worker process ID: {os.getpid()}")
    
    try:
        # Ensure required directories exist
        ensure_directories()
        
        # Set up signal handlers
        setup_signal_handlers()
        
        # Check Redis connection
        if not check_redis_connection():
            logger.error("Cannot connect to Redis. Worker startup aborted.")
            sys.exit(1)
        
        # Calculate worker concurrency
        concurrency = get_worker_concurrency()
        
        # Start the worker
        logger.info(f"Starting Celery worker with concurrency: {concurrency}")
        
        # Prepare worker arguments
        worker_args = [
            'worker',
            '--loglevel=info',
            f'--concurrency={concurrency}',
            '--queues=downloads,maintenance,health',
            '--hostname=gravity-worker@%h',
            f'--time-limit={settings.celery_task_time_limit}',
            f'--soft-time-limit={settings.celery_task_soft_time_limit}',
            '--max-tasks-per-child=50',
            '--max-memory-per-child=200000',  # 200MB memory limit per child
            '--optimization=fair',
            '--pool=prefork',
            '--autoscale=10,3',  # Auto-scale between 3-10 workers based on load
            '--logfile=' + os.path.join(logs_path, "celery", "worker-%I.log"),
            '--pidfile=' + os.path.join(logs_path, "celery", "worker.pid"),
        ]
        
        # Log the command being executed
        logger.info(f"Executing: celery {' '.join(worker_args)}")
        
        # Start the worker
        celery_app.worker_main(worker_args)
        
    except KeyboardInterrupt:
        logger.info("Worker shutdown requested by user")
    except Exception as e:
        logger.error(f"Worker startup failed: {e}")
        sys.exit(1)
    finally:
        logger.info("Celery worker shutdown completed")


if __name__ == "__main__":
    main()