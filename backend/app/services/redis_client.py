"""Redis client configuration and connection management."""

import asyncio
import logging
from typing import Optional, Any, Dict, List
from contextlib import asynccontextmanager
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from app.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client with connection pooling and error handling."""
    
    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._is_connected = False
    
    async def connect(self) -> None:
        """Initialize Redis connection pool."""
        try:
            # Create connection pool with appropriate settings
            self._pool = ConnectionPool.from_url(
                settings.redis_url,
                max_connections=20,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                health_check_interval=30
            )
            
            # Create Redis client
            self._client = redis.Redis(
                connection_pool=self._pool,
                decode_responses=True
            )
            
            # Test connection
            if not await self.health_check():
                raise ConnectionError("Failed to establish Redis connection")
            self._is_connected = True
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._is_connected = False
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection and cleanup resources."""
        try:
            if self._client:
                await self._client.aclose()
            if self._pool:
                await self._pool.aclose()
            self._is_connected = False
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
    
    async def health_check(self) -> bool:
        """Check Redis connectivity and return health status."""
        try:
            if not self._client:
                return False
            
            # Simple ping test
            response = await self._client.ping()
            if response:
                logger.debug("Redis health check passed")
                return True
            else:
                logger.warning("Redis ping returned False")
                return False
                
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._is_connected
    
    @asynccontextmanager
    async def get_client(self):
        """Context manager to get Redis client with error handling."""
        if not self._client or not self._is_connected:
            raise ConnectionError("Redis client not connected")
        
        try:
            yield self._client
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis operation failed: {e}")
            self._is_connected = False
            raise
        except RedisError as e:
            logger.error(f"Redis error: {e}")
            raise
    
    async def execute_with_retry(self, operation, *args, **kwargs):
        """Execute Redis operation with retry logic and graceful degradation."""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                async with self.get_client() as client:
                    return await operation(client, *args, **kwargs)
            except (ConnectionError, TimeoutError) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Redis operation failed after {max_retries} attempts: {e}")
                    raise
                
                logger.warning(f"Redis operation failed (attempt {attempt + 1}), retrying in {retry_delay}s: {e}")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                
                # Try to reconnect
                try:
                    await self.connect()
                except Exception:
                    pass  # Continue with retry
            except RedisError as e:
                logger.error(f"Redis operation error: {e}")
                raise


# Global Redis client instance
redis_client = RedisClient()


async def get_redis_client() -> RedisClient:
    """Dependency to get Redis client."""
    if not redis_client.is_connected:
        await redis_client.connect()
    return redis_client


def get_redis_client_sync() -> RedisClient:
    """Synchronous version to get Redis client."""
    return redis_client


async def init_redis() -> None:
    """Initialize Redis connection on startup."""
    try:
        await redis_client.connect()
        logger.info("Redis initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        raise


async def close_redis() -> None:
    """Close Redis connection on shutdown."""
    try:
        await redis_client.disconnect()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.error(f"Error closing Redis: {e}")