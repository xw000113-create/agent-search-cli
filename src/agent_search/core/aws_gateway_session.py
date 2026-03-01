"""
Sync AWS API Gateway IP Rotation via requests-ip-rotator

Creates a requests.Session that automatically rotates IPs through
AWS API Gateway endpoints across multiple regions.

Each request gets a different IP address from AWS's IP pool.
Supports mounting on any target domain.

Environment Variables:
    AWS_ACCESS_KEY_ID: AWS credentials
    AWS_SECRET_ACCESS_KEY: AWS credentials

Dependencies:
    pip install requests-ip-rotator boto3
"""

import os
import requests
import atexit
from typing import Optional, List

try:
    from requests_ip_rotator import ApiGateway
    HAS_IP_ROTATOR = True
except ImportError:
    HAS_IP_ROTATOR = False

DEFAULT_REGIONS = [
    "us-east-1", "us-west-2", "eu-west-1", "ap-northeast-1",
    "ap-southeast-1", "ap-southeast-2", "sa-east-1", "ca-central-1",
]


class GatewaySessionManager:
    """
    Manages AWS API Gateway sessions for IP rotation.

    Creates API Gateway endpoints in multiple AWS regions and routes
    requests through them, getting a new IP per request.

    Usage:
        manager = GatewaySessionManager("https://api.example.com")
        session = manager.get_session()
        response = session.get("https://api.example.com/data")
        # ... when done:
        manager.shutdown()
    """

    def __init__(
        self,
        target_url: str,
        regions: Optional[List[str]] = None,
        access_key_id: Optional[str] = None,
        access_key_secret: Optional[str] = None,
    ):
        if not HAS_IP_ROTATOR:
            raise ImportError(
                "requests-ip-rotator not installed. "
                "Run: pip install requests-ip-rotator boto3"
            )

        self.target_url = target_url
        self.regions = regions or DEFAULT_REGIONS
        self.access_key_id = access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
        self.access_key_secret = access_key_secret or os.getenv('AWS_SECRET_ACCESS_KEY')
        self.gateway: Optional[ApiGateway] = None
        self._session: Optional[requests.Session] = None

    def start(self) -> 'GatewaySessionManager':
        """Start the API Gateway (creates endpoints in AWS regions)."""
        self.gateway = ApiGateway(
            self.target_url,
            access_key_id=self.access_key_id,
            access_key_secret=self.access_key_secret,
            regions=self.regions,
        )
        self.gateway.start()
        atexit.register(self.shutdown)
        return self

    def get_session(self) -> requests.Session:
        """Get a requests.Session mounted with the IP-rotating gateway."""
        if self.gateway is None:
            self.start()
        if self._session is None:
            self._session = requests.Session()
            self._session.mount(self.target_url, self.gateway)
        return self._session

    def shutdown(self):
        """Shutdown gateway (cleans up AWS API Gateway resources)."""
        if self.gateway:
            try:
                self.gateway.shutdown()
            except Exception:
                pass
            self.gateway = None
            self._session = None


def create_gateway_session(
    target_url: str,
    regions: Optional[List[str]] = None,
    access_key_id: Optional[str] = None,
    access_key_secret: Optional[str] = None,
) -> requests.Session:
    """
    One-liner to create an IP-rotating requests.Session.

    WARNING: You must call manager.shutdown() when done, or the AWS
    API Gateway endpoints will remain active (and incur costs).
    For automatic cleanup, use GatewaySessionManager as a context.

    Args:
        target_url: Base URL to rotate IPs for (e.g. "https://api.example.com")
        regions: AWS regions to use (default: 8 regions worldwide)
        access_key_id: AWS key (default: from AWS_ACCESS_KEY_ID env var)
        access_key_secret: AWS secret (default: from AWS_SECRET_ACCESS_KEY env var)

    Returns:
        requests.Session with IP rotation mounted for target_url
    """
    manager = GatewaySessionManager(
        target_url,
        regions=regions,
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
    )
    return manager.start().get_session()
