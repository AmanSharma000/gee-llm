"""
Cache manager for GEE results and LLM responses.
Uses disk-based caching to improve performance and reduce API costs.
"""
import hashlib
import json
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
from diskcache import Cache
from backend.logging_config import setup_logger, log_with_context

logger = setup_logger('backend.cache_manager')

# Cache directory
CACHE_DIR = 'data/cache'

# Default TTL (Time To Live) in seconds
DEFAULT_TTL = 24 * 60 * 60  # 24 hours

# Initialize cache
cache = Cache(CACHE_DIR)


class CacheManager:
    """Manages caching for GEE results and LLM responses."""
    
    def __init__(self, ttl: int = DEFAULT_TTL):
        """
        Initialize cache manager.
        
        Args:
            ttl: Time to live in seconds (default: 24 hours)
        """
        self.ttl = ttl
        self.cache = cache
        
        log_with_context(
            logger, 20, "CacheManager initialized",
            ttl_hours=ttl / 3600,
            cache_dir=CACHE_DIR
        )
    
    def _generate_key(self, prefix: str, data: str) -> str:
        """
        Generate a cache key from data.
        
        Args:
            prefix: Key prefix (e.g., 'gee', 'llm')
            data: Data to hash
            
        Returns:
            Cache key string
        """
        # Create hash of the data
        hash_obj = hashlib.sha256(data.encode('utf-8'))
        hash_str = hash_obj.hexdigest()[:16]  # Use first 16 chars
        
        return f"{prefix}:{hash_str}"
    
    def get_gee_result(self, code: str) -> Optional[Any]:
        """
        Get cached GEE execution result.
        
        Args:
            code: GEE Python code
            
        Returns:
            Cached result or None if not found
        """
        key = self._generate_key('gee', code)
        
        try:
            cached_data = self.cache.get(key)
            
            if cached_data is not None:
                log_with_context(
                    logger, 20, "Cache hit for GEE result",
                    key=key,
                    code_length=len(code)
                )
                return cached_data['result']
            else:
                log_with_context(
                    logger, 20, "Cache miss for GEE result",
                    key=key
                )
                return None
                
        except Exception as e:
            log_with_context(
                logger, 30, "Cache get error",
                error=str(e),
                key=key
            )
            return None
    
    def set_gee_result(self, code: str, result: Any) -> None:
        """
        Cache GEE execution result.
        
        Args:
            code: GEE Python code
            result: Execution result
        """
        key = self._generate_key('gee', code)
        
        try:
            cached_data = {
                'result': result,
                'timestamp': datetime.now().isoformat(),
                'code': code
            }
            
            self.cache.set(key, cached_data, expire=self.ttl)
            
            log_with_context(
                logger, 20, "Cached GEE result",
                key=key,
                code_length=len(code),
                ttl_hours=self.ttl / 3600
            )
            
        except Exception as e:
            log_with_context(
                logger, 30, "Cache set error",
                error=str(e),
                key=key
            )
    
    def get_llm_response(self, prompt: str) -> Optional[str]:
        """
        Get cached LLM response.
        
        Args:
            prompt: LLM prompt
            
        Returns:
            Cached response or None if not found
        """
        key = self._generate_key('llm', prompt)
        
        try:
            cached_data = self.cache.get(key)
            
            if cached_data is not None:
                log_with_context(
                    logger, 20, "Cache hit for LLM response",
                    key=key,
                    prompt_length=len(prompt)
                )
                return cached_data['response']
            else:
                log_with_context(
                    logger, 20, "Cache miss for LLM response",
                    key=key
                )
                return None
                
        except Exception as e:
            log_with_context(
                logger, 30, "Cache get error",
                error=str(e),
                key=key
            )
            return None
    
    def set_llm_response(self, prompt: str, response: str) -> None:
        """
        Cache LLM response.
        
        Args:
            prompt: LLM prompt
            response: LLM response
        """
        key = self._generate_key('llm', prompt)
        
        try:
            cached_data = {
                'response': response,
                'timestamp': datetime.now().isoformat(),
                'prompt_length': len(prompt)
            }
            
            self.cache.set(key, cached_data, expire=self.ttl)
            
            log_with_context(
                logger, 20, "Cached LLM response",
                key=key,
                prompt_length=len(prompt),
                response_length=len(response),
                ttl_hours=self.ttl / 3600
            )
            
        except Exception as e:
            log_with_context(
                logger, 30, "Cache set error",
                error=str(e),
                key=key
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        try:
            stats = {
                'size': len(self.cache),
                'volume': self.cache.volume(),
                'hits': getattr(self.cache, 'hits', 0),
                'misses': getattr(self.cache, 'misses', 0)
            }
            
            log_with_context(
                logger, 20, "Cache stats retrieved",
                **stats
            )
            
            return stats
            
        except Exception as e:
            log_with_context(
                logger, 30, "Cache stats error",
                error=str(e)
            )
            return {}
    
    def clear(self) -> None:
        """Clear all cached data."""
        try:
            self.cache.clear()
            log_with_context(logger, 20, "Cache cleared")
        except Exception as e:
            log_with_context(
                logger, 30, "Cache clear error",
                error=str(e)
            )


# Global cache manager instance
cache_manager = CacheManager()


def get_cached_gee_result(code: str) -> Optional[Any]:
    """Convenience function to get cached GEE result."""
    return cache_manager.get_gee_result(code)


def cache_gee_result(code: str, result: Any) -> None:
    """Convenience function to cache GEE result."""
    cache_manager.set_gee_result(code, result)


def get_cached_llm_response(prompt: str) -> Optional[str]:
    """Convenience function to get cached LLM response."""
    return cache_manager.get_llm_response(prompt)


def cache_llm_response(prompt: str, response: str) -> None:
    """Convenience function to cache LLM response."""
    cache_manager.set_llm_response(prompt, response)
