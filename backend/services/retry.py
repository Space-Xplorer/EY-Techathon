"""
Retry Logic for External APIs
Provides decorators and utilities for retrying failed API calls
"""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
    retry_if_exception_type,
    before_sleep_log
)
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)


# Groq API retry decorator
def retry_groq_api(max_attempts: int = 3):
    """
    Retry decorator for Groq API calls
    
    Retries with exponential backoff:
    - Attempt 1: Wait 2s
    - Attempt 2: Wait 4s  
    - Attempt 3: Wait 8s
    
    Usage:
        @retry_groq_api(max_attempts=3)
        def call_groq(prompt):
            return groq_client.chat.completions.create(...)
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )


# Supabase retry decorator
def retry_supabase_query(max_attempts: int = 3):
    """
    Retry decorator for Supabase queries
    
    Retries with fixed 2s wait between attempts
    
    Usage:
        @retry_supabase_query(max_attempts=3)
        def query_rfps():
            return supabase.table("rfp_summaries").select("*").execute()
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_fixed(2),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )


# Generic retry with fallback
def with_fallback(primary_func: Callable, fallback_func: Callable, *args, **kwargs) -> Any:
    """
    Execute primary function with fallback on failure
    
    Usage:
        result = with_fallback(
            lambda: call_groq_api(prompt),
            lambda: call_openai_api(prompt)
        )
    """
    try:
        return primary_func(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Primary function failed: {e}, trying fallback")
        try:
            return fallback_func(*args, **kwargs)
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {fallback_error}")
            raise


# Specific retry strategies
class RetryStrategies:
    """Pre-configured retry strategies for common use cases"""
    
    @staticmethod
    def groq_with_openai_fallback(groq_func: Callable, openai_func: Callable, *args, **kwargs):
        """
        Try Groq first (3 retries), then fall back to OpenAI
        
        Usage:
            result = RetryStrategies.groq_with_openai_fallback(
                groq_func=lambda: groq_call(prompt),
                openai_func=lambda: openai_call(prompt)
            )
        """
        @retry_groq_api(max_attempts=3)
        def _retry_groq():
            return groq_func(*args, **kwargs)
        
        try:
            return _retry_groq()
        except Exception as e:
            logger.warning(f"Groq failed after retries: {e}, falling back to OpenAI")
            return openai_func(*args, **kwargs)
    
    @staticmethod
    def database_with_retry(query_func: Callable, *args, **kwargs):
        """
        Database query with automatic retry
        
        Usage:
            result = RetryStrategies.database_with_retry(
                lambda: supabase.table("rfps").select("*").execute()
            )
        """
        @retry_supabase_query(max_attempts=3)
        def _retry_query():
            return query_func(*args, **kwargs)
        
        return _retry_query()


if __name__ == "__main__":
    # Test retry logic
    import random
    
    @retry_groq_api(max_attempts=3)
    def flaky_function():
        if random.random() < 0.7:  # 70% failure rate
            raise Exception("Simulated failure")
        return "Success!"
    
    try:
        result = flaky_function()
        print(f"Result: {result}")
    except Exception as e:
        print(f"Failed after retries: {e}")
