"""Multi-engine search aggregator with ranking."""

import os
import json
import hashlib
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import quote, urlencode
from bs4 import BeautifulSoup
from agent_search.core.proxy_chain import ProxyChain
from agent_search.core.html_to_markdown import HTMLToMarkdown


class MultiEngineSearch:
    """
    Search aggregator that queries multiple engines and ranks results.

    Engines:
    - Whoogle (Google via proxy)
    - DuckDuckGo Lite
    - Bing (if API key available)

    Results are deduplicated, scored, and ranked by relevance.
    """

    def __init__(self):
        self.proxy_chain = ProxyChain()
        self.html_to_md = HTMLToMarkdown()
        self.session = requests.Session()

        # Engine endpoints
        self.whoogle_url = os.getenv("AGENT_SEARCH_ENDPOINT", "http://localhost:15000")
        self.bing_api_key = os.getenv("BING_SEARCH_API_KEY")

    def search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Perform multi-engine search and return aggregated results.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            Dict with query, results, and metadata
        """
        all_results = []
        engines_used = []
        errors = []

        # Try Whoogle first (Google results)
        try:
            whoogle_results = self._search_whoogle(query)
            if whoogle_results:
                all_results.extend(whoogle_results)
                engines_used.append("whoogle")
        except Exception as e:
            errors.append(f"Whoogle: {str(e)}")

        # Try DuckDuckGo
        try:
            ddg_results = self._search_duckduckgo(query)
            if ddg_results:
                all_results.extend(ddg_results)
                engines_used.append("duckduckgo")
        except Exception as e:
            errors.append(f"DuckDuckGo: {str(e)}")

        # Try Bing if API key available
        if self.bing_api_key:
            try:
                bing_results = self._search_bing(query)
                if bing_results:
                    all_results.extend(bing_results)
                    engines_used.append("bing")
            except Exception as e:
                errors.append(f"Bing: {str(e)}")

        # Fallback: Try Wikipedia API (no key needed, real results)
        if not all_results:
            try:
                wiki_results = self._search_wikipedia(query)
                if wiki_results:
                    all_results.extend(wiki_results)
                    engines_used.append("wikipedia")
            except Exception as e:
                errors.append(f"Wikipedia: {str(e)}")

        # Deduplicate and rank results
        if all_results:
            unique_results = self._deduplicate_results(all_results)
            ranked_results = self._rank_results(unique_results, query)
            final_results = ranked_results[:max_results]
        else:
            final_results = []

        return {
            "query": query,
            "results": final_results,
            "total_results": len(final_results),
            "engines_used": engines_used,
            "errors": errors if errors else None,
            "search_time": 0.0,
        }

    def _search_whoogle(self, query: str) -> List[Dict[str, Any]]:
        """Search using Whoogle (Google proxy)."""
        search_url = f"{self.whoogle_url}/search?q={quote(query)}"

        response = self.session.get(search_url, timeout=10)
        data = response.json()

        results = []
        if "results" in data:
            for item in data["results"]:
                results.append(
                    {
                        "title": item.get("title", "Untitled"),
                        "url": item.get("url", item.get("href", "#")),
                        "snippet": item.get("snippet", item.get("body", "")),
                        "source": "whoogle",
                        "score": 0.9,  # High score for Google results
                    }
                )

        return results

    def _search_duckduckgo(self, query: str) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo Lite."""
        # DuckDuckGo Lite HTML endpoint
        ddg_url = f"https://lite.duckduckgo.com/lite/?q={quote(query)}"

        # Use requests with proper headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

        response = self.session.get(ddg_url, headers=headers, timeout=10)

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        results = []
        # DuckDuckGo Lite results are in table rows
        result_rows = soup.find_all("tr", class_="result")

        for row in result_rows[:10]:  # Get top 10
            try:
                # Find link
                link_elem = row.find("a", class_="result-link")
                if not link_elem:
                    continue

                url = link_elem.get("href", "")
                title = link_elem.get_text(strip=True)

                # Find snippet
                snippet_elem = row.find("td", class_="result-snippet")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                if url and title:
                    results.append(
                        {
                            "title": title[:200],
                            "url": url[:500],
                            "snippet": snippet[:300],
                            "source": "duckduckgo",
                            "score": 0.7,
                        }
                    )
            except Exception:
                continue

        return results

    def _search_bing(self, query: str) -> List[Dict[str, Any]]:
        """Search using Bing API."""
        if not self.bing_api_key:
            return []

        # Bing Web Search API v7
        endpoint = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": self.bing_api_key}
        params = {"q": query, "count": 10, "mkt": "en-US"}

        response = self.session.get(
            endpoint, headers=headers, params=params, timeout=10
        )
        data = response.json()

        results = []
        if "webPages" in data and "value" in data["webPages"]:
            for item in data["webPages"]["value"]:
                results.append(
                    {
                        "title": item.get("name", "Untitled"),
                        "url": item.get("url", "#"),
                        "snippet": item.get("snippet", ""),
                        "source": "bing",
                        "score": 0.8,
                    }
                )

        return results

    def _search_wikipedia(self, query: str) -> List[Dict[str, Any]]:
        """Search Wikipedia API (no key needed)."""
        # Wikipedia search API
        wiki_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 5,
        }

        headers = {"User-Agent": "AgentSearchBot/1.0 (contact@example.com)"}

        response = self.session.get(
            wiki_url, params=params, headers=headers, timeout=10
        )
        data = response.json()

        results = []
        if "query" in data and "search" in data["query"]:
            for item in data["query"]["search"]:
                title = item.get("title", "Untitled")
                # Build Wikipedia URL
                url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                # Clean snippet (remove wiki markup)
                snippet = (
                    item.get("snippet", "")
                    .replace('<span class="searchmatch">', "")
                    .replace("</span>", "")
                )

                results.append(
                    {
                        "title": f"{title} - Wikipedia",
                        "url": url,
                        "snippet": snippet[:300] + "..."
                        if len(snippet) > 300
                        else snippet,
                        "source": "wikipedia",
                        "score": 0.75,  # Good score for Wikipedia
                    }
                )

        return results

    def _deduplicate_results(
        self, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate results based on URL."""
        seen_urls = set()
        unique_results = []

        for result in results:
            url = result.get("url", "")
            # Normalize URL for comparison
            normalized_url = url.lower().strip().rstrip("/")

            if normalized_url and normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                unique_results.append(result)

        return unique_results

    def _rank_results(
        self, results: List[Dict[str, Any]], query: str
    ) -> List[Dict[str, Any]]:
        """Score and rank results by relevance."""
        query_words = set(query.lower().split())

        for result in results:
            score = result.get("score", 0.5)
            title = result.get("title", "").lower()
            snippet = result.get("snippet", "").lower()

            # Boost score based on query term matching
            title_matches = sum(1 for word in query_words if word in title)
            snippet_matches = sum(1 for word in query_words if word in snippet)

            # Boost for title matches (more important)
            score += title_matches * 0.15
            score += snippet_matches * 0.05

            # Boost for authoritative domains
            url = result.get("url", "")
            if any(domain in url for domain in [".edu", ".gov", "wikipedia.org"]):
                score += 0.1

            # Boost for https
            if url.startswith("https://"):
                score += 0.02

            result["score"] = min(score, 1.0)  # Cap at 1.0

        # Sort by score descending
        return sorted(results, key=lambda x: x.get("score", 0), reverse=True)


def perform_search(query: str, max_results: int = 10) -> Dict[str, Any]:
    """
    Convenience function to perform multi-engine search.

    Args:
        query: Search query
        max_results: Maximum results to return

    Returns:
        Search results dictionary
    """
    searcher = MultiEngineSearch()
    return searcher.search(query, max_results)
