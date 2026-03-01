"""
Playwright Browser Integration

JavaScript rendering support using Playwright.
Handles dynamic content, SPAs, and JavaScript-rendered pages.

Usage:
    from agent_search.core.playwright_browser import PlaywrightBrowser, BrowserPool

    # Single browser instance
    browser = PlaywrightBrowser()
    await browser.start()

    html = await browser.fetch(
        "https://example.com",
        wait_for=".content",  # Wait for element
        actions=["scroll"]     # Perform actions
    )

    await browser.close()

    # With browser pool (recommended)
    pool = BrowserPool(max_browsers=3)
    html = await pool.fetch("https://example.com")
"""

import asyncio
import time
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from contextlib import asynccontextmanager

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


@dataclass
class BrowserConfig:
    """Configuration for Playwright browser."""

    headless: bool = True
    browser_type: str = "chromium"  # chromium, firefox, webkit
    user_agent: Optional[str] = None
    viewport: Dict[str, int] = None
    extra_args: List[str] = None
    stealth_mode: bool = True  # Anti-detection measures
    timeout: int = 30000  # milliseconds

    def __post_init__(self):
        if self.viewport is None:
            self.viewport = {"width": 1920, "height": 1080}
        if self.extra_args is None:
            self.extra_args = []


@dataclass
class FetchOptions:
    """Options for fetching a page."""

    wait_for: Optional[str] = None  # CSS selector to wait for
    wait_time: int = 1000  # milliseconds to wait after load
    actions: List[Dict[str, Any]] = None  # Actions to perform
    screenshot: bool = False
    full_page: bool = True


class PlaywrightBrowser:
    """
    Browser automation using Playwright.

    Handles JavaScript rendering, dynamic content, and anti-detection.
    """

    def __init__(self, config: Optional[BrowserConfig] = None):
        if not HAS_PLAYWRIGHT:
            raise ImportError(
                "Playwright is required. Install: pip install playwright && playwright install"
            )

        self.config = config or BrowserConfig()
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def start(self):
        """Start the browser."""
        self._playwright = await async_playwright().start()

        # Launch browser
        browser_launcher = getattr(self._playwright, self.config.browser_type)

        launch_options = {
            "headless": self.config.headless,
        }

        if self.config.extra_args:
            launch_options["args"] = self.config.extra_args

        self._browser = await browser_launcher.launch(**launch_options)

        # Create context with custom settings
        context_options = {
            "viewport": self.config.viewport,
        }

        if self.config.user_agent:
            context_options["user_agent"] = self.config.user_agent

        if self.config.stealth_mode:
            context_options["locale"] = "en-US"
            context_options["timezone_id"] = "America/New_York"

        self._context = await self._browser.new_context(**context_options)

        # Apply stealth measures
        if self.config.stealth_mode:
            await self._apply_stealth_measures()

        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.config.timeout)

    async def _apply_stealth_measures(self):
        """Apply anti-detection measures."""
        # Override navigator.webdriver
        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # Override plugins
        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)

        # Override permissions
        await self._context.add_init_script("""
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

    async def fetch(
        self, url: str, options: Optional[FetchOptions] = None
    ) -> Dict[str, Any]:
        """
        Fetch a URL with JavaScript rendering.

        Args:
            url: URL to fetch
            options: Fetch options

        Returns:
            Dict with html, screenshot (if requested), and metadata
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")

        opts = options or FetchOptions()
        result = {
            "html": "",
            "screenshot": None,
            "metadata": {},
            "success": False,
            "error": None,
        }

        try:
            # Navigate to page
            response = await self._page.goto(url, wait_until="networkidle")

            # Wait for specific element if specified
            if opts.wait_for:
                await self._page.wait_for_selector(
                    opts.wait_for, timeout=self.config.timeout
                )

            # Wait additional time
            if opts.wait_time > 0:
                await asyncio.sleep(opts.wait_time / 1000)

            # Perform actions
            if opts.actions:
                await self._perform_actions(opts.actions)

            # Get HTML
            result["html"] = await self._page.content()

            # Take screenshot if requested
            if opts.screenshot:
                result["screenshot"] = await self._page.screenshot(
                    full_page=opts.full_page, type="png"
                )

            # Extract metadata
            result["metadata"] = await self._extract_metadata()
            result["success"] = True

        except Exception as e:
            result["error"] = str(e)

        return result

    async def _perform_actions(self, actions: List[Dict[str, Any]]):
        """Perform actions on the page."""
        for action in actions:
            action_type = action.get("type")

            if action_type == "click":
                selector = action.get("selector")
                await self._page.click(selector)

            elif action_type == "scroll":
                await self._page.evaluate(
                    "window.scrollTo(0, document.body.scrollHeight)"
                )
                await asyncio.sleep(0.5)

            elif action_type == "wait":
                delay = action.get("milliseconds", 1000)
                await asyncio.sleep(delay / 1000)

            elif action_type == "type":
                selector = action.get("selector")
                text = action.get("text", "")
                await self._page.fill(selector, text)

            elif action_type == "press":
                key = action.get("key")
                await self._page.keyboard.press(key)

            elif action_type == "hover":
                selector = action.get("selector")
                await self._page.hover(selector)

    async def _extract_metadata(self) -> Dict[str, Any]:
        """Extract page metadata."""
        return await self._page.evaluate("""() => {
            return {
                title: document.title,
                url: window.location.href,
                description: document.querySelector('meta[name="description"]')?.content || '',
                keywords: document.querySelector('meta[name="keywords"]')?.content || '',
                author: document.querySelector('meta[name="author"]')?.content || '',
            };
        """)

    async def close(self):
        """Close the browser."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class BrowserPool:
    """
    Pool of browser instances for parallel processing.

    Similar to Crawl4AI's browser pool management.
    """

    def __init__(self, max_browsers: int = 3, config: Optional[BrowserConfig] = None):
        self.max_browsers = max_browsers
        self.config = config or BrowserConfig()
        self._browsers: List[PlaywrightBrowser] = []
        self._semaphore = asyncio.Semaphore(max_browsers)
        self._lock = asyncio.Lock()

    async def start(self):
        """Start the browser pool."""
        for _ in range(self.max_browsers):
            browser = PlaywrightBrowser(self.config)
            await browser.start()
            self._browsers.append(browser)

    async def fetch(
        self, url: str, options: Optional[FetchOptions] = None
    ) -> Dict[str, Any]:
        """Fetch a URL using an available browser from the pool."""
        async with self._semaphore:
            # Get available browser
            browser = None
            async with self._lock:
                if self._browsers:
                    browser = self._browsers.pop(0)

            if not browser:
                # Create new browser if pool is exhausted
                browser = PlaywrightBrowser(self.config)
                await browser.start()

            try:
                result = await browser.fetch(url, options)
            finally:
                # Return browser to pool
                async with self._lock:
                    self._browsers.append(browser)

            return result

    async def fetch_many(
        self, urls: List[str], options: Optional[FetchOptions] = None
    ) -> List[Dict[str, Any]]:
        """Fetch multiple URLs in parallel."""
        tasks = [self.fetch(url, options) for url in urls]
        return await asyncio.gather(*tasks)

    async def close(self):
        """Close all browsers in the pool."""
        for browser in self._browsers:
            await browser.close()
        self._browsers.clear()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class DynamicScraper:
    """
    High-level scraper that combines proxy chain with Playwright.

    Handles both static and dynamic content with automatic fallback.
    """

    def __init__(
        self,
        proxy_chain=None,
        use_browser: bool = True,
        browser_config: Optional[BrowserConfig] = None,
    ):
        self.proxy_chain = proxy_chain
        self.use_browser = use_browser
        self.browser_config = browser_config or BrowserConfig()
        self._browser_pool: Optional[BrowserPool] = None

    async def start(self):
        """Initialize the scraper."""
        if self.use_browser:
            self._browser_pool = BrowserPool(max_browsers=3, config=self.browser_config)
            await self._browser_pool.start()

    async def scrape(
        self, url: str, require_js: bool = False, options: Optional[FetchOptions] = None
    ) -> Dict[str, Any]:
        """
        Scrape a URL with automatic fallback.

        Args:
            url: URL to scrape
            require_js: Force JavaScript rendering
            options: Fetch options

        Returns:
            Scraped data with html, metadata, etc.
        """
        # Try static first (faster)
        if not require_js and self.proxy_chain:
            try:
                response = self.proxy_chain.get(url, timeout=10)
                if response.status_code == 200:
                    return {
                        "html": response.text,
                        "url": url,
                        "method": "static",
                        "success": True,
                        "error": None,
                    }
            except Exception:
                pass

        # Fall back to browser
        if self.use_browser and self._browser_pool:
            return await self._browser_pool.fetch(url, options)

        return {
            "html": "",
            "url": url,
            "success": False,
            "error": "Browser not available",
        }

    async def close(self):
        """Close the scraper."""
        if self._browser_pool:
            await self._browser_pool.close()


# Convenience functions
async def fetch_with_browser(
    url: str, wait_for: Optional[str] = None, headless: bool = True
) -> str:
    """
    Quick fetch with Playwright.

    Args:
        url: URL to fetch
        wait_for: CSS selector to wait for
        headless: Run in headless mode

    Returns:
        HTML content
    """
    config = BrowserConfig(headless=headless)
    options = FetchOptions(wait_for=wait_for)

    async with PlaywrightBrowser(config) as browser:
        result = await browser.fetch(url, options)
        return result.get("html", "")


async def scrape_dynamic(
    urls: List[str], max_parallel: int = 3
) -> List[Dict[str, Any]]:
    """
    Scrape multiple URLs in parallel.

    Args:
        urls: List of URLs to scrape
        max_parallel: Maximum parallel browsers

    Returns:
        List of scrape results
    """
    config = BrowserConfig()
    async with BrowserPool(max_browsers=max_parallel, config=config) as pool:
        return await pool.fetch_many(urls)
