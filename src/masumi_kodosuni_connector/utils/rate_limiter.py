"""Rate limiting and retry utilities for external API calls."""
import asyncio
import time
from typing import Optional, Callable, Any, Dict
from masumi_kodosuni_connector.config.logging import get_logger

logger = get_logger("rate_limiter")


class RateLimiter:
    """Token bucket rate limiter for API calls."""
    
    def __init__(self, max_calls: int = 10, time_window: float = 60.0):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make an API call, blocking if necessary."""
        async with self._lock:
            now = time.time()
            
            # Remove old calls outside the time window
            self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]
            
            # If we're at the limit, wait until we can make another call
            if len(self.calls) >= self.max_calls:
                oldest_call = min(self.calls)
                wait_time = self.time_window - (now - oldest_call)
                if wait_time > 0:
                    logger.warning("Rate limit reached, waiting", 
                                 wait_seconds=round(wait_time, 2),
                                 current_calls=len(self.calls),
                                 max_calls=self.max_calls,
                                 time_window=self.time_window)
                    await asyncio.sleep(wait_time)
                    return await self.acquire()  # Recursive call after waiting
            
            # Record this call
            self.calls.append(now)


class ExponentialBackoff:
    """Exponential backoff utility for retrying failed requests."""
    
    def __init__(self, 
                 max_retries: int = 3, 
                 base_delay: float = 1.0, 
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    async def execute(self, 
                     func: Callable,
                     *args,
                     retry_on_exceptions: tuple = (Exception,),
                     **kwargs) -> Any:
        """Execute function with exponential backoff retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    logger.info("Request succeeded after retry", attempt=attempt)
                return result
                
            except retry_on_exceptions as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    logger.error("All retry attempts exhausted", 
                               attempts=attempt + 1, 
                               final_error=str(e))
                    raise e
                
                # Calculate delay with exponential backoff
                delay = min(
                    self.base_delay * (self.exponential_base ** attempt),
                    self.max_delay
                )
                
                logger.warning("Request failed, retrying with backoff",
                             attempt=attempt + 1,
                             max_attempts=self.max_retries + 1,
                             delay_seconds=delay,
                             error=str(e))
                
                await asyncio.sleep(delay)
        
        # This should never be reached due to the raise in the loop
        raise last_exception


class RateLimitedHTTPClient:
    """HTTP client wrapper with built-in rate limiting and retry logic."""
    
    def __init__(self, 
                 rate_limiter: Optional[RateLimiter] = None,
                 backoff: Optional[ExponentialBackoff] = None):
        self.rate_limiter = rate_limiter or RateLimiter(max_calls=10, time_window=60.0)
        self.backoff = backoff or ExponentialBackoff(max_retries=3)
        self.logger = get_logger("http_client")
    
    async def request(self, client, method: str, url: str, **kwargs) -> Any:
        """Make an HTTP request with rate limiting and retry logic."""
        
        async def _make_request():
            # Apply rate limiting
            await self.rate_limiter.acquire()
            
            self.logger.debug("Making HTTP request", method=method, url=url)
            
            # Make the actual request
            response = await getattr(client, method.lower())(url, **kwargs)
            
            # Check for rate limiting response codes
            if response.status_code == 429:  # Too Many Requests
                retry_after = response.headers.get('retry-after', '5')  # Default to 5 seconds
                wait_time = float(retry_after)
                self.logger.warning("Server rate limit hit, waiting", 
                                  wait_seconds=wait_time,
                                  status_code=response.status_code,
                                  url=url)
                await asyncio.sleep(wait_time)
                raise Exception(f"Rate limited by server: {response.status_code}")
            
            # Also check for 503 Service Unavailable which might indicate rate limiting
            if response.status_code == 503:
                self.logger.warning("Service unavailable, possibly rate limited", 
                                  status_code=response.status_code,
                                  url=url)
                raise Exception(f"Service unavailable (possible rate limit): {response.status_code}")
            
            # Raise for other HTTP errors (will be caught by backoff)
            if response.status_code >= 500:
                raise Exception(f"Server error: {response.status_code}")
            
            response.raise_for_status()
            return response
        
        # Execute with exponential backoff
        return await self.backoff.execute(
            _make_request,
            retry_on_exceptions=(Exception,)  # Retry on any exception
        )


# Global instances for use across the application
kodosumi_rate_limiter = RateLimiter(max_calls=12, time_window=60.0)  # 12 calls per minute (more conservative)
masumi_rate_limiter = RateLimiter(max_calls=30, time_window=60.0)    # 30 calls per minute

kodosumi_http_client = RateLimitedHTTPClient(
    rate_limiter=kodosumi_rate_limiter,
    backoff=ExponentialBackoff(max_retries=3, base_delay=2.0, max_delay=60.0)  # Longer delays for rate limiting
)

masumi_http_client = RateLimitedHTTPClient(
    rate_limiter=masumi_rate_limiter,
    backoff=ExponentialBackoff(max_retries=3, base_delay=0.5, max_delay=15.0)
)