"""
Crawl command implementation.
"""

import click
from agent_search.core.sitemap_crawler import SitemapCrawler
from agent_search.core.html_to_markdown import HTMLToMarkdown


def execute_crawl(url: str, pro: bool, depth: int, max_pages: int):
    """Execute a crawl."""
    click.echo(f"🕷️ Crawling {url}...", err=True)
    click.echo(f" Depth: {depth}", err=True)
    click.echo(f" Max pages: {max_pages}", err=True)
    click.echo(f" Mode: {'Pro' if pro else 'Lite'}", err=True)

    try:
        # Use Lite mode by default
        crawler = SitemapCrawler()
        html_to_md = HTMLToMarkdown()

        click.echo("📡 Starting crawl...", err=True)

        # Fetch URLs from sitemap
        urls = crawler.discover_urls(url, max_urls=max_pages)

        click.echo(f"✅ Found {len(urls)} URLs to crawl", err=True)
        click.echo("\n---")

        for i, page_url in enumerate(urls[:max_pages], 1):
            try:
                click.echo(f"\n[{i}/{min(len(urls), max_pages)}] {page_url}", err=True)
                content = html_to_md.fetch_and_convert(page_url)
                click.echo(f"✓ {page_url}")
                click.echo(f"```markdown")
                click.echo(content[:500] + "..." if len(content) > 500 else content)
                click.echo(f"```")
                click.echo(f"---")
            except Exception as e:
                click.echo(f"❌ Error crawling {page_url}: {e}", err=True)

    except Exception as e:
        click.echo(f"❌ Crawl failed: {e}", err=True)
        click.echo("Crawl not yet fully implemented")
