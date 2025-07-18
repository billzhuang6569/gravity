"""Celery application configuration for Gravity Video Downloader."""

import os
import multiprocessing
from celery import Celery
from celery.schedules import crontab
from celery import signals

from app.config import settings

# Create Celery application
celery_app = Celery(
    "gravity_downloader",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.download_tasks", "app.tasks.cleanup_tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Task routing and execution
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Worker configuration - Dynamic concurrency based on CPU cores
    worker_concurrency=settings.celery_worker_concurrency or (multiprocessing.cpu_count() * 2),
    worker_prefetch_multiplier=1,  # Prevent worker from prefetching too many tasks
    task_acks_late=True,  # Acknowledge tasks only after completion
    worker_disable_rate_limits=False,
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks to prevent memory leaks
    worker_max_memory_per_child=200000,  # 200MB memory limit per child
    
    # Task timeout and retry configuration
    task_soft_time_limit=settings.celery_task_soft_time_limit,  # 30 minutes
    task_time_limit=settings.celery_task_time_limit,  # 31 minutes (hard limit)
    task_default_retry_delay=settings.celery_default_retry_delay,  # 1 minute
    task_max_retries=settings.celery_max_retries,  # 3 retries
    task_reject_on_worker_lost=True,  # Reject tasks if worker is lost
    
    # Result backend configuration
    result_expires=3600 * 24 * 7,  # 7 days
    result_backend_transport_options={
        "visibility_timeout": 3600,
        "retry_on_timeout": True,
        "health_check_interval": 30,
        "max_connections": 20,  # Maximum number of connections in the pool
        "socket_timeout": 5,     # Socket timeout in seconds
        "socket_connect_timeout": 5,  # Socket connection timeout
    },
    
    # Redis broker configuration with enhanced reliability
    broker_transport_options={
        "visibility_timeout": 3600,
        "fanout_prefix": True,
        "fanout_patterns": True,
        "retry_on_timeout": True,
        "health_check_interval": 30,
        "socket_keepalive": True,
        "max_connections": 20,  # Maximum number of connections in the pool
        "socket_timeout": 5,     # Socket timeout in seconds
        "socket_connect_timeout": 5,  # Socket connection timeout
    },
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    broker_pool_limit=10,  # Maximum number of connections in the broker pool
    
    # Task routing with priority queues
    task_routes={
        "app.tasks.download_tasks.*": {"queue": "downloads"},
        "app.tasks.cleanup_tasks.*": {"queue": "maintenance"},
        "app.tasks.download_tasks.health_check_task": {"queue": "health"},
    },
    
    # Queue configuration
    task_default_queue="downloads",
    task_create_missing_queues=True,
    task_queue_max_priority=10,  # Enable priority support in queues
    task_default_priority=5,     # Default task priority
    
    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-old-files": {
            "task": "app.tasks.cleanup_tasks.cleanup_old_files",
            "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
            "options": {"queue": "maintenance"},
        },
        "cleanup-old-tasks": {
            "task": "app.tasks.cleanup_tasks.cleanup_old_tasks",
            "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
            "options": {"queue": "maintenance"},
        },
        "system-health-check": {
            "task": "app.tasks.cleanup_tasks.system_health_check",
            "schedule": crontab(minute="*/15"),  # Every 15 minutes
            "options": {"queue": "health"},
        },
        "optimize-redis-memory": {
            "task": "app.tasks.cleanup_tasks.optimize_redis_memory",
            "schedule": crontab(hour=4, minute=0),  # Daily at 4 AM
            "options": {"queue": "maintenance"},
        },
    },
    beat_schedule_filename="celerybeat-schedule",
    beat_max_loop_interval=300,  # Maximum interval between beat scheduler runs (5 minutes)
    
    # Monitoring and logging
    worker_send_task_events=True,
    task_send_sent_event=True,
    worker_hijack_root_logger=False,
    worker_log_color=False,
    
    # Task execution optimization
    task_compression='gzip',  # Compress task messages
    result_compression='gzip',  # Compress task results
    
    # Security settings
    security_key=settings.celery_security_key,  # Optional security key for message signing
    
    # Task track started
    task_track_started=True,  # Track when tasks are started
)

# Task autodiscovery
celery_app.autodiscover_tasks(["app.tasks"])


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery functionality."""
    print(f"Request: {self.request!r}")
    return "Debug task completed"


# Worker event handlers
@signals.worker_init.connect
def worker_init_handler(sender=None, conf=None, **kwargs):
    """Handle worker initialization."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Worker {sender} initialized with concurrency: {conf.worker_concurrency}")


@signals.worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handle worker ready state."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Worker {sender} is ready to process tasks")


@signals.worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Handle worker shutdown."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Worker {sender} is shutting down")


@signals.task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task pre-execution."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Task {task.name}[{task_id}] starting")


@signals.task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Handle task post-execution."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Task {task.name}[{task_id}] completed with state: {state}")


@signals.task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwargs):
    """Handle task failures."""
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Task {sender.name}[{task_id}] failed: {exception}")
    logger.error(f"Traceback: {traceback}")


@signals.task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **kwargs):
    """Handle task retries."""
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Task {sender.name}[{task_id}] retrying: {reason}")


@signals.worker_process_init.connect
def worker_process_init_handler(sender=None, **kwargs):
    """Handle worker process initialization."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Worker process {os.getpid()} initialized")


@signals.heartbeat_sent.connect
def heartbeat_sent_handler(sender=None, **kwargs):
    """Handle worker heartbeat events."""
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"Heartbeat sent from worker {sender}")


@signals.worker_process_shutdown.connect
def worker_process_shutdown_handler(sender=None, pid=None, exitcode=None, **kwargs):
    """Handle worker process shutdown."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Worker process {pid} shutting down with exit code {exitcode}")


def get_celery_worker_status():
    """Get current Celery worker status and statistics."""
    try:
        inspect = celery_app.control.inspect()
        
        # Get active tasks
        active_tasks = inspect.active()
        
        # Get registered tasks
        registered_tasks = inspect.registered()
        
        # Get worker statistics
        stats = inspect.stats()
        
        return {
            'active_tasks': active_tasks,
            'registered_tasks': registered_tasks,
            'stats': stats,
            'status': 'healthy' if active_tasks is not None else 'unhealthy'
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }