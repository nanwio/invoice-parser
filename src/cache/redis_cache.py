"""
Redis caching service
One responsibility: cache invoice processing results
"""

import json
import hashlib
from typing import Optional
from loguru import logger

from src.domain.models import Invoice
from src.config.settings import app_settings


class InvoiceCacheService:
    """
    Simple caching service for processed invoices.
    Uses Redis for fast retrieval of previously processed invoices.
    """

    def __init__(self):
        """Initialize cache service."""
        self._redis_client = None
        self._setup_redis()

    def _setup_redis(self):
        """Set up Redis connection."""
        if not app_settings.database.CACHE_ENABLED:
            logger.info("Caching disabled")
            return

        try:
            import redis
            self._redis_client = redis.from_url(
                app_settings.database.REDIS_URL,
                decode_responses=True
            )
            # Test connection
            self._redis_client.ping()
            logger.info("Redis cache connected")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self._redis_client = None

    async def get_cached_invoice(self, file_hash: str) -> Optional[Invoice]:
        """
        Get cached invoice by file hash.

        Args:
            file_hash: SHA256 hash of the PDF file

        Returns:
            Invoice object if cached, None otherwise
        """
        if not self._redis_client:
            return None

        try:
            cached_data = self._redis_client.get(f"invoice:{file_hash}")
            if cached_data:
                logger.info(f"Cache HIT for file {file_hash[:8]}...")
                invoice_dict = json.loads(cached_data)
                return Invoice(**invoice_dict)
            else:
                logger.info(f"Cache MISS for file {file_hash[:8]}...")
                return None

        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
            return None

    async def cache_invoice(self, file_hash: str, invoice: Invoice, ttl_hours: int = 24):
        """
        Cache processed invoice.

        Args:
            file_hash: SHA256 hash of the PDF file
            invoice: Processed invoice object
            ttl_hours: Time to live in hours
        """
        if not self._redis_client:
            return

        try:
            invoice_json = json.dumps(invoice.model_dump(), default=str)
            ttl_seconds = ttl_hours * 3600

            self._redis_client.setex(
                f"invoice:{file_hash}",
                ttl_seconds,
                invoice_json
            )
            logger.info(f"Invoice cached for {file_hash[:8]}... (TTL: {ttl_hours}h)")

        except Exception as e:
            logger.error(f"Cache storage error: {e}")

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        if not self._redis_client:
            return {"cache_enabled": False}

        try:
            info = self._redis_client.info()
            return {
                "cache_enabled": True,
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "Unknown"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            return {"cache_enabled": False, "error": str(e)}

    def clear_all_cache(self) -> dict:
        """Clear all cached invoices. Use after prompt updates to force re-processing."""
        if not self._redis_client:
            return {"success": False, "message": "Cache not enabled"}

        try:
            # Get all invoice keys
            keys = self._redis_client.keys("invoice:*")
            if keys:
                deleted_count = self._redis_client.delete(*keys)
                logger.info(f"Cleared {deleted_count} cached invoices")
                return {"success": True, "deleted_count": deleted_count}
            else:
                logger.info("No cached invoices to clear")
                return {"success": True, "deleted_count": 0}
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return {"success": False, "error": str(e)}


# Global cache instance
invoice_cache = InvoiceCacheService()