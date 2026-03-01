<p align="center">
  <h1 align="center">Agent Search</h1>
  <p align="center"><strong>Give any AI agent the ability to search, crawl, and extract the web.</strong></p>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python 3.9+"></a>
  <a href="https://pypi.org/project/agentsearchcli/"><img src="https://img.shields.io/pypi/v/agentsearchcli.svg" alt="PyPI"></a>
</p>

---

Agent Search is a CLI and Python library that gives AI agents reliable web access. One command to search, crawl websites, extract structured data, and monitor pages for changes — all routed through a 4-layer proxy chain that automatically handles IP rotation, CAPTCHA detection, and rate limiting.

```bash
pip install agentsearchcli
search "latest NVIDIA earnings" --format json
```

## Why Agent Search?

Most AI agents can't reliably access the web. Search APIs are expensive, direct requests get blocked, and scraping requires infrastructure. Agent Search solves this:

- **Multi-engine search** — Aggregates results from Google, DuckDuckGo, Bing, and Wikipedia. Deduplicates and ranks by relevance.
- **4-layer proxy chain** — Automatic failover: MacBook relay -> NordVPN SOCKS5 -> AWS API Gateway IP rotation -> direct. Never get blocked.
- **Headless browsing** — Playwright with stealth mode for JavaScript-rendered pages.
- **Structured extraction** — Pull data from any page using CSS selectors, XPath, or LLM-powered extraction.
- **Change monitoring** — Watch any URL for content changes with configurable intervals.
- **Community proxy pool** — Earn credits by sharing bandwidth. Spend credits to use the network.

---

## Quick Start

```bash
# Install
pip install agentsearchcli

# First run — creates account and gets API key
search

# Search the web
search "Python asyncio documentation"

# Output as JSON (for agents)
search query "React hooks tutorial" --format json

# Use headless browser for JS-heavy sites
search query "site:twitter.com AI news" --browser

# Crawl a docs site
search crawl https://docs.python.org --depth 3 --max-pages 100

# Extract structured data
search extract https://shop.com/products --schema schema.json --format json

# Monitor a page for changes (check every 30 min)
search monitor https://example.com/pricing --interval 1800
```

---

## Installation

```bash
# Core (requests-based, no browser)
pip install agentsearchcli

# With headless browser support
pip install agentsearchcli[browser]

# From source
git clone https://github.com/r0botsorg/agent-search-cli.git
cd agent-search-cli
pip install -e ".[dev]"
```

**Requirements:** Python 3.9+ and an internet connection. Everything else is optional.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    CLI / Library                      │
│    search query | crawl | extract | monitor          │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│               Multi-Engine Search                    │
│    Google + DuckDuckGo + Bing + Wikipedia             │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│               4-Layer Proxy Chain                    │
│                                                      │
│    1. MacBook Relay     (residential IP)             │
│    2. NordVPN SOCKS5    (residential IP)             │
│    3. AWS API Gateway   (rotating datacenter IPs)    │
│    4. Direct            (fallback)                   │
│                                                      │
│    Auto-failover · CAPTCHA detection · Rate limiting │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│               Content Processing                     │
│                                                      │
│    HTML → Markdown · CSS/XPath extraction            │
│    LLM extraction · Change detection                 │
│    Playwright stealth · Session management           │
└─────────────────────────────────────────────────────┘
```

---

## Modes

| Mode | Cost | Proxies | Best For |
|------|------|---------|----------|
| **Lite** | Free | Self-managed (your proxies) | Developers with existing infrastructure |
| **Pro** | Paid | Fully managed | Teams who want zero setup |
| **Pool** | Free | Community-powered | Everyone — share bandwidth, earn credits |

---

## CLI Reference

### Global Options

| Option | Description |
|--------|-------------|
| `--version` | Show version and exit |
| `--verbose` / `-v` | Enable debug logging |
| `--config PATH` | Path to custom config file |
| `--skip-onboarding` | Skip the first-run setup wizard |

### Search

```bash
search "your query"                              # quick search
search query "your query" --format json          # JSON output
search query "your query" --browser              # JS rendering
search query "your query" --extract "h1, .price" # CSS extraction
search query "your query" --pro                  # hosted mode
search query "your query" -o results.json        # save to file
```

### Crawl

```bash
search crawl https://docs.example.com --depth 3 --max-pages 100
```

### Extract

```bash
search extract https://shop.com/product --schema schema.json --format json
```

### Monitor

```bash
search monitor https://example.com/pricing --interval 1800
```

### Proxy Pool

```bash
search pool join       # contribute bandwidth, earn credits
search pool leave      # stop participating
search pool status     # your node status
search pool stats      # global network stats
search pool credits    # your balance
```

### Auth

```bash
search auth login      # authenticate for Pro mode
search auth logout     # remove stored credentials
search auth status     # check auth state
```

### Command Tree

```
search [QUERY]
├── query QUERY [--pro] [-f markdown|html|json] [-o PATH] [--extract CSS] [--browser]
├── crawl URL [--pro] [--depth N] [--max-pages N]
├── extract URL [--pro] [--schema PATH] [-f markdown|json]
├── monitor URL [--pro] [--interval N]
├── onboard
├── auth
│   ├── login
│   ├── logout
│   └── status
└── pool
    ├── join
    ├── leave
    ├── status
    ├── stats
    └── credits
```

**13 commands** total.

---

## Python Library

Use Agent Search as a library in your own code:

```python
from agent_search.core.proxy_chain import ProxyChain
from agent_search.core.multi_search import MultiEngineSearch
from agent_search.core.html_to_markdown import HTMLToMarkdown
from agent_search.core.data_extraction import DataExtractor
from agent_search.core.change_detector import ChangeDetector

# Proxy-aware HTTP requests with automatic failover
proxy = ProxyChain()
response = proxy.get("https://example.com")
data = await proxy.async_get("https://api.example.com/data")
proxies = proxy.get_best_proxies_dict()  # for use with requests

# Multi-engine search with dedup + ranking
engine = MultiEngineSearch()
results = engine.search("latest AI research", max_results=10)

# HTML to clean Markdown
converter = HTMLToMarkdown()
markdown = converter.convert(html, base_url="https://example.com")

# Structured data extraction
extractor = DataExtractor()
data = extractor.extract(url, selectors=["h1", ".price", ".description"])

# Change monitoring
detector = ChangeDetector()
changed = detector.check(url)  # returns True if content changed
```

---

## Core Modules

| Module | Description |
|--------|-------------|
| `proxy_chain` | 4-layer proxy with automatic failover |
| `multi_search` | Multi-engine search aggregation with dedup + ranking |
| `html_to_markdown` | Clean HTML-to-Markdown conversion |
| `data_extraction` | CSS, XPath, and LLM-powered structured extraction |
| `playwright_browser` | Headless Chrome with stealth mode |
| `batch_processor` | Async batch URL processing with concurrency control |
| `change_detector` | Content change monitoring via SHA-256 snapshots |
| `captcha_detector` | CAPTCHA and anti-bot block detection |
| `rate_limiter` | Thread-safe rate limiting with adaptive backoff |
| `retry_handler` | Exponential backoff with circuit breaker pattern |
| `sitemap_crawler` | URL discovery via sitemap.xml and robots.txt |
| `aws_ip_rotator` | AWS API Gateway IP rotation (new IP per request) |
| `nordvpn_proxy` | NordVPN SOCKS5 residential proxy support |
| `session_manager` | Persistent session and cookie storage |
| `user_agents` | 27 real browser User-Agent strings with rotation |
| `llm_extractor` | LLM-powered intelligent data extraction |

---

## Configuration

Config is stored at `~/.config/agent-search/config.json` (created on first run via onboarding wizard).

### Environment Variables

| Variable | Description |
|----------|-------------|
| `AGENT_SEARCH_ENDPOINT` | Search endpoint URL (default: `http://localhost:15000`) |
| `AGENT_SEARCH_API_KEY` | Pro mode API key |
| `NORDVPN_SERVICE_USER` | NordVPN SOCKS5 username |
| `NORDVPN_SERVICE_PASS` | NordVPN SOCKS5 password |
| `AWS_API_GATEWAY_ID` | AWS API Gateway ID for IP rotation |
| `AWS_REGION` | AWS region (default: `us-east-1`) |
| `MACBOOK_PROXY_URL` | MacBook relay proxy URL |
| `MACBOOK_API_KEY` | MacBook relay auth key |
| `OPENAI_API_KEY` | For LLM-powered extraction |
| `BING_SEARCH_API_KEY` | Bing Search API key (optional engine) |

---

## Project Structure

```
agent-search-cli/
├── pyproject.toml                # Package config + entry points
├── src/agent_search/
│   ├── cli/                      # CLI layer (Click)
│   │   ├── main.py               # Command routing
│   │   ├── onboarding.py         # First-run setup wizard
│   │   └── commands/
│   │       ├── query.py          # Web search
│   │       ├── crawl.py          # Website crawling
│   │       ├── extract.py        # Data extraction
│   │       ├── monitor.py        # Change monitoring
│   │       ├── auth.py           # Authentication
│   │       └── pool.py           # Proxy pool management
│   ├── core/                     # Core library (usable independently)
│   │   ├── proxy_chain.py        # 4-layer proxy failover
│   │   ├── multi_search.py       # Multi-engine search
│   │   ├── html_to_markdown.py   # HTML → Markdown
│   │   ├── data_extraction.py    # Structured extraction
│   │   ├── playwright_browser.py # Headless browser
│   │   ├── batch_processor.py    # Async batch processing
│   │   ├── change_detector.py    # Change monitoring
│   │   ├── captcha_detector.py   # Anti-bot detection
│   │   ├── rate_limiter.py       # Rate limiting
│   │   ├── retry_handler.py      # Retry + circuit breaker
│   │   ├── sitemap_crawler.py    # Sitemap discovery
│   │   ├── aws_ip_rotator.py     # AWS IP rotation
│   │   ├── nordvpn_proxy.py      # NordVPN SOCKS5
│   │   ├── session_manager.py    # Session persistence
│   │   ├── llm_extractor.py      # LLM extraction
│   │   └── user_agents.py        # UA rotation
│   ├── pool/                     # Proxy pool network
│   └── utils/
│       ├── logger.py
│       └── version.py
└── tests/
    ├── test_*.py
    └── unit/
```

---

## Development

```bash
git clone https://github.com/r0botsorg/agent-search-cli.git
cd agent-search-cli
pip install -e ".[dev]"
python -m pytest tests/ -v
```

---

## About Qwerty

Agent Search is built by **Qwerty** ([qwert.ai](https://qwert.ai)) — an AI-powered search platform designed specifically for agents and autonomous systems.

Traditional search wasn't built for the agent era. It was built for humans typing queries into search boxes. Qwerty is different: an agent-first search infrastructure built from the ground up for the software that's replacing manual workflows.

### The Platform

Agent Search CLI is the open-source core of the Qwerty platform. The full stack includes:

| Component | Description |
|-----------|-------------|
| **[Agent Search CLI](https://github.com/r0botsorg/agent-search-cli)** | Open-source CLI and Python library (this repo) |
| **Qwerty API** | Hosted search API at `api.qwert.ai` — managed proxy infrastructure, no setup required |
| **Proxy Pool** | Community-powered proxy network — share bandwidth, earn credits |

### Pricing

| Plan | Price | Requests | What You Get |
|------|-------|----------|--------------|
| **Lite** | Free | 1,000/mo | Basic search, API access, community support |
| **Pro** | $49/mo | 50,000/mo | Managed proxies, semantic search, priority support, analytics |
| **Enterprise** | $999/mo | Unlimited | Dedicated infrastructure, SLA, SSO, custom integrations |

Start free at [qwert.ai](https://qwert.ai) or self-host the entire stack with the open-source repos.

### Contact

- **Email**: [hello@qwert.ai](mailto:hello@qwert.ai)
- **Website**: [qwert.ai](https://qwert.ai)
- **Docs**: [qwert.ai/docs](https://qwert.ai/docs)

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

<p align="center">Built by <a href="https://qwert.ai">Qwerty</a></p>
