# Copyright 2024 Artificial Intelligence Labs, SL

from abc import ABC, abstractmethod
from typing import Optional
from loguru import logger


class CacheStrategy(ABC):
    """Abstract base class for cache implementations."""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to cache backend."""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Disconnect from cache backend."""
        pass
    
    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: str, ttl: int) -> bool:
        """Set value in cache with TTL in seconds."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass


class RedisStrategy(CacheStrategy):
    """
    Redis-based cache implementation.
    """
    
    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._client = None
    
    async def connect(self) -> bool:
        try:
            import redis.asyncio as redis
            self._client = redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                retry_on_error=[
                    redis.ConnectionError,
                    redis.TimeoutError
                ]
            )
            await self._client.ping()
            logger.info("Redis connection established")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    async def disconnect(self):
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Redis connection closed")
    
    async def get(self, key: str) -> Optional[str]:
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            return None
    
    async def set(self, key: str, value: str, ttl: int) -> bool:
        try:
            await self._client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.warning(f"Redis set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        try:
            return (await self._client.delete(key)) > 0
        except Exception as e:
            logger.warning(f"Redis delete error: {e}")
            return False


class CloudflareKVStrategy(CacheStrategy):
    """
    Cloudflare KV-based cache implementation using the official SDK.
    """
    
    def __init__(self, kv_namespace_id: str, account_id: str, api_token: str):
        self._namespace_id = kv_namespace_id
        self._account_id = account_id
        self._api_token = api_token
        self._client = None
    
    async def connect(self) -> bool:
        try:
            from cloudflare import AsyncCloudflare
            self._client = AsyncCloudflare(api_token=self._api_token)
            logger.info("Cloudflare KV cache ready")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Cloudflare client: {e}")
            return False
    
    async def disconnect(self):
        if self._client:
            await self._client.close()
            self._client = None
    
    async def get(self, key: str) -> Optional[str]:
        try:
            result = await self._client.kv.namespaces.values.get(
                key_name=key,
                account_id=self._account_id,
                namespace_id=self._namespace_id
            )
            return result if isinstance(result, str) else None
        except Exception as e:
            if "404" in str(e):
                return None
            logger.warning(f"KV get error: {e}")
            return None
    
    async def set(self, key: str, value: str, ttl: int) -> bool:
        try:
            await self._client.kv.namespaces.values.update(
                key_name=key,
                account_id=self._account_id,
                namespace_id=self._namespace_id,
                value=value,
                expiration_ttl=ttl
            )
            return True
        except Exception as e:
            logger.warning(f"KV set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        try:
            await self._client.kv.namespaces.values.delete(
                key_name=key,
                account_id=self._account_id,
                namespace_id=self._namespace_id
            )
            return True
        except Exception as e:
            logger.warning(f"KV delete error: {e}")
            return False


class LocalKVStrategy(CacheStrategy):
    """
    Local KV strategy for development when running in Cloudflare containers.
    """
    
    def __init__(self):
        self._store = {}
    
    async def connect(self) -> bool:
        logger.info("Local KV cache ready (development mode)")
        return True
    
    async def disconnect(self):
        self._store.clear()
    
    async def get(self, key: str) -> Optional[str]:
        return self._store.get(key)
    
    async def set(self, key: str, value: str, ttl: int) -> bool:
        # Note: TTL not implemented in local version
        self._store[key] = value
        return True
    
    async def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False