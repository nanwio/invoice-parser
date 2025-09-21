# Copyright 2024 Artificial Intelligence Labs, SL

import json
import os

from typing import Optional
from loguru import logger

from app.settings import settings
from app.services.parser.models import Invoice

from .strategies import (
    CacheStrategy, 
    RedisStrategy, 
    CloudflareKVStrategy,
    LocalKVStrategy
)


class CacheService:
    """
    Unified caching service with strategy pattern.
    Automatically selects Redis or Cloudflare KV based on environment.
    """
    
    def __init__(self):
        self._strategy: Optional[CacheStrategy] = None
        self._cache_prefix = "invoice:"
        self._ttl_seconds = 2400000  # 27 days
        
    def _get_strategy(self) -> CacheStrategy:
        """
        Select appropriate cache strategy based on environment.
        """

        if self._strategy is None:

            # Check if we're running on Cloudflare
            if os.getenv("CF_ACCOUNT_ID") and os.getenv("CF_API_TOKEN"):
                # Use Cloudflare KV
                kv_namespace_id = os.getenv("KV_NAMESPACE_ID", "")
                account_id = os.getenv("CF_ACCOUNT_ID", "")
                api_token = os.getenv("CF_API_TOKEN", "")
                
                if kv_namespace_id:
                    self._strategy = CloudflareKVStrategy(
                        kv_namespace_id=kv_namespace_id,
                        account_id=account_id,
                        api_token=api_token
                    )
                    logger.info("Using Cloudflare KV cache strategy")
                else:
                    # Fallback to local KV for development
                    self._strategy = LocalKVStrategy()
                    logger.info("Using local KV cache strategy (development)")
            else:
                # Use Redis
                self._strategy = RedisStrategy(settings.REDIS_URL)
                logger.info("Using Redis cache strategy")
                
        return self._strategy
    
    async def connect(self) -> bool:
        """
        Connect to cache backend.
        """
        try:
            strategy = self._get_strategy()
            return await strategy.connect()
        except Exception as e:
            logger.error(f"Failed to connect to cache: {e}")
            return False
    
    async def disconnect(self):
        """
        Disconnect from cache backend.
        """
        if self._strategy:
            await self._strategy.disconnect()
            self._strategy = None
    
    def _get_cache_key(self, file_hash: str) -> str:
        """
        Generate cache key from file hash.
        """
        return f"{self._cache_prefix}{file_hash}"
    
    async def get_invoice(self, file_hash: str) -> Optional[Invoice]:
        """
        Retrieve cached invoice by file hash.
        
        Args:
            file_hash: SHA256 hash of the PDF file
            
        Returns:
            Cached Invoice object or None if not found
        """
        if not settings.CACHE_ENABLED:
            return None
            
        try:
            strategy = self._get_strategy()
            key = self._get_cache_key(file_hash)
            cached_data = await strategy.get(key)
            
            if cached_data:
                logger.info(f"Cache hit for hash: {file_hash[:8]}...")
                invoice_dict = json.loads(cached_data)
                return Invoice(**invoice_dict)
            else:
                logger.info(f"Cache miss for hash: {file_hash[:8]}...")
                return None
                
        except Exception as e:
            logger.warning(f"Error retrieving from cache: {e}")
            return None
    
    async def set_invoice(self, file_hash: str, invoice: Invoice) -> bool:
        """
        Cache an invoice with TTL.
        
        Args:
            file_hash: SHA256 hash of the PDF file
            invoice: Invoice object to cache
            
        Returns:
            True if cached successfully, False otherwise
        """
        if not settings.CACHE_ENABLED:
            return False
            
        try:
            strategy = self._get_strategy()
            key = self._get_cache_key(file_hash)
            invoice_json = invoice.model_dump_json()
            
            success = await strategy.set(key, invoice_json, self._ttl_seconds)
            if success:
                logger.info(f"Cached invoice for hash: {file_hash[:8]}...")
            return success
            
        except Exception as e:
            logger.warning(f"Error caching invoice: {e}")
            return False
    
    async def delete_invoice(self, file_hash: str) -> bool:
        """
        Remove an invoice from cache.
        
        Args:
            file_hash: SHA256 hash of the PDF file
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            strategy = self._get_strategy()
            key = self._get_cache_key(file_hash)
            deleted = await strategy.delete(key)

            if deleted:
                logger.info(f"Deleted cached invoice for hash: {file_hash[:8]}...")

            return deleted
            
        except Exception as e:
            logger.warning(f"Error deleting from cache: {e}")
            return False


cache_service = CacheService()