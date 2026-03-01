"""
Tests for batch processing and crawling.
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from agent_search.batch_processor import (
    BatchProcessor,
    BatchConfig,
    Crawler,
    process_urls,
)


class TestBatchConfig(unittest.TestCase):
    """Test BatchConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = BatchConfig()

        self.assertEqual(config.max_workers, 10)
        self.assertEqual(config.requests_per_second, 5.0)
        self.assertEqual(config.max_retries, 3)
        self.assertFalse(config.use_browser)

    def test_custom_config(self):
        """Test custom configuration."""
        config = BatchConfig(max_workers=20, requests_per_second=10.0, use_browser=True)

        self.assertEqual(config.max_workers, 20)
        self.assertEqual(config.requests_per_second, 10.0)
        self.assertTrue(config.use_browser)


class TestBatchProcessor(unittest.TestCase):
    """Test BatchProcessor."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = BatchConfig(
            max_workers=2,
            use_proxy_chain=False,  # Don't use real proxy
        )
        self.processor = BatchProcessor(self.config)

    async def test_process_single_url(self):
        """Test processing a single URL."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>Test</html>"
        mock_response.headers = {"Content-Type": "text/html"}

        mock_proxy = Mock()
        mock_proxy.get.return_value = mock_response

        # Inject mock proxy_chain directly (setUp creates processor with proxy_chain=None)
        self.processor.proxy_chain = mock_proxy

        # Test
        results = await self.processor.process(["https://example.com"])

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["success"])
        self.assertEqual(results[0]["url"], "https://example.com")

    async def test_process_multiple_urls(self):
        """Test processing multiple URLs."""

        # Mock responses
        def mock_get(url, **kwargs):
            response = Mock()
            response.status_code = 200
            response.text = f"<html>{url}</html>"
            response.headers = {}
            return response

        mock_proxy = Mock()
        mock_proxy.get.side_effect = mock_get

        # Inject mock proxy_chain directly
        self.processor.proxy_chain = mock_proxy

        urls = ["https://example1.com", "https://example2.com"]
        results = await self.processor.process(urls)

        self.assertEqual(len(results), 2)
        self.assertTrue(all(r["success"] for r in results))

    @patch("agent_search.core.batch_processor.ProxyChain")
    async def test_process_with_error(self, mock_proxy_class):
        """Test handling errors."""
        # Mock to raise exception
        mock_proxy = Mock()
        mock_proxy.get.side_effect = Exception("Connection failed")
        mock_proxy_class.return_value = mock_proxy

        results = await self.processor.process(["https://example.com"])

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]["success"])
        self.assertIn("error", results[0])

    async def test_progress_callback(self):
        """Test progress callback."""
        progress_calls = []

        def on_progress(total, completed):
            progress_calls.append((total, completed))

        with patch("agent_search.core.batch_processor.ProxyChain") as mock_proxy_class:
            mock_proxy = Mock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "test"
            mock_response.headers = {}
            mock_proxy.get.return_value = mock_response
            mock_proxy_class.return_value = mock_proxy

            urls = ["https://example1.com", "https://example2.com"]
            await self.processor.process(urls, on_progress=on_progress)

            self.assertGreater(len(progress_calls), 0)


class TestCrawler(unittest.TestCase):
    """Test Crawler."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = BatchConfig(max_workers=2)
        self.crawler = Crawler(max_depth=2, same_domain_only=True)

    @patch("agent_search.core.batch_processor.Crawler._extract_links")
    async def test_crawl_single_page(self, mock_extract):
        """Test crawling a single page."""
        # Mock response — headers must be a real dict (dict(Mock()) raises TypeError
        # which is silently caught by _default_processor, yielding success=False)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>Test</html>"
        mock_response.headers = {"Content-Type": "text/html"}

        mock_proxy = Mock()
        mock_proxy.get.return_value = mock_response

        # Inject mock proxy_chain directly into the crawler's processor
        self.crawler.processor.proxy_chain = mock_proxy

        # Mock no links found
        mock_extract.return_value = []

        pages = await self.crawler.crawl("https://example.com")

        self.assertEqual(len(pages), 1)

    def test_extract_links(self):
        """Test extracting links from HTML."""
        html = """
        <html>
        <body>
            <a href="/page1">Page 1</a>
            <a href="https://example.com/page2">Page 2</a>
            <a href="https://other.com/page">External</a>
            <a href="#anchor">Anchor</a>
        </body>
        </html>
        """

        links = self.crawler._extract_links(html, "https://example.com", "example.com")

        # Should only get same-domain links
        self.assertEqual(len(links), 2)
        self.assertIn("https://example.com/page1", links)
        self.assertIn("https://example.com/page2", links)

    def test_extract_links_relative(self):
        """Test extracting relative links."""
        html = '<a href="/about">About</a>'

        links = self.crawler._extract_links(html, "https://example.com", "example.com")

        self.assertEqual(len(links), 1)
        self.assertEqual(links[0], "https://example.com/about")


class TestProcessUrls(unittest.TestCase):
    """Test process_urls convenience function."""

    @patch("agent_search.core.batch_processor.ProxyChain")
    async def test_process_urls(self, mock_proxy_class):
        """Test quick URL processing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>Test</html>"
        mock_response.headers = {}

        mock_proxy = Mock()
        mock_proxy.get.return_value = mock_response
        mock_proxy_class.return_value = mock_proxy

        results = await process_urls(
            ["https://example1.com", "https://example2.com"], max_workers=2
        )

        self.assertEqual(len(results), 2)


def async_test(coro):
    """Decorator for async test methods."""

    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))

    return wrapper


# Apply async decorator to async methods
for name, method in list(TestBatchProcessor.__dict__.items()):
    if name.startswith("test_") and asyncio.iscoroutinefunction(method):
        setattr(TestBatchProcessor, name, async_test(method))

for name, method in list(TestCrawler.__dict__.items()):
    if name.startswith("test_") and asyncio.iscoroutinefunction(method):
        setattr(TestCrawler, name, async_test(method))

for name, method in list(TestProcessUrls.__dict__.items()):
    if name.startswith("test_") and asyncio.iscoroutinefunction(method):
        setattr(TestProcessUrls, name, async_test(method))


if __name__ == "__main__":
    unittest.main()
