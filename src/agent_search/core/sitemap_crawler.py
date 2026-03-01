"""
Sitemap and URL Discovery

Discover URLs from sitemaps, robots.txt, and link extraction.

Usage:
    from agent_search.core.sitemap_crawler import SitemapCrawler, URLDiscovery

    # Sitemap-based discovery
    crawler = SitemapCrawler()
    urls = await crawler.discover("https://example.com")

    # URL discovery from sitemap
    urls = await crawler.parse_sitemap("https://example.com/sitemap.xml")

    # From robots.txt
    urls = await crawler.parse_robots_txt("https://example.com/robots.txt")
"""

import asyncio
from typing import Optional, List, Dict, Any, Set
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass
import xml.etree.ElementTree as ET

try:
    from bs4 import BeautifulSoup

    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

from .proxy_chain import ProxyChain


@dataclass
class SitemapEntry:
    """Single sitemap entry."""

    url: str
    lastmod: Optional[str] = None
    changefreq: Optional[str] = None
    priority: Optional[float] = None


class SitemapCrawler:
    """
    Crawl sitemaps and discover URLs.

    Similar to Crawl4AI's AsyncUrlSeeder.
    """

    def __init__(self, proxy_chain: Optional[ProxyChain] = None):
        self.proxy_chain = proxy_chain or ProxyChain()
        self.discovered: Set[str] = set()

    async def discover(
        self, base_url: str, methods: Optional[List[str]] = None
    ) -> List[str]:
        """
        Discover URLs using multiple methods.

        Args:
            base_url: Starting URL
            methods: List of methods to use ['sitemap', 'robots', 'links']

        Returns:
            List of discovered URLs
        """
        if methods is None:
            methods = ["sitemap", "robots", "links"]

        discovered = []

        # Parse base URL
        parsed = urlparse(base_url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        # Try sitemap
        if "sitemap" in methods:
            sitemap_url = f"{base}/sitemap.xml"
            sitemap_urls = await self.parse_sitemap(sitemap_url)
            discovered.extend(sitemap_urls)
            self.discovered.update(sitemap_urls)

        # Try robots.txt
        if "robots" in methods:
            robots_url = f"{base}/robots.txt"
            robots_urls = await self.parse_robots_txt(robots_url)
            discovered.extend(robots_urls)
            self.discovered.update(robots_urls)

        # Try link extraction from homepage
        if "links" in methods:
            try:
                response = self.proxy_chain.get(base_url, timeout=10)
                if response.status_code == 200:
                    links = self._extract_links(response.text, base_url)
                    discovered.extend(links)
                    self.discovered.update(links)
            except Exception:
                pass

        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for url in discovered:
            if url not in seen:
                seen.add(url)
                unique.append(url)

        return unique

    async def parse_sitemap(
        self, sitemap_url: str, recursive: bool = True
    ) -> List[str]:
        """
        Parse sitemap.xml and return all URLs.

        Args:
            sitemap_url: URL of sitemap
            recursive: Follow sitemap index files

        Returns:
            List of URLs
        """
        urls = []

        try:
            response = self.proxy_chain.get(sitemap_url, timeout=30)
            if response.status_code != 200:
                return urls

            content = response.text

            # Check if it's a sitemap index
            if "<sitemapindex" in content:
                urls.extend(await self._parse_sitemap_index(content, recursive))
            else:
                urls.extend(self._parse_sitemap_content(content))

        except Exception:
            pass

        return urls

    def _parse_sitemap_content(self, content: str) -> List[str]:
        """Parse sitemap XML content."""
        urls = []

        try:
            root = ET.fromstring(content)

            # Handle both urlset and sitemapindex
            ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            # Find all URL entries
            for url_elem in root.findall(".//ns:url", ns) or root.findall(".//url"):
                loc = url_elem.find("ns:loc", ns) or url_elem.find("loc")
                if loc is not None and loc.text:
                    urls.append(loc.text.strip())

        except ET.ParseError:
            # Try regex fallback
            urls = re.findall(r"<loc>([^<]+)</loc>", content)

        return urls

    async def _parse_sitemap_index(self, content: str, recursive: bool) -> List[str]:
        """Parse sitemap index file."""
        urls = []

        try:
            root = ET.fromstring(content)
            ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            # Find all sitemap entries
            for sitemap in root.findall(".//ns:sitemap", ns) or root.findall(
                ".//sitemap"
            ):
                loc = sitemap.find("ns:loc", ns) or sitemap.find("loc")
                if loc is not None and loc.text:
                    child_sitemap = loc.text.strip()
                    if recursive:
                        child_urls = await self.parse_sitemap(
                            child_sitemap, recursive=False
                        )
                        urls.extend(child_urls)
                    else:
                        urls.append(child_sitemap)

        except ET.ParseError:
            # Try regex fallback
            sitemaps = re.findall(r"<loc>([^<]+)</loc>", content)
            for sitemap in sitemaps:
                if sitemap.endswith(".xml"):
                    urls.append(sitemap)

        return urls

    async def parse_robots_txt(self, robots_url: str) -> List[str]:
        """
        Parse robots.txt and extract sitemap URLs.

        Args:
            robots_url: URL of robots.txt

        Returns:
            List of discovered URLs from sitemaps
        """
        urls = []

        try:
            response = self.proxy_chain.get(robots_url, timeout=10)
            if response.status_code != 200:
                return urls

            content = response.text

            # Find Sitemap directives
            sitemaps = re.findall(r"^[Ss]itemap:\s*(.+)$", content, re.MULTILINE)

            for sitemap in sitemaps:
                sitemap = sitemap.strip()
                if sitemap:
                    discovered = await self.parse_sitemap(sitemap)
                    urls.extend(discovered)

        except Exception:
            pass

        return urls

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        """Extract links from HTML."""
        if not HAS_BS4:
            return []

        soup = BeautifulSoup(html, "html.parser")
        links = []
        base_domain = urlparse(base_url).netloc

        for a in soup.find_all("a", href=True):
            href = a["href"]

            # Skip anchors and non-http
            if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            # Resolve URL
            full_url = urljoin(base_url, href)

            # Only same domain
            if urlparse(full_url).netloc == base_domain:
                links.append(full_url)

        return links


class URLDiscovery:
    """
    High-level URL discovery combining multiple strategies.

    Similar to Firecrawl's Map functionality.
    """

    def __init__(self, proxy_chain: Optional[ProxyChain] = None):
        self.sitemap_crawler = SitemapCrawler(proxy_chain)
        self.discovered: Set[str] = set()

    async def discover(
        self,
        url: str,
        include_sitemap: bool = True,
        include_robots: bool = True,
        include_links: bool = True,
        max_urls: int = 1000,
    ) -> Dict[str, Any]:
        """
        Discover URLs from a website.

        Args:
            url: Starting URL
            include_sitemap: Parse sitemap.xml
            include_robots: Parse robots.txt
            include_links: Extract links from pages
            max_urls: Maximum URLs to discover

        Returns:
            Dict with discovered URLs and metadata
        """
        methods = []
        if include_sitemap:
            methods.append("sitemap")
        if include_robots:
            methods.append("robots")
        if include_links:
            methods.append("links")

        urls = await self.sitemap_crawler.discover(url, methods)

        # Limit results
        urls = urls[:max_urls]

        return {
            "source_url": url,
            "total_discovered": len(urls),
            "urls": urls,
            "methods_used": methods,
        }

    async def search_within_site(
        self, site_url: str, query: str, max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search within a site for URLs matching a query.

        Args:
            site_url: Site to search
            query: Search query
            max_results: Maximum results

        Returns:
            List of matching URLs with relevance scores
        """
        # Discover all URLs
        discovery = await self.discover(site_url, max_urls=500)
        urls = discovery["urls"]

        # Simple relevance scoring
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored_urls = []
        for url in urls:
            url_lower = url.lower()

            # Calculate score
            score = 0

            # Exact match in URL
            if query_lower in url_lower:
                score += 10

            # Word matches
            for word in query_words:
                if word in url_lower:
                    score += 1

            if score > 0:
                scored_urls.append({"url": url, "relevance_score": score})

        # Sort by score
        scored_urls.sort(key=lambda x: x["relevance_score"], reverse=True)

        return scored_urls[:max_results]


# Convenience functions
async def discover_urls(url: str, max_urls: int = 1000) -> List[str]:
    """
    Quick URL discovery from a website.

    Args:
        url: Starting URL
        max_urls: Maximum URLs to discover

    Returns:
        List of discovered URLs
    """
    discovery = URLDiscovery()
    result = await discovery.discover(url, max_urls=max_urls)
    return result["urls"]


def discover_sitemap_sync(url: str) -> List[str]:
    """
    Synchronous sitemap discovery.

    Args:
        url: Sitemap URL

    Returns:
        List of URLs
    """
    import requests

    urls = []
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            # Parse as sitemap
            if "<sitemapindex" in response.text:
                # Sitemap index - just return sitemap URLs
                urls = re.findall(r"<loc>([^<]+)</loc>", response.text)
            else:
                urls = re.findall(r"<loc>([^<]+)</loc>", response.text)
    except Exception:
        pass

    return urls
