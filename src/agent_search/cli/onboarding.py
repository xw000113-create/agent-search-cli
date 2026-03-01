"""
Onboarding wizard for first-time CLI users.
Creates account and gets API key automatically.
"""

import os
import sys
import json
import click
from typing import Optional
from pathlib import Path
import requests


CONFIG_DIR = Path.home() / ".config" / "agent-search"
CONFIG_FILE = CONFIG_DIR / "config.json"


def get_config():
    """Get user config, creating if needed."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def save_config(config):
    """Save user config."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    CONFIG_FILE.chmod(0o600)  # Secure permissions (after file exists)


def check_onboarding_complete():
    """Check if user has completed onboarding."""
    config = get_config()
    return bool(config.get("api_key"))


def should_run_onboarding():
    """Check if we should run onboarding."""
    # Skip if API key exists
    if check_onboarding_complete():
        return False

    # Skip in non-interactive mode
    if not sys.stdin.isatty():
        return False

    return True


def run_onboarding_wizard():
    """Interactive onboarding wizard."""
    click.echo()
    click.echo("=" * 60)
    click.echo("  Welcome to Agent Search!")
    click.echo("=" * 60)
    click.echo()
    click.echo("Let's get you set up. This will just take a moment.")
    click.echo()

    # Check if user already has an account
    click.echo("Do you already have a Qwerty account?")
    has_account = click.confirm("Sign in to existing account?", default=False)

    if has_account:
        return _onboarding_login()
    else:
        return _onboarding_signup()


def _onboarding_signup():
    """Create new account via CLI."""
    click.echo()
    click.echo("📝 Create your account")
    click.echo("-" * 40)

    email = click.prompt("Email address")
    password = click.prompt("Password", hide_input=True)
    confirm = click.prompt("Confirm password", hide_input=True)

    if password != confirm:
        click.echo("❌ Passwords don't match", err=True)
        return False

    click.echo()
    click.echo("🔑 Creating account...")

    try:
        # Register account via API
        api_url = os.getenv("AGENT_SEARCH_API", "https://api.qwert.ai")
        response = requests.post(
            f"{api_url}/auth/register",
            json={"email": email, "password": password},
            timeout=10,
        )

        if response.status_code == 201:
            data = response.json()
            api_key = data.get("api_key")

            # Save config
            config = get_config()
            config.update(
                {"email": email, "api_key": api_key, "tier": "free", "first_run": False}
            )
            save_config(config)

            # Ask about joining the pool
            click.echo()
            click.echo("Search Pool 🌊")
            click.echo("-" * 40)
            click.echo("Join the network to unlock unblocked search.")
            click.echo("Your IP helps power the Pool - you earn 1 credit/hour.")
            click.echo()

            join_pool = click.confirm(
                "Jump in the Pool? (can change later)", default=False
            )

            if join_pool:
                # Import and run pool join
                from agent_search.cli.commands.pool import execute_join

                execute_join()
                click.echo()
                click.echo("✅ Pool participation enabled!")
            else:
                config["pool_opted_out"] = True
                save_config(config)
                click.echo()
                click.echo("You can join anytime with: search pool join")

            # Ask about Pro signup
            click.echo()
            click.echo("Qwerty Pro 🚀")
            click.echo("-" * 40)
            click.echo("Priority proxies, unlimited searches, advanced extraction")
            click.echo()

            sign_up_pro = click.confirm("Sign up for Pro?", default=False)

            if sign_up_pro:
                click.echo()
                click.echo("🚀 Redirecting to Pro signup...")
                click.echo()
                # Open browser to pricing page
                import webbrowser

                webbrowser.open("https://qwert.ai/pricing")
                click.echo("Opening https://qwert.ai/pricing in your browser...")
                click.echo()
                click.echo(
                    "After subscribing, your Pro features will be activated automatically!"
                )
                click.echo()
                return True

            click.echo()
            click.echo("=" * 60)
            click.echo("✅ Account created successfully!")
            click.echo("=" * 60)
            click.echo()
            click.echo(f"📧 Email: {email}")
            click.echo(f"🔑 API Key: {api_key[:8]}...{api_key[-8:]}")
            click.echo()
            click.echo("You're all set! Start searching with:")
            click.echo('  search "your query here"')
            click.echo()
            click.echo("💡 Upgrade to Pro anytime at: https://qwert.ai/pricing")
            click.echo()

            return True

        elif response.status_code == 409:
            click.echo("❌ Email already registered", err=True)
            click.echo()
            if click.confirm("Sign in instead?", default=True):
                return _onboarding_login()
            return False
        else:
            error = response.json().get("detail", "Unknown error")
            click.echo(f"❌ Registration failed: {error}", err=True)
            return False

    except requests.exceptions.ConnectionError:
        click.echo()
        click.echo("⚠️  Couldn't connect to Agent Search servers.")
        click.echo()
        click.echo("You can:")
        click.echo("1. Try again later")
        click.echo("2. Use Lite mode (self-hosted, no account needed)")
        click.echo('   search "query" --lite')
        click.echo()
        click.echo("Or sign up on the website:")
        click.echo("   https://qwert.ai/signup")
        click.echo()

        if click.confirm("Continue with Lite mode?", default=True):
            config = get_config()
            config["tier"] = "lite"
            config["first_run"] = False
            save_config(config)
            click.echo("✅ Set up for Lite mode!")
            return True
        return False

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        return False


def _onboarding_login():
    """Login to existing account via CLI."""
    click.echo()
    click.echo("🔐 Sign in to your account")
    click.echo("-" * 40)

    email = click.prompt("Email address")
    password = click.prompt("Password", hide_input=True)

    click.echo()
    click.echo("🔑 Authenticating...")

    try:
        api_url = os.getenv("AGENT_SEARCH_API", "https://api.qwert.ai")
        response = requests.post(
            f"{api_url}/auth/login",
            data={"username": email, "password": password},
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            api_key = data.get("api_key")
            tier = data.get("tier", "free")

            # Save config
            config = get_config()
            config.update(
                {"email": email, "api_key": api_key, "tier": tier, "first_run": False}
            )
            save_config(config)

            click.echo()
            click.echo("=" * 60)
            click.echo("✅ Signed in successfully!")
            click.echo("=" * 60)
            click.echo()
            click.echo(f"📧 Email: {email}")
            click.echo(f"⭐ Tier: {tier.capitalize()}")
            click.echo()
            click.echo("You're all set! Start searching with:")
            click.echo('  search "your query here"')
            click.echo()

            if tier == "free":
                click.echo("💡 Upgrade to Pro: https://qwert.ai/pricing")

            return True
        else:
            click.echo("❌ Login failed. Check your credentials.", err=True)
            return False

    except requests.exceptions.ConnectionError:
        click.echo()
        click.echo("⚠️  Couldn't connect to Agent Search servers.")
        click.echo()
        click.echo("Continue with Lite mode (self-hosted):")
        config = get_config()
        config["tier"] = "lite"
        config["first_run"] = False
        save_config(config)
        return True

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        return False


def ensure_onboarded():
    """Ensure user is onboarded before running commands."""
    if should_run_onboarding():
        success = run_onboarding_wizard()
        if not success:
            click.echo()
            click.echo("Onboarding incomplete. Run 'search auth login' to try again.")
            return False
    return True


def get_api_key():
    """Get user's API key from config."""
    config = get_config()
    return config.get("api_key")


def get_tier():
    """Get user's tier from config."""
    config = get_config()
    return config.get("tier", "free")
