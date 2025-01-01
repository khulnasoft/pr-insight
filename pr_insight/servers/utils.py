import hashlib
import hmac
import time
from collections import defaultdict
from typing import Callable, Any

from fastapi import HTTPException


def verify_signature(payload_body: bytes, secret_token: str, signature_header: str) -> None:
    """Verify that the payload was sent from GitHub by validating SHA256.

    Args:
        payload_body: Original request body to verify (request.body())
        secret_token: GitHub app webhook token (WEBHOOK_SECRET)
        signature_header: Header received from GitHub (x-hub-signature-256)

    Raises:
        HTTPException: If signature header is missing or signatures don't match
    """
    if not signature_header:
        raise HTTPException(status_code=403, detail="x-hub-signature-256 header is missing!")
    
    hash_object = hmac.new(secret_token.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = f"sha256={hash_object.hexdigest()}"
    
    if not hmac.compare_digest(expected_signature, signature_header):
        raise HTTPException(status_code=403, detail="Request signatures didn't match!")


class RateLimitExceeded(Exception):
    """Raised when the git provider API rate limit has been exceeded."""
    pass


class DefaultDictWithTimeout(defaultdict):
    """A defaultdict with a time-to-live (TTL) for cached items.
    
    This class extends defaultdict to add expiration functionality for stored items.
    Keys will be automatically removed after the specified TTL period.
    """

    def __init__(
        self,
        default_factory: Callable[[], Any] | None = None,
        ttl: int | None = None,
        refresh_interval: int = 60,
        update_key_time_on_get: bool = True,
        *args,
        **kwargs,
    ):
        """Initialize the timeout dictionary.

        Args:
            default_factory: The default factory to use for missing keys
            ttl: The time-to-live (TTL) in seconds for each item
            refresh_interval: How often to check and remove expired items (in seconds)
            update_key_time_on_get: Whether to update item expiration on access
            *args: Additional positional arguments for defaultdict
            **kwargs: Additional keyword arguments for defaultdict
        """
        super().__init__(default_factory, *args, **kwargs)
        self.__key_times = {}
        self.__ttl = ttl
        self.__refresh_interval = refresh_interval
        self.__update_key_time_on_get = update_key_time_on_get
        self.__last_refresh = self.__time() - self.__refresh_interval

    @staticmethod
    def __time() -> float:
        """Get current monotonic time.

        Returns:
            Current time from monotonic clock
        """
        return time.monotonic()

    def __refresh(self) -> None:
        """Remove expired items if refresh interval has elapsed."""
        if self.__ttl is None:
            return

        current_time = self.__time()
        if current_time - self.__last_refresh <= self.__refresh_interval:
            return

        expired_keys = [
            key for key, key_time in self.__key_times.items() 
            if current_time - key_time > self.__ttl
        ]
        for key in expired_keys:
            del self[key]
            
        self.__last_refresh = current_time

    def __getitem__(self, key: Any) -> Any:
        if self.__update_key_time_on_get:
            self.__key_times[key] = self.__time()
        self.__refresh()
        return super().__getitem__(key)

    def __setitem__(self, key: Any, value: Any) -> None:
        self.__key_times[key] = self.__time()
        super().__setitem__(key, value)

    def __delitem__(self, key: Any) -> None:
        del self.__key_times[key]
        super().__delitem__(key)
