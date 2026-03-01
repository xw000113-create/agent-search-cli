"""
Tests for ProxyChain and proxy modules.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import requests

from agent_search.proxy_chain import ProxyChain
from agent_search.nordvpn_proxy import NordVpnProxy
from agent_search.aws_ip_rotator import AwsHttpClient


class TestProxyChain(unittest.TestCase):
    """Test the unified ProxyChain interface."""

    def setUp(self):
        """Set up test fixtures."""
        self.chain = ProxyChain(
            enabled_layers=["direct"]  # Only use direct for testing
        )

    @patch("agent_search.core.proxy_chain.requests.request")
    def test_direct_request_success(self, mock_request):
        """Test direct HTTP request."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_request.return_value = mock_response

        # Act
        response = self.chain.get("https://example.com")

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "Success")

    @patch("agent_search.core.proxy_chain.requests.request")
    def test_direct_request_failure(self, mock_request):
        """Test request failure."""
        # Arrange
        mock_request.side_effect = requests.ConnectionError("Connection failed")

        # Act & Assert
        with self.assertRaises(ConnectionError):
            self.chain.get("https://example.com")

    def test_proxy_chain_initialization(self):
        """Test ProxyChain initialization."""
        chain = ProxyChain()

        self.assertIsNotNone(chain)
        self.assertEqual(chain.timeout, 30)
        self.assertIn("direct", chain.enabled_layers)

    def test_get_best_proxies_dict(self):
        """Test getting best proxy dict."""
        chain = ProxyChain()
        proxies = chain.get_best_proxies_dict()

        # Should return empty dict when no NordVPN configured
        self.assertIsInstance(proxies, dict)


class TestNordVpnProxy(unittest.TestCase):
    """Test NordVPN SOCKS5 proxy."""

    def setUp(self):
        """Set up test fixtures."""
        self.proxy = NordVpnProxy(
            username="test_user", password="test_pass", server="us.socks.nordhold.net"
        )

    def test_proxy_url_construction(self):
        """Test proxy URL construction."""
        expected = "socks5://test_user:test_pass@us.socks.nordhold.net:1080"
        self.assertEqual(self.proxy.proxy_url, expected)

    def test_is_configured(self):
        """Test configuration detection."""
        self.assertTrue(self.proxy.is_configured)

        empty_proxy = NordVpnProxy()
        self.assertFalse(empty_proxy.is_configured)

    def test_get_proxies_dict(self):
        """Test getting proxies dict."""
        proxies = self.proxy.get_proxies_dict()

        expected_url = "socks5://test_user:test_pass@us.socks.nordhold.net:1080"
        self.assertEqual(proxies["http"], expected_url)
        self.assertEqual(proxies["https"], expected_url)

    @patch("agent_search.core.nordvpn_proxy.requests.Session")
    def test_get_requests_session(self, mock_session_class):
        """Test getting requests session."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        session = self.proxy.get_requests_session()

        # Verify proxies were set
        mock_session.proxies.update.assert_called_once()


class TestAwsHttpClient(unittest.TestCase):
    """Test AWS IP Rotator."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = AwsHttpClient(gateway_id="test-gateway", region="us-east-1")

    def test_get_aws_gateway_url(self):
        """Test AWS Gateway URL generation."""
        original_url = "https://example.com/api/data"
        aws_url = self.client._get_aws_gateway_url(original_url)

        expected = (
            "https://test-gateway.execute-api.us-east-1.amazonaws.com/prod/proxy?"
            "url=https%3A%2F%2Fexample.com%2Fapi%2Fdata"
        )
        self.assertEqual(aws_url, expected)

    def test_should_skip_direct_initial(self):
        """Test that direct requests are allowed initially."""
        should_skip = self.client._should_skip_direct("https://example.com")
        self.assertFalse(should_skip)

    def test_record_failure(self):
        """Test failure recording."""
        url = "https://example.com"

        # Record multiple failures
        for _ in range(3):
            self.client._record_failure(url)

        # Should skip direct after threshold
        should_skip = self.client._should_skip_direct(url)
        self.assertTrue(should_skip)

    def test_record_success_resets_failure(self):
        """Test that success resets failure count."""
        url = "https://example.com"

        # Record failures
        for _ in range(3):
            self.client._record_failure(url)

        # Record success
        self.client._record_success(url)

        # Should not skip after success
        should_skip = self.client._should_skip_direct(url)
        self.assertFalse(should_skip)

    def test_url_hashing(self):
        """Test URL hashing for failure tracking."""
        url1 = "https://example.com"
        url2 = "https://example.com"

        hash1 = self.client._url_hash(url1)
        hash2 = self.client._url_hash(url2)

        self.assertEqual(hash1, hash2)


class TestProxyChainLayerFallback(unittest.TestCase):
    """Test proxy layer fallback logic."""

    @patch("agent_search.core.proxy_chain.requests.request")
    def test_fallback_to_direct(self, mock_request):
        """Test that direct layer works as the fallback when it's the only enabled layer.

        With enabled_layers=["direct"], ProxyChain tries the direct layer once.
        There is no intra-layer retry — each layer is attempted a single time.
        """
        mock_request.return_value = Mock(status_code=200, text="Success")

        chain = ProxyChain(enabled_layers=["direct"])
        response = chain.get("https://example.com")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "Success")
        mock_request.assert_called_once()

    @patch("agent_search.core.proxy_chain.requests.request")
    def test_direct_only_raises_on_failure(self, mock_request):
        """Test that ConnectionError propagates when the only layer fails."""
        mock_request.side_effect = requests.ConnectionError("Failed")

        chain = ProxyChain(enabled_layers=["direct"])
        with self.assertRaises(ConnectionError):
            chain.get("https://example.com")


if __name__ == "__main__":
    unittest.main()
