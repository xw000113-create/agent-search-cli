"""
Extract command implementation.
"""

import click
import json
from typing import Optional
from agent_search.core.data_extraction import StructuredExtractor
from agent_search.core.html_to_markdown import HTMLToMarkdown


def execute_extract(url: str, pro: bool, schema: Optional[str], format: str):
    """Execute extraction."""
    click.echo(f"🔍 Extracting from {url}...", err=True)
    click.echo(f" Format: {format}", err=True)
    if schema:
        click.echo(f" Schema: {schema}", err=True)
    click.echo(f" Mode: {'Pro' if pro else 'Lite'}", err=True)

    try:
        # Use Lite mode by default
        extractor = StructuredExtractor()
        html_to_md = HTMLToMarkdown()

        click.echo("📡 Fetching page content...", err=True)

        # Get the HTML content
        content = html_to_md.fetch_and_convert(url)

        click.echo("🔍 Extracting structured data...", err=True)

        # Extract based on format/schema
        if schema:
            # Parse schema if provided
            try:
                schema_def = json.loads(schema)
                data = extractor.extract_with_schema(content, schema_def)
            except json.JSONDecodeError:
                click.echo("❌ Invalid schema JSON, using default extraction", err=True)
                data = extractor.extract(content)
        else:
            data = extractor.extract(content)

        # Output based on format
        if format == "json":
            result = json.dumps(data, indent=2)
        elif format == "yaml":
            try:
                import yaml

                result = yaml.dump(data, default_flow_style=False)
            except ImportError:
                result = json.dumps(data, indent=2)
        else:
            # Default to pretty text
            result = "\n".join([f"{k}: {v}" for k, v in data.items()])

        click.echo("\n✅ Extracted Data:")
        click.echo(result)

    except Exception as e:
        click.echo(f"❌ Extraction failed: {e}", err=True)
        click.echo("Extract not yet fully implemented")
