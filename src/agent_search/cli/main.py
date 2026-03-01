"""
Main CLI implementation for Agent Search.
"""

import click
import sys
from typing import Optional

from agent_search.utils.version import get_version
from agent_search.utils.logger import setup_logging


class SearchGroup(click.Group):
    """Custom group that prioritises subcommand resolution over the optional
    ``query`` argument.

    Click normally parses positional arguments *before* trying to resolve a
    subcommand name.  Because the top-level group declares an optional
    ``query`` argument, words like ``auth`` and ``pool`` are consumed as
    the argument value instead of being matched to their respective
    subgroups.  This class overrides ``parse_args`` to check whether the
    first non-option token is a registered command name and, if so,
    temporarily strips the optional argument so Click proceeds to command
    resolution instead.
    """

    def parse_args(self, ctx, args):
        # Find the first positional (non-option) token
        is_subcommand = False
        for token in args:
            if token.startswith("-"):
                continue
            if token in self.commands:
                is_subcommand = True
            break

        if is_subcommand:
            # Temporarily remove the optional 'query' argument so Click
            # doesn't swallow the subcommand name.
            original_params = self.params
            self.params = [p for p in self.params if p.name != "query"]
            try:
                result = super().parse_args(ctx, args)
            finally:
                self.params = original_params
            # Ensure 'query' key exists in ctx.params so the callback
            # doesn't blow up with a missing-argument TypeError.
            ctx.params.setdefault("query", None)
            return result
        else:
            return super().parse_args(ctx, args)


@click.group(cls=SearchGroup, invoke_without_command=True)
@click.version_option(version=get_version(), prog_name="search")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--config", type=click.Path(), help="Path to config file")
@click.option("--skip-onboarding", is_flag=True, help="Skip onboarding wizard")
@click.argument("query", required=False)
@click.pass_context
def cli(
    ctx,
    verbose: bool,
    config: Optional[str],
    skip_onboarding: bool,
    query: Optional[str],
):
    """
    Agent Search - Web search for AI agents.

    Lite: Self-hosted (free) - you manage proxies
    Pro: Hosted service (paid) - we manage proxies
    Pool: Community-powered proxy network

    Quick Start:
    search "Python asyncio documentation"
    search "React hooks" --format json
    search pool join

    Examples:
    \b
    # Search (Lite mode)
    search "Python docs"

    \b
    # Search (Pro mode)
    search "Python docs" --pro

    \b
    # Crawl website
    search crawl https://example.com

    \b
    # Join Proxy Pool
    search pool join
    """
    setup_logging(verbose=verbose)
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config_path"] = config

    # Run onboarding on first use (unless skipped or a subcommand is being invoked)
    if not skip_onboarding and not query and ctx.invoked_subcommand is None:
        from agent_search.cli.onboarding import ensure_onboarded

        if not ensure_onboarded():
            sys.exit(1)

    # If query argument provided and no subcommand, treat as search query
    if query and ctx.invoked_subcommand is None:
        # Forward to query command
        ctx.invoke(
            query_cmd,
            query=query,
            pro=False,
            format="markdown",
            output=None,
            extract=None,
            browser=False,
        )


@cli.command(name="query")
@click.argument("query")
@click.option("--pro", is_flag=True, help="Use Pro mode (hosted)")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["markdown", "html", "json"]),
    default="markdown",
    help="Output format",
)
@click.option("--output", "-o", type=click.Path(), help="Output file")
@click.option("--extract", help="CSS selectors to extract")
@click.option("--browser/--no-browser", default=False, help="Use browser rendering")
def query_cmd(
    query: str,
    pro: bool,
    format: str,
    output: Optional[str],
    extract: Optional[str],
    browser: bool,
):
    """Search the web for a query."""
    from agent_search.cli.commands.query import execute_query

    execute_query(query, pro, format, output, extract, browser)


@cli.command()
@click.argument("url")
@click.option("--pro", is_flag=True, help="Use Pro mode")
@click.option("--depth", default=2, help="Crawl depth")
@click.option("--max-pages", default=50, help="Max pages to crawl")
def crawl(url: str, pro: bool, depth: int, max_pages: int):
    """Crawl a website."""
    from agent_search.cli.commands.crawl import execute_crawl

    execute_crawl(url, pro, depth, max_pages)


@cli.command()
@click.argument("url")
@click.option("--pro", is_flag=True, help="Use Pro mode")
@click.option("--schema", type=click.Path(), help="JSON schema file")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["markdown", "json"]),
    default="json",
    help="Output format",
)
def extract(url: str, pro: bool, schema: Optional[str], format: str):
    """Extract structured data from a URL."""
    from agent_search.cli.commands.extract import execute_extract

    execute_extract(url, pro, schema, format)


@cli.command()
@click.argument("url")
@click.option("--pro", is_flag=True, help="Use Pro mode")
@click.option("--interval", default=3600, help="Check interval in seconds")
def monitor(url: str, pro: bool, interval: int):
    """Monitor a URL for changes."""
    from agent_search.cli.commands.monitor import execute_monitor

    execute_monitor(url, pro, interval)


@cli.group()
def pool():
    """Manage Proxy Pool Network participation."""
    pass


@pool.command()
def join():
    """Join the Proxy Pool Network."""
    from agent_search.cli.commands.pool import execute_join

    execute_join()


@pool.command()
def leave():
    """Leave the Proxy Pool Network."""
    from agent_search.cli.commands.pool import execute_leave

    execute_leave()


@pool.command()
def status():
    """Check pool participation status."""
    from agent_search.cli.commands.pool import execute_status

    execute_status()


@pool.command()
def stats():
    """View global pool statistics."""
    from agent_search.cli.commands.pool import execute_stats

    execute_stats()


@pool.command()
def credits():
    """View your earned credits."""
    from agent_search.cli.commands.pool import execute_credits

    execute_credits()


@cli.group()
def auth():
    """Manage authentication for Pro mode."""
    pass


@auth.command()
def login():
    """Login to Pro mode."""
    from agent_search.cli.commands.auth import execute_login

    execute_login()


@auth.command()
def logout():
    """Logout from Pro mode."""
    from agent_search.cli.commands.auth import execute_logout

    execute_logout()


@auth.command()
def status():
    """Check authentication status."""
    from agent_search.cli.commands.auth import execute_status

    execute_status()


@cli.command()
def onboard():
    """Run the onboarding wizard (create account & get API key)."""
    from agent_search.cli.onboarding import run_onboarding_wizard

    success = run_onboarding_wizard()
    if not success:
        sys.exit(1)


def main():
    """Entry point for 'search' command."""
    try:
        return cli()
    except click.ClickException as e:
        e.show()
        return e.exit_code
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        return 1


def main_alias():
    """Entry point for legacy 'agent-search' command."""
    click.echo("Note: 'agent-search' is deprecated. Use 'search' instead.", err=True)
    return main()
