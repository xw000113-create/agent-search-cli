"""
REST API Server

FastAPI-based REST API for the proxy toolkit.
Provides endpoints for scraping, crawling, and extraction.

Usage:
    from agent_search.core.api_server import app, start_server

    # Start server
    start_server(host="0.0.0.0", port=8000)

    # Or use with uvicorn directly
    uvicorn.run(app, host="0.0.0.0", port=8000)

Endpoints:
    POST /scrape - Scrape a single URL
    POST /crawl - Crawl multiple URLs
    POST /extract - Extract structured data
    POST /search - Search and scrape results
    GET /health - Health check
"""

import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from pydantic import BaseModel, Field

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from .proxy_chain import ProxyChain
from .batch_processor import BatchProcessor, BatchConfig, Crawler
from .data_extraction import StructuredExtractor, CSSExtractionStrategy
from .html_to_markdown import html_to_markdown


# Request/Response models
class ScrapeRequest(BaseModel):
    """Request model for scraping."""

    url: str = Field(..., description="URL to scrape")
    wait_for: Optional[str] = Field(None, description="CSS selector to wait for")
    actions: Optional[List[Dict[str, Any]]] = Field(
        None, description="Actions to perform"
    )
    use_browser: bool = Field(False, description="Use browser rendering")
    include_images: bool = Field(True, description="Include images in markdown")
    include_links: bool = Field(True, description="Include links in markdown")


class ScrapeResponse(BaseModel):
    """Response model for scraping."""

    success: bool
    url: str
    markdown: Optional[str] = None
    html: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class CrawlRequest(BaseModel):
    """Request model for crawling."""

    url: str = Field(..., description="Starting URL")
    max_depth: int = Field(3, description="Maximum crawl depth")
    max_pages: int = Field(50, description="Maximum pages to crawl")
    same_domain_only: bool = Field(True, description="Stay within same domain")
    use_browser: bool = Field(False, description="Use browser rendering")


class CrawlResponse(BaseModel):
    """Response model for crawling."""

    success: bool
    url: str
    pages_crawled: int
    pages: List[ScrapeResponse]
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ExtractRequest(BaseModel):
    """Request model for extraction."""

    url: str = Field(..., description="URL to extract from")
    schema: Optional[Dict[str, Any]] = Field(None, description="Extraction schema")
    selectors: Optional[Dict[str, Any]] = Field(None, description="CSS selectors")
    instruction: Optional[str] = Field(None, description="Natural language instruction")
    use_llm: bool = Field(False, description="Use LLM for extraction")


class ExtractResponse(BaseModel):
    """Response model for extraction."""

    success: bool
    url: str
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class BatchScrapeRequest(BaseModel):
    """Request model for batch scraping."""

    urls: List[str] = Field(..., description="URLs to scrape")
    max_workers: int = Field(10, description="Maximum parallel workers")
    use_browser: bool = Field(False, description="Use browser rendering")


# Global instances
proxy_chain: Optional[ProxyChain] = None
batch_processor: Optional[BatchProcessor] = None
extractor: Optional[StructuredExtractor] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    global proxy_chain, batch_processor, extractor

    # Startup
    proxy_chain = ProxyChain()
    batch_processor = BatchProcessor(BatchConfig(use_browser=False))
    extractor = StructuredExtractor()

    await batch_processor.start()

    yield

    # Shutdown
    await batch_processor.close()


# Create FastAPI app
if HAS_FASTAPI:
    app = FastAPI(
        title="Proxy Toolkit API",
        description="Web scraping and data extraction API with proxy rotation",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    security = HTTPBearer(auto_error=False)

    def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
        """Verify API token if configured."""
        api_key = os.getenv("API_KEY")
        if not api_key:
            return True

        if not credentials:
            raise HTTPException(status_code=401, detail="Authentication required")

        if credentials.credentials != api_key:
            raise HTTPException(status_code=403, detail="Invalid API key")

        return True

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": "2.0.0",
            "features": [
                "proxy_rotation",
                "browser_rendering",
                "markdown_conversion",
                "structured_extraction",
                "batch_processing",
            ],
            "timestamp": datetime.now().isoformat(),
        }

    @app.post("/scrape", response_model=ScrapeResponse)
    async def scrape(request: ScrapeRequest, auth: bool = Depends(verify_token)):
        """
        Scrape a single URL.

        Returns markdown, HTML, and metadata for the URL.
        """
        try:
            if request.use_browser:
                # Use browser rendering
                from .playwright_browser import (
                    PlaywrightBrowser,
                    BrowserConfig,
                    FetchOptions,
                )

                config = BrowserConfig(headless=True)
                options = FetchOptions(
                    wait_for=request.wait_for, actions=request.actions or []
                )

                async with PlaywrightBrowser(config) as browser:
                    result = await browser.fetch(request.url, options)

                    if result["success"]:
                        html = result["html"]
                        markdown = html_to_markdown(
                            html,
                            base_url=request.url,
                            include_images=request.include_images,
                            include_links=request.include_links,
                        )

                        return ScrapeResponse(
                            success=True,
                            url=request.url,
                            markdown=markdown,
                            html=html,
                            metadata=result.get("metadata", {}),
                        )
                    else:
                        return ScrapeResponse(
                            success=False,
                            url=request.url,
                            error=result.get("error", "Unknown error"),
                        )
            else:
                # Use proxy chain
                response = proxy_chain.get(request.url, timeout=30)

                if response.status_code == 200:
                    markdown = html_to_markdown(
                        response.text,
                        base_url=request.url,
                        include_images=request.include_images,
                        include_links=request.include_links,
                    )

                    return ScrapeResponse(
                        success=True,
                        url=request.url,
                        markdown=markdown,
                        html=response.text,
                        metadata={
                            "status_code": response.status_code,
                            "content_type": response.headers.get("Content-Type"),
                        },
                    )
                else:
                    return ScrapeResponse(
                        success=False,
                        url=request.url,
                        error=f"HTTP {response.status_code}",
                    )

        except Exception as e:
            return ScrapeResponse(success=False, url=request.url, error=str(e))

    @app.post("/crawl", response_model=CrawlResponse)
    async def crawl(
        request: CrawlRequest,
        background_tasks: BackgroundTasks,
        auth: bool = Depends(verify_token),
    ):
        """
        Crawl a website starting from a URL.

        Returns all pages crawled with their content.
        """
        try:
            crawler = Crawler(
                max_depth=request.max_depth, same_domain_only=request.same_domain_only
            )

            pages = await crawler.crawl(request.url)
            pages = pages[: request.max_pages]

            # Convert to response format
            scrape_responses = []
            for page in pages:
                if page.get("success"):
                    html = page.get("html", "")
                    markdown = html_to_markdown(html, base_url=page.get("url"))

                    scrape_responses.append(
                        ScrapeResponse(
                            success=True,
                            url=page.get("url"),
                            markdown=markdown,
                            html=html,
                            metadata=page.get("metadata", {}),
                        )
                    )

            return CrawlResponse(
                success=True,
                url=request.url,
                pages_crawled=len(scrape_responses),
                pages=scrape_responses,
            )

        except Exception as e:
            return CrawlResponse(
                success=False, url=request.url, pages_crawled=0, pages=[], error=str(e)
            )

    @app.post("/extract", response_model=ExtractResponse)
    async def extract(request: ExtractRequest, auth: bool = Depends(verify_token)):
        """
        Extract structured data from a URL.

        Supports CSS selectors or LLM-based extraction.
        """
        try:
            # First fetch the page
            response = proxy_chain.get(request.url, timeout=30)

            if response.status_code != 200:
                return ExtractResponse(
                    success=False, url=request.url, error=f"HTTP {response.status_code}"
                )

            html = response.text

            if request.selectors:
                # Use CSS extraction
                strategy = CSSExtractionStrategy(
                    base_selector=request.selectors.get("base", "body"),
                    fields=request.selectors.get("fields", {}),
                )

                data = extractor.extract_with_css(html, strategy)

                return ExtractResponse(success=True, url=request.url, data=data)
            else:
                # Try to extract tables
                tables = extractor.extract_tables(html)

                return ExtractResponse(success=True, url=request.url, data=tables)

        except Exception as e:
            return ExtractResponse(success=False, url=request.url, error=str(e))

    @app.post("/batch", response_model=List[ScrapeResponse])
    async def batch_scrape(
        request: BatchScrapeRequest, auth: bool = Depends(verify_token)
    ):
        """
        Scrape multiple URLs in batch.

        Processes URLs in parallel with rate limiting.
        """
        try:
            config = BatchConfig(
                max_workers=request.max_workers, use_browser=request.use_browser
            )

            async with BatchProcessor(config) as processor:
                results = await processor.process(request.urls)

                responses = []
                for result in results:
                    if result.get("success"):
                        html = result.get("html", "")
                        markdown = html_to_markdown(html, base_url=result.get("url"))

                        responses.append(
                            ScrapeResponse(
                                success=True,
                                url=result.get("url"),
                                markdown=markdown,
                                html=html,
                                metadata=result.get("metadata", {}),
                            )
                        )
                    else:
                        responses.append(
                            ScrapeResponse(
                                success=False,
                                url=result.get("url"),
                                error=result.get("error", "Unknown error"),
                            )
                        )

                return responses

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/sitemap")
    async def get_sitemap(url: str, auth: bool = Depends(verify_token)):
        """
        Discover URLs from sitemap.

        Returns all URLs found in sitemap.xml and robots.txt.
        """
        from .sitemap_crawler import URLDiscovery

        try:
            discovery = URLDiscovery(proxy_chain)
            result = await discovery.discover(url)

            return {
                "success": True,
                "source_url": url,
                "total_discovered": result["total_discovered"],
                "urls": result["urls"],
            }

        except Exception as e:
            return {"success": False, "source_url": url, "error": str(e)}

else:
    # FastAPI not available - create placeholder
    app = None


def start_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """
    Start the API server.

    Args:
        host: Host to bind to
        port: Port to listen on
        reload: Enable auto-reload for development
    """
    if not HAS_FASTAPI:
        raise ImportError(
            "FastAPI and uvicorn required. Install: pip install fastapi uvicorn"
        )

    import uvicorn

    uvicorn.run("agent_search.core.api_server:app", host=host, port=port, reload=reload)


# Convenience function for running directly
if __name__ == "__main__":
    start_server()
