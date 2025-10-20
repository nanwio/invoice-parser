"""
Simple script to clear Redis cache.
Use after prompt updates to force re-processing with new rules.
"""

import asyncio
from invoice_processing.caching.redis_cache import invoice_cache
from loguru import logger


def main():
    """Clear all cached invoices."""
    logger.info("Starting cache clear operation...")

    result = invoice_cache.clear_all_cache()

    if result.get("success"):
        deleted_count = result.get("deleted_count", 0)
        logger.info(f"✅ Successfully cleared {deleted_count} cached invoice(s)")
        print(f"✅ Cache cleared: {deleted_count} invoice(s) removed")
    else:
        error_msg = result.get("error") or result.get("message", "Unknown error")
        logger.error(f"❌ Failed to clear cache: {error_msg}")
        print(f"❌ Error: {error_msg}")


if __name__ == "__main__":
    main()
