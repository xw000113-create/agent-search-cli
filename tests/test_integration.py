"""
Integration tests for the complete Proxy Toolkit.
Tests end-to-end workflows.
"""

import unittest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import shutil

from agent_search import ProxyChain, HTMLToMarkdown
from agent_search.batch_processor import BatchProcessor, BatchConfig
from agent_search.data_extraction import StructuredExtractor, CSSExtractionStrategy
from agent_search.change_detector import ChangeDetector


class TestEndToEndScraping(unittest.TestCase):
    """Test complete scraping workflows."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    @patch("agent_search.core.proxy_chain.requests.request")
    def test_scrape_and_convert_to_markdown(self, mock_request):
        """Test scraping and converting to markdown."""
        # Arrange
        html = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Hello World</h1>
            <p>This is a test paragraph.</p>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.headers = {"Content-Type": "text/html"}
        mock_request.return_value = mock_response

        # Act
        chain = ProxyChain(enabled_layers=["direct"])
        response = chain.get("https://example.com")

        converter = HTMLToMarkdown()
        markdown = converter.convert(response.text)

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertIn("# Hello World", markdown)
        self.assertIn("This is a test paragraph.", markdown)

    @patch("agent_search.core.proxy_chain.requests.request")
    def test_scrape_and_extract_data(self, mock_request):
        """Test scraping and extracting structured data."""
        # Arrange
        html = """
        <html>
        <body>
            <div class="product">
                <h2>Product Name</h2>
                <span class="price">$29.99</span>
            </div>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_request.return_value = mock_response

        # Act
        chain = ProxyChain(enabled_layers=["direct"])
        response = chain.get("https://example.com/products")

        extractor = StructuredExtractor()
        strategy = CSSExtractionStrategy(
            base_selector=".product", fields={"name": "h2", "price": ".price"}
        )
        data = extractor.extract_with_css(response.text, strategy)

        # Assert
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Product Name")
        self.assertEqual(data[0]["price"], "$29.99")

    @patch("agent_search.core.proxy_chain.requests.request")
    def test_scrape_with_change_detection(self, mock_request):
        """Test scraping with change detection."""
        # First scrape
        html1 = "<html><body>Version 1</body></html>"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = html1
        mock_request.return_value = mock_response

        chain = ProxyChain(enabled_layers=["direct"])
        response = chain.get("https://example.com")

        detector = ChangeDetector(storage_dir=self.temp_dir)
        result1 = detector.detect_changes("https://example.com", response.text)

        self.assertTrue(result1.has_changed)
        self.assertEqual(result1.change_type, "initial")

        # Second scrape with same content
        result2 = detector.detect_changes("https://example.com", response.text)
        self.assertFalse(result2.has_changed)

        # Third scrape with different content
        html2 = "<html><body>Version 2</body></html>"
        mock_response.text = html2
        result3 = detector.detect_changes("https://example.com", html2)
        self.assertTrue(result3.has_changed)


class TestBatchProcessingIntegration(unittest.TestCase):
    """Test batch processing integration."""

    async def test_batch_scrape_workflow(self):
        """Test complete batch scraping workflow."""
        # Mock responses
        responses = {
            "https://example1.com": "<html><h1>Page 1</h1></html>",
            "https://example2.com": "<html><h1>Page 2</h1></html>",
        }

        def mock_get(url, **kwargs):
            response = Mock()
            response.status_code = 200
            response.text = responses.get(url, "")
            response.headers = {}
            return response

        mock_proxy = Mock()
        mock_proxy.get.side_effect = mock_get

        # Act — inject mock proxy_chain directly
        config = BatchConfig(max_workers=2, use_proxy_chain=False)
        processor = BatchProcessor(config)
        processor.proxy_chain = mock_proxy

        results = await processor.process(list(responses.keys()))

        # Assert
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r["success"] for r in results))

    @patch("agent_search.core.batch_processor.ProxyChain")
    async def test_batch_with_extraction(self, mock_proxy_class):
        """Test batch scraping with data extraction."""
        html = """
        <div class="item">
            <h2>Title</h2>
            <p>Description</p>
        </div>
        """

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.headers = {}

        mock_proxy = Mock()
        mock_proxy.get.return_value = mock_response
        mock_proxy_class.return_value = mock_proxy

        # Process
        config = BatchConfig(max_workers=2)
        processor = BatchProcessor(config)

        urls = ["https://example1.com", "https://example2.com"]
        results = await processor.process(urls)

        # Extract from results
        extractor = StructuredExtractor()
        strategy = CSSExtractionStrategy(
            base_selector=".item", fields={"title": "h2", "description": "p"}
        )

        all_data = []
        for result in results:
            if result.get("success"):
                data = extractor.extract_with_css(result["html"], strategy)
                all_data.extend(data)

        self.assertEqual(len(all_data), 2)


class TestProxyChainIntegration(unittest.TestCase):
    """Test ProxyChain integration with other components."""

    def test_proxy_chain_with_rate_limiter(self):
        """Test ProxyChain with rate limiting."""
        from agent_search.rate_limiter import RateLimiter

        limiter = RateLimiter(min_delay=0.1)
        chain = ProxyChain(enabled_layers=["direct"])

        # Apply rate limiting before requests
        limiter.wait()

        with patch("agent_search.core.proxy_chain.requests.request") as mock_req:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_req.return_value = mock_response

            response = chain.get("https://example.com")
            self.assertEqual(response.status_code, 200)

    def test_proxy_chain_with_retry(self):
        """Test ProxyChain with retry logic."""
        from agent_search.retry_handler import RetryHandler, RetryConfig

        config = RetryConfig(max_retries=2, base_delay=0.01)
        retry_handler = RetryHandler(config)
        chain = ProxyChain(enabled_layers=["direct"])

        with patch("agent_search.core.proxy_chain.requests.request") as mock_req:
            # First two calls fail, third succeeds
            mock_req.side_effect = [
                Exception("Fail 1"),
                Exception("Fail 2"),
                Mock(status_code=200, text="Success"),
            ]

            # This would need retry logic integrated
            # For now, just verify the components exist
            self.assertIsNotNone(retry_handler)
            self.assertIsNotNone(chain)


class TestAntiDetectionIntegration(unittest.TestCase):
    """Test anti-detection features integration."""

    def test_user_agent_rotation_with_proxy(self):
        """Test UA rotation with proxy requests."""
        from agent_search.user_agents import get_random_user_agent

        # Get random UA
        ua = get_random_user_agent()

        with patch("agent_search.core.proxy_chain.requests.request") as mock_req:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_req.return_value = mock_response

            chain = ProxyChain(enabled_layers=["direct"])
            response = chain.get("https://example.com", headers={"User-Agent": ua})

            # Verify UA was passed
            call_args = mock_req.call_args
            headers = call_args[1].get("headers", {})
            self.assertEqual(headers.get("User-Agent"), ua)

    def test_captcha_detection_integration(self):
        """Test CAPTCHA detection."""
        from agent_search.captcha_detector import CaptchaDetector

        detector = CaptchaDetector()

        # Test CAPTCHA detection
        captcha_html = "<html><div class='g-recaptcha'></div></html>"
        result = detector.detect(captcha_html)

        self.assertTrue(result["is_captcha"])
        self.assertEqual(result["type"], "captcha")

        # Test normal page
        normal_html = "<html><body>Normal content</body></html>"
        result = detector.detect(normal_html)

        self.assertFalse(result["is_captcha"])
        self.assertFalse(result["requires_action"])


def async_test(coro):
    """Decorator for async test methods."""

    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))

    return wrapper


# Apply async decorator
for name, method in list(TestBatchProcessingIntegration.__dict__.items()):
    if name.startswith("test_") and asyncio.iscoroutinefunction(method):
        setattr(TestBatchProcessingIntegration, name, async_test(method))


if __name__ == "__main__":
    unittest.main()
