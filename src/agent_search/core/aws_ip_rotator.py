"""
Async AWS IP Rotation HTTP Client

Routes requests through AWS API Gateway for automatic IP rotation.
Falls back from direct -> AWS Gateway on 429/403/timeout errors.
Tracks failures per-URL and adaptively skips direct attempts after repeated failures.

Environment Variables:
    USE_AWS_IP_ROTATION_FALLBACK: Enable/disable (default: "true")
    AWS_API_GATEWAY_ID: Required - your deployed API Gateway ID
    AWS_REGION: AWS region (default: "us-east-1")
"""

import os
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import quote, urlencode

# Optional async support
try:
    import aiohttp
    import asyncio
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    aiohttp = None
    asyncio = None


class AwsHttpClient:
    """
    Async HTTP client with automatic AWS API Gateway IP rotation fallback.

    When a direct request fails with 429/403/timeout, retries through
    AWS API Gateway which assigns a new IP per request.

    After 3 consecutive failures for a URL, skips direct attempts
    for 5 minutes and goes straight to AWS rotation.
    """

    def __init__(
        self,
        gateway_id: Optional[str] = None,
        region: Optional[str] = None,
        fallback_enabled: Optional[bool] = None,
        failure_threshold: int = 3,
        cooldown_minutes: int = 5,
    ):
        self.gateway_id = gateway_id or os.getenv('AWS_API_GATEWAY_ID')
        self.region = region or os.getenv('AWS_REGION', 'us-east-1')

        if fallback_enabled is not None:
            self.fallback_enabled = fallback_enabled
        else:
            self.fallback_enabled = os.getenv('USE_AWS_IP_ROTATION_FALLBACK', 'true').lower() == 'true'

        self.failure_count: Dict[str, int] = {}
        self.last_failure: Dict[str, datetime] = {}
        self.failure_threshold = failure_threshold
        self.cooldown_minutes = cooldown_minutes

    def _url_hash(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()

    def _should_skip_direct(self, url: str) -> bool:
        if not self.fallback_enabled or not self.gateway_id:
            return False

        h = self._url_hash(url)
        if h in self.failure_count and self.failure_count[h] >= self.failure_threshold:
            last = self.last_failure.get(h)
            if last and datetime.now() - last < timedelta(minutes=self.cooldown_minutes):
                return True
            else:
                self.failure_count[h] = 0
        return False

    def _record_failure(self, url: str):
        h = self._url_hash(url)
        self.failure_count[h] = self.failure_count.get(h, 0) + 1
        self.last_failure[h] = datetime.now()

    def _record_success(self, url: str):
        h = self._url_hash(url)
        self.failure_count.pop(h, None)
        self.last_failure.pop(h, None)

    def _get_aws_gateway_url(self, original_url: str) -> Optional[str]:
        if not self.gateway_id:
            return None
        encoded_url = quote(original_url, safe='')
        return f"https://{self.gateway_id}.execute-api.{self.region}.amazonaws.com/prod/proxy?url={encoded_url}"

    async def get(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: int = 30,
        return_raw: bool = False,
    ) -> Any:
        """
        GET with automatic AWS fallback.

        Args:
            url: Target URL
            params: Query parameters
            headers: HTTP headers
            timeout: Seconds
            return_raw: If True, return raw text instead of parsed JSON

        Returns:
            Parsed JSON dict (default) or raw text (if return_raw=True)
        """
        full_url = url
        if params:
            sep = '&' if '?' in url else '?'
            full_url = f"{url}{sep}{urlencode(params)}"

        # Try direct first (unless adaptive skip)
        if not self._should_skip_direct(full_url):
            try:
                timeout_obj = aiohttp.ClientTimeout(total=timeout)
                async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                    async with session.get(full_url, headers=headers) as response:
                        if response.status == 200:
                            self._record_success(full_url)
                            return await response.text() if return_raw else await response.json()
                        if response.status in [429, 403]:
                            self._record_failure(full_url)
                        else:
                            response.raise_for_status()
            except (asyncio.TimeoutError, aiohttp.ClientError):
                self._record_failure(full_url)

        # AWS rotation fallback
        if self.fallback_enabled and self.gateway_id:
            aws_url = self._get_aws_gateway_url(full_url)
            if aws_url:
                timeout_obj = aiohttp.ClientTimeout(total=timeout + 10)
                async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                    async with session.get(aws_url, headers=headers) as response:
                        if response.status == 200:
                            return await response.text() if return_raw else await response.json()
                        response.raise_for_status()

        raise aiohttp.ClientError(f"Both direct and AWS rotation failed for {full_url}")

    async def post(
        self,
        url: str,
        json: Optional[Dict] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """POST with automatic AWS fallback."""
        if not self._should_skip_direct(url):
            try:
                timeout_obj = aiohttp.ClientTimeout(total=timeout)
                async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                    async with session.post(url, json=json, data=data, headers=headers) as response:
                        if response.status == 200:
                            self._record_success(url)
                            return await response.json()
                        if response.status in [429, 403]:
                            self._record_failure(url)
                        else:
                            response.raise_for_status()
            except (asyncio.TimeoutError, aiohttp.ClientError):
                self._record_failure(url)

        if self.fallback_enabled and self.gateway_id:
            aws_url = self._get_aws_gateway_url(url)
            if aws_url:
                timeout_obj = aiohttp.ClientTimeout(total=timeout + 10)
                async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                    async with session.post(aws_url, json=json, data=data, headers=headers) as response:
                        if response.status == 200:
                            return await response.json()
                        response.raise_for_status()

        raise aiohttp.ClientError(f"Both direct and AWS rotation failed for POST {url}")


# Global singleton
_aws_client: Optional[AwsHttpClient] = None

def get_aws_http_client(**kwargs) -> AwsHttpClient:
    """Get global AWS HTTP client instance (singleton)."""
    global _aws_client
    if _aws_client is None:
        _aws_client = AwsHttpClient(**kwargs)
    return _aws_client
