#!/usr/bin/env python3
"""Celery Beat scheduler startup script for periodic tasks."""

import os
import sys
import signal
import logging
import time
from pathlib import Path

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.celery_app import celery_app
from app.config import settings

# Configure logging
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logs_path = "/opt/gravity/logs" if os.path.exists("/opt/gravity") else os.path.join(os.getcwd(), "logs")
beat_path = "/opt/gravity/beat" if os.path.exists("/opt/gravity") else os.path.join(os.getcwd(), "beat")
log_file = os.path.join(logs_path, "beat.log")

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
        logs_path,
        beat_path,  # Directory for beat schedule file
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
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)


def check_redis_connection():
    """Check Redis connection before starting beat scheduler."""
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


def cleanup_stale_files():
    """Clean up stale PID and schedule files."""
    pid_file = os.path.join(beat_path, "celerybeat.pid")
    schedule_file = os.path.join(beat_path, "celerybeat-schedule")
    
    # Remove stale PID file if exists
    if os.path.exists(pid_file):
        try:
            os.remove(pid_file)
            logger.info(f"Removed stale PID file: {pid_file}")
        except Exception as e:
            logger.warning(f"Could not remove PID file {pid_file}: {e}")
    
    # Check if schedule file is corrupted (0 bytes or very small)
    if os.path.exists(schedule_file):
        try:
            file_size = os.path.getsize(schedule_file)
            if file_size < 10:  # Likely corrupted
                os.remove(schedule_file)
                logger.info(f"Removed potentially corrupted schedule file: {schedule_file} (size: {file_size} bytes)")
        except Exception as e:
            logger.warning(f"Error checking schedule file {schedule_file}: {e}")


def main():
    """Main beat scheduler startup function."""
    logger.info("Starting Gravity Video Downloader Celery Beat Scheduler")
    logger.info(f"Beat scheduler process ID: {os.getpid()}")
    
    try:
        # Ensure required directories exist
        ensure_directories()
        
        # Set up signal handlers
        setup_signal_handlers()
        
        # Check Redis connection
        if not check_redis_connection():
            logger.error("Cannot connect to Redis. Beat scheduler startup aborted.")
            sys.exit(1)
        
        # Clean up stale files
        cleanup_stale_files()
        
        # Start the beat scheduler
        logger.info("Starting Celery Beat scheduler")
        
        # Prepare beat scheduler paths
        schedule_file = os.path.join(beat_path, "celerybeat-schedule")
        pid_file = os.path.join(beat_path, "celerybeat.pid")
        log_file = os.path.join(logs_path, "celery", "beat.log")
        
        # Prepare beat arguments
        beat_args = [
            'beat',
            '--loglevel=info',
            f'--schedule={schedule_file}',
            f'--pidfile={pid_file}',
            f'--logfile={log_file}',
            '--max-interval=300',  # Maximum sleep interval between checks (5 minutes)
            '--scheduler=celery.beat.PersistentScheduler',  # Use persistent scheduler
        ]
        
        # Log the command being executed
        logger.info(f"Executing: celery {' '.join(beat_args)}")
        
        # Start the beat scheduler
        celery_app.start(beat_args)
        
    except KeyboardInterrupt:
        logger.info("Beat scheduler shutdown requested by user")
    except Exception as e:
        logger.error(f"Beat scheduler startup failed: {e}")
        sys.exit(1)
    finally:
        logger.info("Celery Beat scheduler shutdown completed")


if __name__ == "__main__":
    main()