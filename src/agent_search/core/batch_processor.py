"""
Batch Processing and Parallel Execution

Process multiple URLs in parallel with rate limiting and retry logic.

Usage:
    from agent_search.core.batch_processor import BatchProcessor, BatchConfig

    config = BatchConfig(
        max_workers=10,
        requests_per_second=5,
        max_retries=3
    )

    processor = BatchProcessor(config)

    # Process URLs
    results = await processor.process([
        "https://example.com/page1",
        "https://example.com/page2",
    ])

    # With custom processing
    async def custom_fetch(url):
        # Custom logic
        return {"url": url, "data": ...}

    results = await processor.process(urls, processor=custom_fetch)
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable, Coroutine
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import time

from .proxy_chain import ProxyChain
from .rate_limiter import RateLimiter
from .retry_handler import RetryHandler, RetryConfig


@dataclass
class BatchConfig:
    """Configuration for batch processing."""

    max_workers: int = 10
    requests_per_second: float = 5.0
    max_retries: int = 3
    timeout: int = 30
    use_proxy_chain: bool = True
    use_browser: bool = False  # Use Playwright for JS rendering


class BatchProcessor:
    """
    Process multiple URLs in parallel with rate limiting.

    Features:
    - Parallel execution with worker pool
    - Rate limiting (requests per second)
    - Automatic retry with exponential backoff
    - Progress tracking
    - Error handling
    """

    def __init__(
        self,
        config: Optional[BatchConfig] = None,
        proxy_chain: Optional[ProxyChain] = None,
    ):
        self.config = config or BatchConfig()
        self.proxy_chain = (
            proxy_chain or ProxyChain() if self.config.use_proxy_chain else None
        )

        # Rate limiter
        self.rate_limiter = RateLimiter(
            min_delay=1.0 / self.config.requests_per_second, max_delay=5.0
        )

        # Retry handler
        self.retry_handler = RetryHandler(
            RetryConfig(
                max_retries=self.config.max_retries,
                retry_on_status_codes=[429, 503, 504, 502, 500, 408],
            )
        )

        # Browser pool (optional)
        self._browser_pool = None
        if self.config.use_browser:
            from .playwright_browser import BrowserPool, BrowserConfig

            self._browser_pool = BrowserPool(
                max_browsers=min(self.config.max_workers, 5),
                config=BrowserConfig(headless=True),
            )

    async def start(self):
        """Initialize the processor."""
        if self._browser_pool:
            await self._browser_pool.start()

    async def process(
        self,
        urls: List[str],
        processor: Optional[
            Callable[[str], Coroutine[Any, Any, Dict[str, Any]]]
        ] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Process multiple URLs in parallel.

        Args:
            urls: List of URLs to process
            processor: Custom processor function (optional)
            on_progress: Callback(total, completed) for progress updates

        Returns:
            List of results
        """
        if processor is None:
            processor = self._default_processor

        # Use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.config.max_workers)

        async def process_with_limit(url: str) -> Dict[str, Any]:
            async with semaphore:
                return await self._process_single(url, processor)

        # Process all URLs
        tasks = [process_with_limit(url) for url in urls]

        # Track progress
        results = []
        total = len(urls)
        completed = 0

        for task in asyncio.as_completed(tasks):
            result = await task
            results.append(result)
            completed += 1

            if on_progress:
                on_progress(total, completed)

        return results

    async def _process_single(
        self, url: str, processor: Callable[[str], Coroutine[Any, Any, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Process a single URL with rate limiting and retry."""
        # Wait for rate limit
        self.rate_limiter.wait()

        try:
            # Execute with retry
            result = await self.retry_handler.execute(lambda: processor(url))
            return result
        except Exception as e:
            return {"url": url, "success": False, "error": str(e), "data": None}

    async def _default_processor(self, url: str) -> Dict[str, Any]:
        """Default processor that fetches HTML."""
        if self.config.use_browser and self._browser_pool:
            # Use browser for JS rendering
            result = await self._browser_pool.fetch(url)
            return {
                "url": url,
                "success": result.get("success", False),
                "html": result.get("html", ""),
                "metadata": result.get("metadata", {}),
                "error": result.get("error"),
            }
        else:
            # Use proxy chain
            try:
                response = self.proxy_chain.get(url, timeout=self.config.timeout)
                return {
                    "url": url,
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "html": response.text if response.status_code == 200 else "",
                    "headers": dict(response.headers),
                    "error": None,
                }
            except Exception as e:
                return {"url": url, "success": False, "error": str(e), "html": ""}

    async def close(self):
        """Clean up resources."""
        if self._browser_pool:
            await self._browser_pool.close()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class Crawler:
    """
    Website crawler with depth control and URL discovery.

    Similar to Firecrawl's crawl functionality.
    """

    def __init__(
        self,
        config: Optional[BatchConfig] = None,
        max_depth: int = 3,
        same_domain_only: bool = True,
    ):
        self.config = config or BatchConfig()
        self.max_depth = max_depth
        self.same_domain_only = same_domain_only
        self.processor = BatchProcessor(self.config)
        self.visited = set()

    async def crawl(
        self, start_url: str, on_page: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Crawl a website starting from a URL.

        Args:
            start_url: Starting URL
            on_page: Callback for each page crawled

        Returns:
            List of crawled pages
        """
        from urllib.parse import urlparse

        await self.processor.start()

        base_domain = urlparse(start_url).netloc
        results = []

        # BFS crawl
        to_crawl = [(start_url, 0)]  # (url, depth)

        while to_crawl:
            # Get batch of URLs at same depth
            current_depth = to_crawl[0][1]
            batch = []

            while to_crawl and to_crawl[0][1] == current_depth:
                url, depth = to_crawl.pop(0)
                if url not in self.visited and depth <= self.max_depth:
                    batch.append((url, depth))

            if not batch:
                continue

            # Process batch
            urls = [url for url, _ in batch]
            pages = await self.processor.process(urls)

            for page in pages:
                if page.get("success"):
                    self.visited.add(page["url"])
                    results.append(page)

                    if on_page:
                        on_page(page)

                    # Find links for next level
                    if current_depth < self.max_depth:
                        links = self._extract_links(
                            page.get("html", ""),
                            page["url"],
                            base_domain if self.same_domain_only else None,
                        )
                        for link in links:
                            if link not in self.visited:
                                to_crawl.append((link, current_depth + 1))

        await self.processor.close()
        return results

    def _extract_links(
        self, html: str, base_url: str, restrict_domain: Optional[str] = None
    ) -> List[str]:
        """Extract links from HTML."""
        from urllib.parse import urljoin, urlparse

        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return []

        soup = BeautifulSoup(html, "html.parser")
        links = []

        for a in soup.find_all("a", href=True):
            href = a["href"]

            # Skip anchors and javascript
            if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            # Resolve URL
            full_url = urljoin(base_url, href)

            # Check domain restriction
            if restrict_domain:
                domain = urlparse(full_url).netloc
                if domain != restrict_domain:
                    continue

            links.append(full_url)

        return links


# Convenience functions
async def process_urls(
    urls: List[str], max_workers: int = 10, use_browser: bool = False
) -> List[Dict[str, Any]]:
    """
    Quick batch processing of URLs.

    Args:
        urls: URLs to process
        max_workers: Number of parallel workers
        use_browser: Use browser rendering

    Returns:
        List of results
    """
    config = BatchConfig(max_workers=max_workers, use_browser=use_browser)
    async with BatchProcessor(config) as processor:
        return await processor.process(urls)


async def crawl_website(
    start_url: str, max_depth: int = 3, max_pages: int = 50
) -> List[Dict[str, Any]]:
    """
    Quick website crawl.

    Args:
        start_url: Starting URL
        max_depth: Maximum crawl depth
        max_pages: Maximum pages to crawl

    Returns:
        List of crawled pages
    """
    crawler = Crawler(max_depth=max_depth)
    results = await crawler.crawl(start_url)
    return results[:max_pages]
