#!/usr/bin/env python3
"""Debug Redis connection."""

import asyncio
import redis.asyncio as redis
from app.services.redis_client import get_redis_client_sync

async def test_redis_direct():
    """Test Redis connection directly."""
    try:
        client = redis.Redis(host="localhost", port=6379, db=0)
        response = await client.ping()
        print(f"Direct Redis ping: {response}")
        await client.close()
        return response
    except Exception as e:
        print(f"Direct Redis test failed: {e}")
        return False

async def test_redis_client():
    """Test Redis client from app."""
    try:
        client = get_redis_client_sync()
        print(f"Redis client initialized: {client}")
        health = await client.health_check()
        print(f"Redis health check: {health}")
        return health
    except Exception as e:
        print(f"Redis client test failed: {e}")
        return False

async def main():
    print("Testing Redis connection...")
    await test_redis_direct()
    await test_redis_client()

if __name__ == "__main__":
    asyncio.run(main())