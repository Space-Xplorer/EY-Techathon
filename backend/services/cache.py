"""
Redis Caching Service
Provides caching layer for frequently accessed data
"""

import redis
import json
import os
from typing import Optional, Any
from functools import wraps
from dotenv import load_dotenv

load_dotenv()


class CacheService:
    """Redis-based caching service"""
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize cache service
        
        Args:
            redis_url: Redis connection URL (default: from env or localhost)
        """
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        try:
            self.client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.client.ping()
            self.available = True
            print("✓ Redis cache connected")
        except Exception as e:
            print(f"⚠️ Redis cache unavailable: {e}")
            self.client = None
            self.available = False
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.available:
            return None
        
        try:
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """
        Set value in cache with TTL
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default: 1 hour)
        """
        if not self.available:
            return False
        
        try:
            self.client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str):
        """Delete key from cache"""
        if not self.available:
            return False
        
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    def clear_pattern(self, pattern: str):
        """Delete all keys matching pattern"""
        if not self.available:
            return False
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
            return True
        except Exception as e:
            print(f"Cache clear error: {e}")
            return False


# Decorator for caching function results
def cached(key_prefix: str, ttl: int = 3600):
    """
    Decorator to cache function results
    
    Usage:
        @cached("oem_products", ttl=3600)
        def get_oem_products():
            return fetch_from_db()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = CacheService()
            
            # Generate cache key
            cache_key = f"{key_prefix}:{args}:{kwargs}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                print(f"Cache HIT: {cache_key}")
                return result
            
            # Cache miss - call function
            print(f"Cache MISS: {cache_key}")
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


# Global cache instance
_cache_instance = None

def get_cache() -> CacheService:
    """Get global cache instance (singleton)"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheService()
    return _cache_instance


if __name__ == "__main__":
    # Test cache
    cache = CacheService()
    
    if cache.available:
        cache.set("test_key", {"value": 123}, ttl=60)
        result = cache.get("test_key")
        print(f"Cache test: {result}")
    else:
        print("Cache not available - install Redis:")
        print("  docker run -d -p 6379:6379 redis:7-alpine")
