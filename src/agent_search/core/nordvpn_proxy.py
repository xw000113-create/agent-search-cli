"""
NordVPN SOCKS5 Proxy Integration

Provides SOCKS5 proxy configuration for both requests and aiohttp/httpx.

Environment Variables:
    NORDVPN_SERVICE_USER: NordVPN service account username
    NORDVPN_SERVICE_PASS: NordVPN service account password
    NORDVPN_SERVER: SOCKS5 server (default: us.socks.nordhold.net)
    NORDVPN_PROXY_URL: Full override URL (optional, takes precedence)

Dependencies:
    pip install httpx[socks] requests[socks] python-socks[asyncio] aiohttp-socks
"""

import os
import requests
from typing import Optional, Dict

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    from aiohttp_socks import ProxyConnector
    HAS_AIOHTTP_SOCKS = True
except ImportError:
    HAS_AIOHTTP_SOCKS = False


class NordVpnProxy:
    """
    NordVPN SOCKS5 proxy configuration.

    Usage:
        proxy = NordVpnProxy()

        # For requests library:
        session = proxy.get_requests_session()
        response = session.get("https://example.com")

        # For httpx:
        async with proxy.get_httpx_client() as client:
            response = await client.get("https://example.com")

        # Just the proxy dict (for requests):
        proxies = proxy.get_proxies_dict()
        requests.get("https://example.com", proxies=proxies)
    """

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        proxy_url: Optional[str] = None,
    ):
        self.proxy_url = proxy_url or os.getenv('NORDVPN_PROXY_URL')

        if not self.proxy_url:
            self.username = username or os.getenv('NORDVPN_SERVICE_USER')
            self.password = password or os.getenv('NORDVPN_SERVICE_PASS')
            self.server = server or os.getenv('NORDVPN_SERVER', 'us.socks.nordhold.net')

            if self.username and self.password:
                self.proxy_url = f"socks5://{self.username}:{self.password}@{self.server}:1080"

    @property
    def is_configured(self) -> bool:
        return self.proxy_url is not None

    def get_proxies_dict(self) -> Dict[str, str]:
        """Get proxy dict for requests library."""
        if not self.proxy_url:
            return {}
        return {
            'http': self.proxy_url,
            'https': self.proxy_url,
        }

    def get_requests_session(self) -> requests.Session:
        """Get a requests.Session configured with SOCKS5 proxy."""
        session = requests.Session()
        if self.proxy_url:
            session.proxies.update(self.get_proxies_dict())
        return session

    def get_httpx_client(self, **kwargs) -> 'httpx.AsyncClient':
        """Get an httpx.AsyncClient configured with SOCKS5 proxy."""
        if not HAS_HTTPX:
            raise ImportError("httpx not installed. Run: pip install httpx[socks]")

        transport = None
        if self.proxy_url:
            transport = httpx.AsyncHTTPTransport(proxy=self.proxy_url)

        return httpx.AsyncClient(transport=transport, **kwargs)

    def get_aiohttp_connector(self) -> Optional['ProxyConnector']:
        """Get an aiohttp ProxyConnector for use with aiohttp.ClientSession."""
        if not HAS_AIOHTTP_SOCKS:
            raise ImportError("aiohttp-socks not installed. Run: pip install aiohttp-socks")
        if not self.proxy_url:
            return None
        return ProxyConnector.from_url(self.proxy_url)


def get_nordvpn_proxy_url() -> Optional[str]:
    """Get NordVPN SOCKS5 proxy URL from environment, or None if not configured."""
    url = os.getenv('NORDVPN_PROXY_URL')
    if url:
        return url

    user = os.getenv('NORDVPN_SERVICE_USER')
    pwd = os.getenv('NORDVPN_SERVICE_PASS')
    server = os.getenv('NORDVPN_SERVER', 'us.socks.nordhold.net')

    if user and pwd:
        return f"socks5://{user}:{pwd}@{server}:1080"
    return None


def get_nordvpn_session() -> requests.Session:
    """Convenience: get a requests.Session with NordVPN SOCKS5 proxy."""
    proxy = NordVpnProxy()
    return proxy.get_requests_session()
