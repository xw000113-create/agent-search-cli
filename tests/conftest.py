"""
Pytest configuration and fixtures for Proxy Toolkit tests.
"""

import pytest
import tempfile
import shutil
from unittest.mock import Mock

# Import toolkit components
from agent_search import ProxyChain
from agent_search.rate_limiter import RateLimiter
from agent_search.retry_handler import RetryHandler, RetryConfig


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests."""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp)


@pytest.fixture
def mock_proxy_response():
    """Provide a mock proxy response."""

    def create_response(status_code=200, text="", headers=None):
        response = Mock()
        response.status_code = status_code
        response.text = text
        response.headers = headers or {}
        return response

    return create_response


@pytest.fixture
def proxy_chain_direct():
    """Provide a ProxyChain configured for direct requests only."""
    return ProxyChain(enabled_layers=["direct"])


@pytest.fixture
def rate_limiter_fast():
    """Provide a RateLimiter with fast settings for tests."""
    return RateLimiter(min_delay=0.01, max_delay=0.05, burst_size=5)


@pytest.fixture
def retry_handler_fast():
    """Provide a RetryHandler with fast settings for tests."""
    config = RetryConfig(
        max_retries=2,
        base_delay=0.01,
        max_delay=0.1,
        jitter=False,  # Disable jitter for deterministic tests
    )
    return RetryHandler(config)


@pytest.fixture
def sample_html():
    """Provide sample HTML for tests."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <meta name="description" content="Test description">
    </head>
    <body>
        <h1>Test Heading</h1>
        <p>This is a test paragraph.</p>
        <a href="https://example.com">Example Link</a>
        <img src="test.jpg" alt="Test Image">
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        <table>
            <tr><th>Name</th><th>Value</th></tr>
            <tr><td>Test</td><td>123</td></tr>
        </table>
    </body>
    </html>
    """


@pytest.fixture
def sample_html_with_script():
    """Provide sample HTML with scripts."""
    return """
    <html>
    <head>
        <script>alert('test');</script>
        <style>body { color: red; }</style>
    </head>
    <body>
        <p>Content</p>
    </body>
    </html>
    """


@pytest.fixture
def sample_product_html():
    """Provide sample product HTML for extraction tests."""
    return """
    <div class="products">
        <div class="product">
            <h2 class="name">Product 1</h2>
            <span class="price">$19.99</span>
            <p class="description">Description 1</p>
        </div>
        <div class="product">
            <h2 class="name">Product 2</h2>
            <span class="price">$29.99</span>
            <p class="description">Description 2</p>
        </div>
    </div>
    """


@pytest.fixture
def sample_sitemap():
    """Provide sample sitemap XML."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>https://example.com/page1</loc>
            <lastmod>2024-01-01</lastmod>
            <changefreq>daily</changefreq>
        </url>
        <url>
            <loc>https://example.com/page2</loc>
            <lastmod>2024-01-02</lastmod>
        </url>
    </urlset>
    """


@pytest.fixture
def sample_robots_txt():
    """Provide sample robots.txt."""
    return """
    User-agent: *
    Allow: /
    Disallow: /private/
    
    Sitemap: https://example.com/sitemap.xml
    """


@pytest.fixture(autouse=True)
def mock_sleep(monkeypatch):
    """Automatically mock time.sleep in tests to speed them up."""
    import time

    original_sleep = time.sleep

    def fast_sleep(seconds):
        # Cap sleep at 0.01 seconds for tests
        original_sleep(min(seconds, 0.01))

    monkeypatch.setattr(time, "sleep", fast_sleep)


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Markers for different test types
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow")
    config.addinivalue_line(
        "markers", "requires_network: mark test as requiring network"
    )
    config.addinivalue_line(
        "markers", "requires_browser: mark test as requiring Playwright browser"
    )


# Skip markers
def pytest_collection_modifyitems(config, items):
    """Modify test collection based on markers."""
    skip_slow = pytest.mark.skip(reason="slow test skipped — run with --run-slow")
    skip_network = pytest.mark.skip(
        reason="network test skipped — run with --run-network"
    )

    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
