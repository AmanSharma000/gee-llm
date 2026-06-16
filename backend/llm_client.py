"""
LLM client using Cohere API (V2) with caching support.
"""
import os
import time
import random
import cohere

# ... (imports)

# ... (imports)
from .logging_config import setup_logger, log_with_context

logger = setup_logger(__name__)

try:
    import streamlit as st
except ImportError:
    st = None

# Import cache manager (lazy import to avoid circular dependencies)
_cache_manager = None

def _get_cache_manager():
    global _cache_manager
    if _cache_manager is None:
        try:
            from .cache_manager import cache_manager
            _cache_manager = cache_manager
        except ImportError:
            _cache_manager = None
    return _cache_manager


def _get_api_key() -> str:
    """
    Get COHERE_API_KEY from:
    1) Environment variable (local dev), or
    2) Streamlit secrets (cloud)
    """
    key = os.getenv("COHERE_API_KEY")
    if key:
        return key

    try:
        if st is not None and "COHERE_API_KEY" in st.secrets:
            return st.secrets["COHERE_API_KEY"]
    except FileNotFoundError:
        pass
    except Exception:
        pass

    # If we are here, we didn't find the key.
    print("Warning: COHERE_API_KEY not found in env or secrets.")
    return ""


# Create a single global client
_client: cohere.ClientV2 | None = None


def _get_client() -> cohere.ClientV2:
    global _client
    if _client is None:
        api_key = _get_api_key()
        _client = cohere.ClientV2(api_key)
    return _client


MODEL_NAME = "command-a-03-2025"


def _call_with_retry(client, model, messages, max_retries=3):
    """
    Call LLM with exponential backoff for transient errors.
    Retries on 5xx errors, connection issues, and rate limits (429).
    Fails fast on other 4xx errors (Auth, Bad Request).
    """
    attempt = 0
    while True:
        try:
            return client.chat(
                model=model,
                messages=messages
            )
        except Exception as e:
            attempt += 1
            error_msg = str(e).lower()
            
            # Determine if error is transient
            is_server_error = any(code in error_msg for code in ["500", "502", "503", "504"])
            is_connection = "connection" in error_msg or "timeout" in error_msg
            is_rate_limit = "429" in error_msg or "too many requests" in error_msg
            
            # Stop if max retries reached OR error is not transient (e.g. 401 Auth)
            if attempt > max_retries or not (is_server_error or is_connection or is_rate_limit):
                raise e
            
            # Exponential backoff: 1s, 2s, 4s... with jitter
            delay = (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            
            log_with_context(
                logger, 30, # WARNING
                f"LLM call failed (Attempt {attempt}/{max_retries}). Retrying in {delay:.2f}s...",
                error=str(e)
            )
            time.sleep(delay)

def call_llm(prompt: str, use_cache: bool = True) -> str:
    """
    Call Cohere LLM with the given prompt, with optional caching.
    
    Args:
        prompt: The prompt to send to the LLM
        use_cache: Whether to use caching (default: True)
        
    Returns:
        The LLM response text
    """
    start_time = time.time()
    
    # Check cache first
    cache_mgr = _get_cache_manager() if use_cache else None
    if cache_mgr:
        cached_response = cache_mgr.get_llm_response(prompt)
        if cached_response:
            duration = time.time() - start_time
            log_with_context(
                logger, 20, "LLM call served from cache",
                model=MODEL_NAME,
                prompt_length=len(prompt),
                response_length=len(cached_response),
                duration_ms=round(duration * 1000, 2)
            )
            return cached_response
    
    # Cache miss or caching disabled - call API
    try:
        client = _get_client()
        
        # Use retry logic
        response = _call_with_retry(
            client=client,
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        # Extract text from response
        response_text = response.message.content[0].text
        
        duration = time.time() - start_time
        
        # Cache the response
        if cache_mgr:
            cache_mgr.set_llm_response(prompt, response_text)
        
        log_with_context(
            logger, 20, "LLM call completed",
            model=MODEL_NAME,
            prompt_length=len(prompt),
            response_length=len(response_text),
            duration_ms=round(duration * 1000, 2),
            cached=False
        )
        
        return response_text
        
    except Exception as e:
        duration = time.time() - start_time
        log_with_context(
            logger, 40, "LLM call failed",
            model=MODEL_NAME,
            error=str(e),
            duration_ms=round(duration * 1000, 2)
        )
        raise
