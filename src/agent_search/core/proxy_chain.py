"""
Unified Proxy Chain with Automatic Fallback

Combines all proxy methods into a single interface with priority ordering:
1. MacBook Proxy (residential IP via your MacBook)
2. NordVPN SOCKS5 (residential IP via NordVPN)
3. AWS API Gateway IP rotation (datacenter IPs, new IP per request)
4. Direct connection (no proxy)

Each layer falls back to the next on failure.

Usage:
    from agent_search.core import ProxyChain

    chain = ProxyChain()

    # Sync GET
    response = chain.get("https://api.example.com/data")

    # Sync POST
    response = chain.post("https://api.example.com/data", json={"key": "value"})

    # Async GET
    data = await chain.async_get("https://api.example.com/data")

    # Use as requests proxy dict (for libraries that accept proxies={})
    proxies = chain.get_best_proxies_dict()

    # Cleanup
    chain.shutdown()
"""

import os
import logging
import requests
from typing import Optional, Dict, Any, List
from urllib.parse import quote, urlencode

from agent_search.core.nordvpn_proxy import NordVpnProxy
from agent_search.core.aws_ip_rotator import AwsHttpClient

logger = logging.getLogger(__name__)

# Optional async support
try:
    import aiohttp
    import asyncio
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    aiohttp = None
    asyncio = None


class ProxyChain:
    """
    Unified proxy interface with layered fallback.

    Tries proxies in order of preference. If one fails, moves to the next.
    Configurable via environment variables or constructor args.

    Environment Variables:
        # MacBook proxy (run macbook_server.py on your MacBook)
        MACBOOK_PROXY_URL=http://your-macbook-ip:8888
        MACBOOK_API_KEY=your-secret-key

        # NordVPN SOCKS5
        NORDVPN_SERVICE_USER=your-service-user
        NORDVPN_SERVICE_PASS=your-service-pass
        NORDVPN_SERVER=us.socks.nordhold.net

        # AWS API Gateway rotation
        AWS_API_GATEWAY_ID=your-gateway-id
        AWS_REGION=us-east-1

        # AWS for requests-ip-rotator
        AWS_ACCESS_KEY_ID=your-key
        AWS_SECRET_ACCESS_KEY=your-secret
    """

    def __init__(
        self,
        macbook_proxy_url: Optional[str] = None,
        macbook_api_key: Optional[str] = None,
        nordvpn_proxy_url: Optional[str] = None,
        aws_gateway_id: Optional[str] = None,
        aws_region: Optional[str] = None,
        enabled_layers: Optional[List[str]] = None,
        timeout: int = 30,
    ):
        self.macbook_url = macbook_proxy_url or os.getenv('MACBOOK_PROXY_URL')
        self.macbook_key = macbook_api_key or os.getenv('MACBOOK_API_KEY', '')
        self.timeout = timeout

        # Layer availability
        self.enabled_layers = enabled_layers or ['macbook', 'nordvpn', 'aws', 'direct']

        # Initialize NordVPN
        self.nordvpn = NordVpnProxy(proxy_url=nordvpn_proxy_url)

        # Initialize AWS async client
        self.aws_client = AwsHttpClient(
            gateway_id=aws_gateway_id,
            region=aws_region,
        )

        # Gateway session manager (lazy, for sync requests-ip-rotator)
        self._gateway_manager = None

    def _log(self, level: str, msg: str):
        getattr(logger, level)(msg)

    # ========================================================================
    # Sync interface (requests-based)
    # ========================================================================

    def get(self, url: str, **kwargs) -> requests.Response:
        """
        Sync GET through the proxy chain.
        Returns the first successful requests.Response.
        """
        kwargs.setdefault('timeout', self.timeout)
        return self._sync_request('GET', url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        """Sync POST through the proxy chain."""
        kwargs.setdefault('timeout', self.timeout)
        return self._sync_request('POST', url, **kwargs)

    def _sync_request(self, method: str, url: str, **kwargs) -> requests.Response:
        errors = []

        # Layer 1: MacBook proxy
        if 'macbook' in self.enabled_layers and self.macbook_url:
            try:
                resp = self._via_macbook_sync(method, url, **kwargs)
                if resp and resp.status_code == 200:
                    self._log('info', f"[macbook] {method} {url[:60]} -> 200")
                    return resp
            except Exception as e:
                errors.append(f"macbook: {e}")

        # Layer 2: NordVPN SOCKS5
        if 'nordvpn' in self.enabled_layers and self.nordvpn.is_configured:
            try:
                session = self.nordvpn.get_requests_session()
                resp = session.request(method, url, **kwargs)
                if resp.status_code == 200:
                    self._log('info', f"[nordvpn] {method} {url[:60]} -> 200")
                    return resp
                errors.append(f"nordvpn: HTTP {resp.status_code}")
            except Exception as e:
                errors.append(f"nordvpn: {e}")

        # Layer 3: AWS Gateway (via proxies dict approach)
        if 'aws' in self.enabled_layers and self.aws_client.gateway_id:
            try:
                resp = self._via_aws_gateway_sync(method, url, **kwargs)
                if resp and resp.status_code == 200:
                    self._log('info', f"[aws] {method} {url[:60]} -> 200")
                    return resp
            except Exception as e:
                errors.append(f"aws: {e}")

        # Layer 4: Direct
        if 'direct' in self.enabled_layers:
            try:
                resp = requests.request(method, url, **kwargs)
                self._log('info', f"[direct] {method} {url[:60]} -> {resp.status_code}")
                return resp
            except Exception as e:
                errors.append(f"direct: {e}")

        raise ConnectionError(
            f"All proxy layers failed for {method} {url}. Errors: {'; '.join(errors)}"
        )

    def _via_macbook_sync(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """Route through MacBook proxy server."""
        headers = kwargs.pop('headers', {}) or {}
        params = kwargs.pop('params', None)
        json_body = kwargs.pop('json', None)

        proxy_payload = {
            'url': url,
            'method': method,
            'headers': headers,
            'params': params,
            'json_body': json_body,
        }

        return requests.post(
            f"{self.macbook_url}/proxy",
            json=proxy_payload,
            headers={'X-API-Key': self.macbook_key},
            timeout=kwargs.get('timeout', self.timeout),
        )

    def _via_aws_gateway_sync(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """Route through AWS API Gateway URL rewriting."""
        aws_url = self.aws_client._get_aws_gateway_url(url)
        if not aws_url:
            return None

        # Rewrite the URL to go through the gateway
        return requests.request(method, aws_url, **kwargs)

    # ========================================================================
    # Async interface (aiohttp-based)
    # ========================================================================

    async def async_get(self, url: str, **kwargs) -> Any:
        """
        Async GET through the proxy chain.
        Returns parsed JSON from the first successful response.
        """
        kwargs.setdefault('timeout', self.timeout)
        return await self._async_request('GET', url, **kwargs)

    async def async_post(self, url: str, **kwargs) -> Any:
        """Async POST through the proxy chain."""
        kwargs.setdefault('timeout', self.timeout)
        return await self._async_request('POST', url, **kwargs)

    async def _async_request(self, method: str, url: str, **kwargs) -> Any:
        timeout_val = kwargs.pop('timeout', self.timeout)
        errors = []
        return_raw = kwargs.pop('return_raw', False)

        # Layer 1: MacBook proxy (async)
        if 'macbook' in self.enabled_layers and self.macbook_url:
            try:
                result = await self._via_macbook_async(method, url, timeout_val, **kwargs)
                if result is not None:
                    self._log('info', f"[macbook] async {method} {url[:60]} -> OK")
                    return result
            except Exception as e:
                errors.append(f"macbook: {e}")

        # Layer 2: NordVPN SOCKS5 (async via aiohttp-socks)
        if 'nordvpn' in self.enabled_layers and self.nordvpn.is_configured:
            try:
                connector = None
                try:
                    connector = self.nordvpn.get_aiohttp_connector()
                except ImportError:
                    pass

                if connector:
                    timeout_obj = aiohttp.ClientTimeout(total=timeout_val)
                    async with aiohttp.ClientSession(connector=connector, timeout=timeout_obj) as session:
                        req_method = getattr(session, method.lower())
                        async with req_method(url, **kwargs) as resp:
                            if resp.status == 200:
                                self._log('info', f"[nordvpn] async {method} {url[:60]} -> 200")
                                return await resp.text() if return_raw else await resp.json()
                            errors.append(f"nordvpn: HTTP {resp.status}")
            except Exception as e:
                errors.append(f"nordvpn: {e}")

        # Layer 3: AWS Gateway (async via AwsHttpClient)
        if 'aws' in self.enabled_layers and self.aws_client.gateway_id:
            try:
                if method == 'GET':
                    result = await self.aws_client.get(url, timeout=timeout_val, return_raw=return_raw, **kwargs)
                else:
                    result = await self.aws_client.post(url, timeout=timeout_val, **kwargs)
                self._log('info', f"[aws] async {method} {url[:60]} -> OK")
                return result
            except Exception as e:
                errors.append(f"aws: {e}")

        # Layer 4: Direct
        if 'direct' in self.enabled_layers:
            try:
                timeout_obj = aiohttp.ClientTimeout(total=timeout_val)
                async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                    req_method = getattr(session, method.lower())
                    async with req_method(url, **kwargs) as resp:
                        self._log('info', f"[direct] async {method} {url[:60]} -> {resp.status}")
                        return await resp.text() if return_raw else await resp.json()
            except Exception as e:
                errors.append(f"direct: {e}")

        raise ConnectionError(
            f"All proxy layers failed for async {method} {url}. Errors: {'; '.join(errors)}"
        )

    async def _via_macbook_async(self, method: str, url: str, timeout_val: int, **kwargs) -> Optional[Any]:
        """Async request through MacBook proxy."""
        headers = kwargs.pop('headers', {}) or {}
        params = kwargs.pop('params', None)
        json_body = kwargs.pop('json', None)

        proxy_payload = {
            'url': url,
            'method': method,
            'headers': headers,
            'params': params,
            'json_body': json_body,
        }

        timeout_obj = aiohttp.ClientTimeout(total=timeout_val)
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.post(
                f"{self.macbook_url}/proxy",
                json=proxy_payload,
                headers={'X-API-Key': self.macbook_key},
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        return None

    # ========================================================================
    # Utility
    # ========================================================================

    def get_best_proxies_dict(self) -> Dict[str, str]:
        """
        Get the best available proxy as a requests-compatible proxies dict.
        Useful for libraries that accept a proxies={} argument.

        Returns:
            Dict like {'http': 'socks5://...', 'https': 'socks5://...'} or {}
        """
        if 'nordvpn' in self.enabled_layers and self.nordvpn.is_configured:
            return self.nordvpn.get_proxies_dict()
        return {}

    def shutdown(self):
        """Clean up any active gateway sessions."""
        if self._gateway_manager:
            self._gateway_manager.shutdown()
            self._gateway_manager = None
