"""Tests for Redis client connection and configuration."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from redis.exceptions import ConnectionError, TimeoutError

from app.services.redis_client import RedisClient, get_redis_client, init_redis, close_redis


@pytest.fixture
def redis_client():
    """Create a Redis client for testing."""
    return RedisClient()


@pytest.mark.asyncio
async def test_redis_client_connect_success(redis_client):
    """Test successful Redis connection."""
    with patch('redis.asyncio.Redis') as mock_redis:
        mock_instance = AsyncMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        
        with patch('redis.asyncio.connection.ConnectionPool.from_url') as mock_pool:
            mock_pool.return_value = AsyncMock()
            
            await redis_client.connect()
            
            assert redis_client.is_connected is True
            mock_instance.ping.assert_called_once()


@pytest.mark.asyncio
async def test_redis_client_connect_failure(redis_client):
    """Test Redis connection failure."""
    with patch('redis.asyncio.Redis') as mock_redis:
        mock_instance = AsyncMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.side_effect = ConnectionError("Connection failed")
        
        with patch('redis.asyncio.connection.ConnectionPool.from_url') as mock_pool:
            mock_pool.return_value = AsyncMock()
            
            with pytest.raises(ConnectionError):
                await redis_client.connect()
            
            assert redis_client.is_connected is False


@pytest.mark.asyncio
async def test_redis_health_check_success(redis_client):
    """Test successful health check."""
    with patch('redis.asyncio.Redis') as mock_redis:
        mock_instance = AsyncMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        
        with patch('redis.asyncio.connection.ConnectionPool.from_url'):
            await redis_client.connect()
            result = await redis_client.health_check()
            
            assert result is True


@pytest.mark.asyncio
async def test_redis_health_check_failure(redis_client):
    """Test health check failure."""
    with patch('redis.asyncio.Redis') as mock_redis:
        mock_instance = AsyncMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.side_effect = ConnectionError("Ping failed")
        
        with patch('redis.asyncio.connection.ConnectionPool.from_url'):
            with pytest.raises(ConnectionError):
                await redis_client.connect()
            
            # Test health check directly on a client that failed to connect
            redis_client._client = mock_instance
            result = await redis_client.health_check()
            
            assert result is False


@pytest.mark.asyncio
async def test_redis_execute_with_retry_success(redis_client):
    """Test successful operation with retry mechanism."""
    with patch('redis.asyncio.Redis') as mock_redis:
        mock_instance = AsyncMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        
        async def mock_operation(client, key, value):
            return await client.set(key, value)
        
        mock_instance.set.return_value = True
        
        with patch('redis.asyncio.connection.ConnectionPool.from_url'):
            await redis_client.connect()
            result = await redis_client.execute_with_retry(mock_operation, "test_key", "test_value")
            
            assert result is True
            mock_instance.set.assert_called_once_with("test_key", "test_value")


@pytest.mark.asyncio
async def test_redis_execute_with_retry_failure_then_success(redis_client):
    """Test retry mechanism with initial failure then success."""
    with patch('redis.asyncio.Redis') as mock_redis:
        mock_instance = AsyncMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        
        async def mock_operation(client, key, value):
            return await client.set(key, value)
        
        # First call fails, second succeeds
        mock_instance.set.side_effect = [ConnectionError("Connection lost"), True]
        
        with patch('redis.asyncio.connection.ConnectionPool.from_url'):
            await redis_client.connect()
            
            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await redis_client.execute_with_retry(mock_operation, "test_key", "test_value")
            
            assert result is True
            assert mock_instance.set.call_count == 2


@pytest.mark.asyncio
async def test_redis_execute_with_retry_max_retries_exceeded(redis_client):
    """Test retry mechanism when max retries are exceeded."""
    with patch('redis.asyncio.Redis') as mock_redis:
        mock_instance = AsyncMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        
        async def mock_operation(client, key, value):
            return await client.set(key, value)
        
        mock_instance.set.side_effect = ConnectionError("Persistent connection error")
        
        with patch('redis.asyncio.connection.ConnectionPool.from_url'):
            await redis_client.connect()
            
            with patch('asyncio.sleep', new_callable=AsyncMock):
                with pytest.raises(ConnectionError):
                    await redis_client.execute_with_retry(mock_operation, "test_key", "test_value")
            
            assert mock_instance.set.call_count == 3  # Max retries


@pytest.mark.asyncio
async def test_get_redis_client_not_connected():
    """Test getting Redis client when not connected."""
    with patch('app.services.redis_client.redis_client') as mock_client:
        mock_client.is_connected = False
        mock_client.connect = AsyncMock()
        
        result = await get_redis_client()
        
        mock_client.connect.assert_called_once()
        assert result == mock_client


@pytest.mark.asyncio
async def test_init_redis_success():
    """Test Redis initialization success."""
    with patch('app.services.redis_client.redis_client') as mock_client:
        mock_client.connect = AsyncMock()
        
        await init_redis()
        
        mock_client.connect.assert_called_once()


@pytest.mark.asyncio
async def test_init_redis_failure():
    """Test Redis initialization failure."""
    with patch('app.services.redis_client.redis_client') as mock_client:
        mock_client.connect = AsyncMock(side_effect=ConnectionError("Init failed"))
        
        with pytest.raises(ConnectionError):
            await init_redis()


@pytest.mark.asyncio
async def test_close_redis():
    """Test Redis connection closure."""
    with patch('app.services.redis_client.redis_client') as mock_client:
        mock_client.disconnect = AsyncMock()
        
        await close_redis()
        
        mock_client.disconnect.assert_called_once()