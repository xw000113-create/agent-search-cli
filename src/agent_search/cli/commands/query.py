"""
Query command implementation.
"""

import os
import click
from typing import Optional
from agent_search.core.proxy_chain import ProxyChain
from agent_search.core.html_to_markdown import HTMLToMarkdown


def execute_query(
    query: str,
    pro: bool,
    format: str,
    output: Optional[str],
    extract: Optional[str],
    browser: bool,
):
    """Execute a search query."""

    click.echo(f"🔍 Searching: {query}", err=True)

    try:
        # Get search URL from environment or use default
        search_endpoint = os.getenv("AGENT_SEARCH_ENDPOINT", "http://localhost:15000")
        search_url = f"{search_endpoint}/search?q={query}"
        click.echo("📡 Fetching results...", err=True)

        if pro:
            # Pro mode - use hosted API (placeholder implementation)
            click.echo("🚀 Using Pro mode (hosted)...", err=True)
            api_key = os.getenv("AGENT_SEARCH_API_KEY")
            if not api_key:
                click.echo(
                    "⚠️  No API key found. Set AGENT_SEARCH_API_KEY environment variable.",
                    err=True,
                )
                click.echo("   Falling back to Lite mode...", err=True)
            else:
                # In production, this would call the Pro API
                click.echo(f"   API Key: {api_key[:8]}...", err=True)

        # Use Lite mode (self-hosted) - fetch JSON from Whoogle
        import requests

        # Fetch JSON results from Whoogle
        click.echo(f" URL: {search_url}", err=True)
        headers = {"Accept": "application/json"}
        response = requests.get(search_url, headers=headers, timeout=30)
        data = response.json()

        # Parse results
        results = data.get("results", [])

        # Format based on output format
        if format == "json":
            import json

            result = json.dumps(data, indent=2)
        elif format == "html":
            # Build HTML output
            html_parts = [f"<h1>Search Results for: {query}</h1>"]
            for item in results[:10]:
                title = item.get("title", "Untitled")
                url = item.get("href", item.get("url", "#"))
                content = item.get("content", item.get("text", ""))
                html_parts.append(f'<div class="result">')
                html_parts.append(f'<h3><a href="{url}">{title}</a></h3>')
                html_parts.append(f"<p>{content[:300]}...</p>")
                html_parts.append(f"<small>{url}</small>")
                html_parts.append("</div>")
            result = "\n".join(html_parts)
        else:
            # Markdown format (default)
            md_parts = [f"# Search Results for: {query}\n"]
            md_parts.append(f"Found {len(results)} results\n")

            for i, item in enumerate(results[:10], 1):
                title = item.get("title", "Untitled")
                url = item.get("href", item.get("url", "#"))
                content = item.get("content", item.get("text", ""))

                md_parts.append(f"## {i}. {title}")
                md_parts.append(f"**URL:** {url}")
                md_parts.append(f"\n{content[:300]}...\n")

            result = "\n".join(md_parts)

        if output:
            with open(output, "w") as f:
                f.write(result)
            click.echo(f"✅ Results saved to: {output}", err=True)
        else:
            click.echo(result)

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        # Fallback to placeholder
        search_endpoint = os.getenv("AGENT_SEARCH_ENDPOINT", "http://localhost:15000")
        result = f"""# Search Results for: {query}

This is a placeholder. In production, this would return:
- Full page content in {format} format
- Extracted data (if --extract was used)
- Clean, structured content ready for AI consumption

Error: {e}

💡 Troubleshooting:
- Ensure Whoogle is running at {search_endpoint}
- For Pro mode, set AGENT_SEARCH_API_KEY environment variable
- Check your network connection and proxy settings
- To start Whoogle locally: pip install whoogle-search && whooogle
"""
        if output:
            with open(output, "w") as f:
                f.write(result)
            click.echo(f"✅ Results saved to: {output}", err=True)
        else:
            click.echo(result)
