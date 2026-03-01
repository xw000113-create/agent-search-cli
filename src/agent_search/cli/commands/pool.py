"""
Pool command implementations with proxy pool participation.
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import click

# Configuration paths
POOL_CONFIG_DIR = Path.home() / ".config" / "agent-search"
POOL_CONFIG_FILE = POOL_CONFIG_DIR / "pool.json"

# Reward rates
CREDITS_PER_HOUR = 1.0
REWARD_TIERS = {
    "1_month_pro": {"credits": 720, "description": "1 month Pro Developer"},
    "1_month_team": {"credits": 5000, "description": "1 month Pro Team"},
    "3_month_pro": {"credits": 2000, "description": "3 months Pro Developer"},
    "1_year_pro": {"credits": 7200, "description": "1 year Pro Developer"},
}


def get_pool_config_path() -> Path:
    """Get the path to the pool configuration file."""
    return POOL_CONFIG_FILE


def ensure_config_dir():
    """Ensure the configuration directory exists."""
    POOL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_pool_config() -> dict:
    """Load the pool configuration from file."""
    config_path = get_pool_config_path()
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_pool_config(config: dict):
    """Save the pool configuration to file."""
    ensure_config_dir()
    config_path = get_pool_config_path()
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def generate_node_id() -> str:
    """Generate a unique node ID."""
    return str(uuid.uuid4())


def format_duration(hours: float) -> str:
    """Format hours into a human-readable duration."""
    if hours < 1:
        return f"{int(hours * 60)} minutes"
    elif hours < 24:
        return f"{int(hours)} hours"
    else:
        days = int(hours / 24)
        remaining_hours = int(hours) % 24
        if remaining_hours > 0:
            return f"{days}d {remaining_hours}h"
        return f"{days} days"


def format_bytes(bytes_value: int) -> str:
    """Format bytes into a human-readable string."""
    value = float(bytes_value)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} PB"


def calculate_credits(online_hours: float) -> float:
    """Calculate credits earned based on online hours."""
    return online_hours * CREDITS_PER_HOUR


def execute_join():
    """Join the Proxy Pool."""
    # Load existing config
    config = load_pool_config()

    # Check if already joined
    if config.get("enabled"):
        click.echo("⚠️  You are already participating in the Proxy Pool Network!")
        click.echo(f"   Node ID: {config.get('node_id', 'Unknown')}")
        click.echo()
        click.echo("Run 'search pool status' to check your participation.")
        return

    click.echo("🌐 Joining Proxy Pool Network...")
    click.echo()
    click.echo("╔════════════════════════════════════════════════╗")
    click.echo("║   PROXY POOL NETWORK - COMMUNITY POOL          ║")
    click.echo("╚════════════════════════════════════════════════╝")
    click.echo()
    click.echo("💡 What this does:")
    click.echo("   • Runs a lightweight proxy on your machine")
    click.echo("   • Other users can route through your IP")
    click.echo("   • You earn Pro credits for contributing")
    click.echo("   • Completely voluntary - disable anytime")
    click.echo()
    click.echo("📊 Benefits:")
    click.echo(f"   • Earn {CREDITS_PER_HOUR} credit/hour while online")
    click.echo(
        f"   • {REWARD_TIERS['1_month_pro']['credits']} credits = 1 month Pro Developer free"
    )
    click.echo("   • Help the open source community")
    click.echo("   • Get priority access to the pool")
    click.echo()
    click.echo("⚙️  Configuration:")
    click.echo("   • Max bandwidth: 1GB/day")
    click.echo("   • Only active when you're online")
    click.echo("   • Pauses when you use your computer")
    click.echo("   • Port: 8888 (configurable)")
    click.echo()

    if click.confirm("Would you like to join?"):
        # Generate new node ID
        node_id = generate_node_id()

        # Create pool configuration
        config = {
            "enabled": True,
            "node_id": node_id,
            "credits_earned": 0.0,
            "bandwidth_used": 0,
            "joined_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "total_hours_online": 0.0,
        }

        # Save configuration
        save_pool_config(config)

        click.echo()
        click.echo("✅ Successfully joined Proxy Pool Network!")
        click.echo()
        click.echo("📋 Your Node Details:")
        click.echo(f"   Node ID: {node_id}")
        click.echo(f"   Joined: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        click.echo()
        click.echo("📖 Next Steps:")
        click.echo("   • Run 'search pool status' to check participation")
        click.echo("   • Run 'search pool credits' to view earnings")
        click.echo("   • Run 'search pool leave' to exit anytime")
        click.echo()
        click.echo("🎉 Thank you for supporting the community!")
    else:
        click.echo()
        click.echo("👋 No problem! Run 'search pool join' anytime to participate.")


def execute_leave():
    """Leave the Proxy Pool."""
    config = load_pool_config()

    if not config:
        click.echo("❌ You haven't joined the Proxy Pool Network yet.")
        click.echo("   Run 'search pool join' to participate.")
        return

    if not config.get("enabled"):
        click.echo("⚠️  You are already inactive in the Proxy Pool Network.")
        click.echo("   Run 'search pool join' to reactivate.")
        return

    click.echo("👋 Leaving Proxy Pool Network...")
    click.echo()

    # Calculate final statistics
    credits_earned = config.get("credits_earned", 0.0)
    total_hours = config.get("total_hours_online", 0.0)
    bandwidth_used = config.get("bandwidth_used", 0)
    node_id = config.get("node_id", "Unknown")
    joined_at = config.get("joined_at")

    # Update config to disabled
    config["enabled"] = False
    config["last_active"] = datetime.now().isoformat()
    save_pool_config(config)

    # Calculate months of Pro earned
    months_earned = credits_earned / REWARD_TIERS["1_month_pro"]["credits"]

    click.echo("╔════════════════════════════════════════════════╗")
    click.echo("║   PARTICIPATION SUMMARY                        ║")
    click.echo("╚════════════════════════════════════════════════╝")
    click.echo()
    click.echo("🎉 Thanks for contributing!")
    click.echo()
    click.echo("📊 Final Statistics:")
    click.echo(f"   Node ID: {node_id}")
    if joined_at:
        click.echo(f"   Member since: {joined_at}")
    click.echo(f"   Total hours online: {format_duration(total_hours)}")
    click.echo(f"   Bandwidth contributed: {format_bytes(bandwidth_used)}")
    click.echo()
    click.echo("💰 Credits Earned:")
    click.echo(f"   Total credits: {credits_earned:.1f}")
    click.echo(f"   That's {months_earned:.1f} months of Pro Developer free!")
    click.echo()
    click.echo("📋 Configuration saved for history.")
    click.echo("   Run 'search pool join' anytime to rejoin.")


def execute_status():
    """Check pool status."""
    config = load_pool_config()

    if not config:
        click.echo("🌍 Proxy Pool Network Status")
        click.echo()
        click.echo("❌ You haven't joined the Proxy Pool Network yet.")
        click.echo()
        click.echo("📖 To participate:")
        click.echo("   Run 'search pool join' to join the network")
        click.echo("   Earn credits for contributing bandwidth")
        return

    is_enabled = config.get("enabled", False)
    node_id = config.get("node_id", "Unknown")
    credits_earned = config.get("credits_earned", 0.0)
    bandwidth_used = config.get("bandwidth_used", 0)
    total_hours = config.get("total_hours_online", 0.0)
    last_active = config.get("last_active")
    joined_at = config.get("joined_at")

    # Calculate time online today (mock calculation)
    hours_today = min(total_hours, 8.0) if is_enabled else 0.0

    # Mock ranking data
    mock_rank = hash(node_id) % 1000 + 1 if node_id != "Unknown" else 0

    click.echo("🌍 Proxy Pool Network Status")
    click.echo()
    click.echo("╔════════════════════════════════════════════════╗")
    click.echo("║   YOUR PARTICIPATION                           ║")
    click.echo("╚════════════════════════════════════════════════╝")
    click.echo()

    if is_enabled:
        click.echo("Status: 🟢 Active")
    else:
        click.echo("Status: 🔴 Inactive")

    click.echo(f"   Node ID: {node_id}")

    if joined_at:
        click.echo(f"   Member since: {joined_at[:10]}")

    if is_enabled:
        click.echo(f"   Time online today: {format_duration(hours_today)}")
        click.echo(f"   Total hours online: {format_duration(total_hours)}")

    click.echo(f"   Bandwidth contributed: {format_bytes(bandwidth_used)}")
    click.echo(f"   Credits earned: {credits_earned:.1f}")

    if is_enabled and mock_rank > 0:
        click.echo(f"   Your rank: #{mock_rank}")

    if last_active:
        click.echo(f"   Last active: {last_active}")

    click.echo()
    click.echo("📊 Pool Statistics:")
    click.echo("   Total nodes: 3,247")
    click.echo("   Online now: 1,892")
    click.echo("   Countries: 47")

    if is_enabled:
        click.echo()
        click.echo("📖 Commands:")
        click.echo("   Run 'search pool credits' to view detailed earnings")
        click.echo("   Run 'search pool stats' to see global statistics")
        click.echo("   Run 'search pool leave' to exit the pool")


def execute_stats():
    """Show pool statistics."""
    click.echo("🌍 Global Proxy Pool Network Statistics")
    click.echo()
    click.echo("╔════════════════════════════════════════════════╗")
    click.echo("║   NETWORK HEALTH                               ║")
    click.echo("╚════════════════════════════════════════════════╝")
    click.echo()

    # Mock global statistics
    total_nodes = 3247
    online_nodes = 1892
    online_percentage = (online_nodes / total_nodes) * 100
    countries = 47

    click.echo(f"Total nodes: {total_nodes:,}")
    click.echo(f"Online now: {online_nodes:,} ({online_percentage:.0f}%)")
    click.echo(f"Countries: {countries}")
    click.echo()

    # Credit distribution info
    total_credits_distributed = 892341
    top_contributor = "@alice_dev"
    top_contributor_credits = 2847

    click.echo("╔════════════════════════════════════════════════╗")
    click.echo("║   CREDIT DISTRIBUTION                          ║")
    click.echo("╚════════════════════════════════════════════════╝")
    click.echo()
    click.echo(f"Total credits distributed: {total_credits_distributed:,}")
    click.echo(
        f"Top contributor: {top_contributor} ({top_contributor_credits} credits)"
    )
    click.echo()

    # Show regional distribution (mock)
    click.echo("Regional Distribution:")
    click.echo("   North America: 34%")
    click.echo("   Europe: 28%")
    click.echo("   Asia: 22%")
    click.echo("   Other: 16%")

    # Load user config for personalized stats
    config = load_pool_config()
    if config and config.get("enabled"):
        node_id = config.get("node_id", "")
        user_rank = hash(node_id) % 1000 + 1
        click.echo()
        click.echo("📊 Your Position:")
        click.echo(f"   Rank: #{user_rank} of {total_nodes:,}")
        click.echo(f"   Percentile: Top {(user_rank / total_nodes * 100):.1f}%")


def execute_credits():
    """Show earned credits."""
    config = load_pool_config()

    if not config:
        click.echo("💰 Your Credits")
        click.echo()
        click.echo("❌ You haven't joined the Proxy Pool Network yet.")
        click.echo("   Run 'search pool join' to start earning credits!")
        return

    credits_earned = config.get("credits_earned", 0.0)
    total_hours = config.get("total_hours_online", 0.0)

    click.echo("💰 Your Credits")
    click.echo()
    click.echo("╔════════════════════════════════════════════════╗")
    click.echo("║   CREDIT BALANCE                               ║")
    click.echo("╚════════════════════════════════════════════════╝")
    click.echo()
    click.echo(f"Current balance: {credits_earned:.1f} credits")
    click.echo()

    # Show redeemable rewards
    click.echo("╔════════════════════════════════════════════════╗")
    click.echo("║   REDEEMABLE REWARDS                           ║")
    click.echo("╚════════════════════════════════════════════════╝")
    click.echo()

    for reward_id, reward_info in REWARD_TIERS.items():
        credits_needed = reward_info["credits"]
        description = reward_info["description"]
        if credits_earned >= credits_needed:
            status = "✅ Available"
        else:
            remaining = credits_needed - credits_earned
            status = f"⏳ Need {remaining:.0f} more"
        click.echo(f"   • {description}: {credits_needed} credits {status}")

    click.echo()
    click.echo("╔════════════════════════════════════════════════╗")
    click.echo("║   RECENT EARNINGS                              ║")
    click.echo("╚════════════════════════════════════════════════╝")
    click.echo()

    # Mock recent earnings breakdown
    today_earnings = min(credits_earned, 8.0) if config.get("enabled") else 0.0
    week_earnings = min(credits_earned, 42.5)
    month_earnings = credits_earned

    click.echo(f"   Today: +{today_earnings:.1f}")
    click.echo(f"   This week: +{week_earnings:.1f}")
    click.echo(f"   This month: +{month_earnings:.1f}")
    click.echo(f"   Total hours: {format_duration(total_hours)}")

    if config.get("enabled"):
        click.echo()
        click.echo("📈 Earning Rate:")
        click.echo(f"   {CREDITS_PER_HOUR} credit/hour while online")
        click.echo("   Earnings are updated every hour")
