# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-01

### Added
- **Multi-engine search** — Google, DuckDuckGo, Bing, and Wikipedia with dedup + ranking
- **4-layer proxy chain** — MacBook relay, NordVPN SOCKS5, AWS API Gateway IP rotation, direct fallback
- **Headless browsing** — Playwright with stealth mode for JavaScript-rendered pages
- **Structured extraction** — CSS selectors, XPath, and LLM-powered extraction
- **Change monitoring** — Watch URLs for content changes with configurable intervals
- **Community proxy pool** — Share bandwidth, earn credits
- **HTML to Markdown conversion** — Clean conversion with BeautifulSoup4
- **Batch processing** — Async parallel URL processing with concurrency control
- **REST API server** — FastAPI-based API for scraping, crawling, and extraction
- **CLI** — `search` command with subcommands: query, crawl, extract, monitor, auth, pool
- **Comprehensive test suite** — 130+ test cases
- Published to PyPI as `agentsearchcli`
