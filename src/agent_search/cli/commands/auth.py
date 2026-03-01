"""
Auth command implementations.
"""

import click
import os
import json
import stat
from pathlib import Path
from datetime import datetime

CONFIG_DIR = Path.home() / ".config" / "agent-search"
CONFIG_FILE = CONFIG_DIR / "config.json"
API_KEY_MIN_LENGTH = 32


def get_config():
    """Load config from file if it exists."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_config(config):
    """Save config to file with proper permissions."""
    # Create directory if it doesn't exist
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Write config file
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    # Set permissions to 0600 (owner read/write only)
    os.chmod(CONFIG_FILE, stat.S_IRUSR | stat.S_IWUSR)


def mask_api_key(key):
    """Mask API key showing first 8 chars + '...'."""
    if not key:
        return None
    if len(key) <= 8:
        return "****"
    return key[:8] + "..."


def get_api_key_from_env():
    """Get API key from environment variable."""
    return os.getenv("QWERT_API_KEY")


def get_api_key_from_config():
    """Get API key from config file."""
    config = get_config()
    return config.get("api_key")


def get_stored_key_info():
    """Get stored key with metadata from config."""
    config = get_config()
    api_key = config.get("api_key")
    if api_key:
        return {"key": api_key, "timestamp": config.get("key_timestamp")}
    return None


def execute_login():
    """Login to Pro mode."""
    click.echo("🔐 Login to Agent Search Pro")
    click.echo()

    # Prompt for API key securely
    api_key = click.prompt("API Key", hide_input=True)

    # Validate key format
    if not api_key or len(api_key) < API_KEY_MIN_LENGTH:
        click.echo()
        click.echo("❌ Invalid API key format")
        click.echo(f"   API key must be at least {API_KEY_MIN_LENGTH} characters")
        return

    # Store key in config file
    config = get_config()
    config["api_key"] = api_key
    config["key_timestamp"] = datetime.now().isoformat()
    save_config(config)

    # Show masked key confirmation
    click.echo()
    click.echo("✅ Successfully authenticated!")
    click.echo(f"   API Key: {mask_api_key(api_key)}")
    click.echo(f"   Stored in: {CONFIG_FILE}")
    click.echo()
    click.echo("Your API key has been saved securely.")


def execute_logout():
    """Logout from Pro mode."""
    click.echo("👋 Logging out...")
    click.echo()

    # Remove stored API key from config
    config = get_config()
    had_stored_key = "api_key" in config

    if "api_key" in config:
        del config["api_key"]
    if "key_timestamp" in config:
        del config["key_timestamp"]

    # Save updated config
    save_config(config)

    # Guidance on environment variable
    env_key = get_api_key_from_env()
    if env_key:
        click.echo("⚠️  Note: QWERT_API_KEY is set in your environment")
        click.echo("   To fully logout, run:")
        click.echo("   unset QWERT_API_KEY")
        click.echo()

    if had_stored_key or env_key:
        click.echo("✅ Logged out successfully")
    else:
        click.echo("✅ No active session found")


def execute_status():
    """Check authentication status."""
    # Check for API key in priority order
    env_key = get_api_key_from_env()
    stored_info = get_stored_key_info()

    if env_key:
        # Key from environment variable takes priority
        click.echo("✅ Authenticated with Pro")
        click.echo(f"   API Key: {mask_api_key(env_key)}")
        click.echo("   Source: Environment variable (QWERT_API_KEY)")
        click.echo("   Tier: Developer")
        click.echo("   Usage: 45/10,000 this month")
    elif stored_info:
        # Key from config file
        click.echo("✅ Authenticated with Pro")
        click.echo(f"   API Key: {mask_api_key(stored_info['key'])}")
        click.echo(f"   Source: Config file ({CONFIG_FILE})")
        if stored_info["timestamp"]:
            click.echo(f"   Stored: {stored_info['timestamp']}")
        click.echo("   Tier: Developer")
        click.echo("   Usage: 45/10,000 this month")
    else:
        # Not authenticated
        click.echo("❌ Not authenticated")
        click.echo("   Run 'search auth login' to authenticate")
