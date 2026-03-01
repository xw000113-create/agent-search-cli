"""
Monitor command implementation.

Monitor a URL for changes and display updates when detected.
"""

import time
import sys
from datetime import datetime
from typing import Optional

import click

from agent_search.core.change_detector import ChangeDetector, ChangeResult
from agent_search.core.proxy_chain import ProxyChain


def format_interval(seconds: int) -> str:
    """Format interval in human-readable form."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    else:
        return f"{seconds // 3600}h"


def display_change(result: ChangeResult, index: int):
    """Display a detected change in a nice format."""
    timestamp = datetime.fromtimestamp(result.timestamp).strftime("%Y-%m-%d %H:%M:%S")

    click.echo()
    click.echo("=" * 60)
    click.echo(f"🔔 CHANGE DETECTED (#{index})")
    click.echo("=" * 60)
    click.echo(f"📍 URL: {result.url}")
    click.echo(f"🕐 Time: {timestamp}")
    click.echo(f"📊 Change Type: {result.change_type}")
    click.echo()
    click.echo("🔐 Hash Comparison:")
    click.echo(f"   Previous: {result.previous_hash[:16]}...")
    click.echo(f"   Current:  {result.current_hash[:16]}...")

    if result.diff_summary:
        click.echo()
        click.echo(f"📋 Diff Summary: {result.diff_summary}")

    click.echo("=" * 60)
    click.echo()


def display_status(
    url: str,
    mode: str,
    interval: int,
    check_count: int,
    changes_detected: int,
    last_check: Optional[float],
    is_running: bool,
):
    """Display current monitoring status."""
    status_icon = "🟢" if is_running else "🔴"
    status_text = "RUNNING" if is_running else "STOPPED"

    click.echo()
    click.echo("─" * 60)
    click.echo(f"{status_icon} Monitoring Status: {status_text}")
    click.echo("─" * 60)
    click.echo(f"📍 URL: {url}")
    click.echo(f"⚙️  Mode: {mode}")
    click.echo(f"⏱️  Interval: {format_interval(interval)}")
    click.echo(f"🔍 Checks: {check_count}")
    click.echo(f"🔄 Changes: {changes_detected}")

    if last_check:
        last_check_str = datetime.fromtimestamp(last_check).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        click.echo(f"🕐 Last Check: {last_check_str}")
    else:
        click.echo("🕐 Last Check: Never")

    click.echo("─" * 60)
    click.echo()


def execute_monitor_lite(url: str, interval: int):
    """
    Execute monitoring in Lite mode (local).

    Uses ChangeDetector for persistent storage and change detection.
    """
    detector = ChangeDetector()
    proxy = ProxyChain()

    check_count = 0
    changes_detected = 0
    last_check: Optional[float] = None
    is_running = True

    click.echo()
    click.echo("🚀 Starting Change Monitor (Lite Mode)")
    click.echo("=" * 60)
    click.echo(f"📍 URL: {url}")
    click.echo(f"⏱️  Check Interval: {format_interval(interval)}")
    click.echo(f"💾 Storage: {detector.storage_dir}")
    click.echo("=" * 60)
    click.echo()
    click.echo("Press Ctrl+C to stop monitoring")
    click.echo()

    # Take initial snapshot
    click.echo("📸 Taking initial snapshot...")
    try:
        response = proxy.get(url, timeout=30)
        if response.status_code == 200:
            initial_result = detector.detect_changes(url, response.text)
            if initial_result.change_type == "initial":
                click.echo(
                    f"✅ Initial snapshot saved (hash: {initial_result.current_hash[:16]}...)"
                )
            else:
                click.echo(
                    f"✅ Previous snapshot found (hash: {initial_result.current_hash[:16]}...)"
                )
        else:
            click.echo(f"❌ Failed to fetch URL: HTTP {response.status_code}", err=True)
            return
    except Exception as e:
        click.echo(f"❌ Error taking initial snapshot: {e}", err=True)
        return

    click.echo()
    click.echo(
        f"⏳ Starting monitoring loop (checking every {format_interval(interval)})..."
    )
    click.echo()

    try:
        while is_running:
            check_count += 1
            current_time = time.time()

            # Show status before check
            display_status(
                url=url,
                mode="Lite (Local)",
                interval=interval,
                check_count=check_count,
                changes_detected=changes_detected,
                last_check=last_check,
                is_running=True,
            )

            click.echo(
                f"🔍 Check #{check_count} at {datetime.now().strftime('%H:%M:%S')}..."
            )

            try:
                # Fetch current content
                response = proxy.get(url, timeout=30)

                if response.status_code == 200:
                    # Check for changes
                    result = detector.detect_changes(url, response.text)
                    last_check = current_time

                    if result.has_changed and result.change_type != "initial":
                        changes_detected += 1
                        display_change(result, changes_detected)
                    else:
                        click.echo(
                            f"✓ No changes detected (hash: {result.current_hash[:16]}...)"
                        )

                else:
                    click.echo(
                        f"⚠️  HTTP {response.status_code} - will retry next cycle",
                        err=True,
                    )

            except Exception as e:
                click.echo(f"⚠️  Error during check: {e}", err=True)

            click.echo()
            click.echo(f"⏳ Sleeping for {format_interval(interval)}...")
            click.echo("-" * 60)

            # Sleep with interruption handling
            try:
                time.sleep(interval)
            except KeyboardInterrupt:
                is_running = False
                break

    except KeyboardInterrupt:
        is_running = False

    # Final status
    click.echo()
    click.echo("\n" + "=" * 60)
    click.echo("🛑 Monitoring Stopped")
    click.echo("=" * 60)
    display_status(
        url=url,
        mode="Lite (Local)",
        interval=interval,
        check_count=check_count,
        changes_detected=changes_detected,
        last_check=last_check,
        is_running=False,
    )

    # Show stats
    stats = detector.get_monitoring_stats()
    click.echo(f"📊 Total URLs monitored: {stats['total_monitored']}")
    click.echo(f"💾 Snapshots stored in: {stats['storage_dir']}")


def execute_monitor_pro(url: str, interval: int):
    """
    Execute monitoring in Pro mode (API).

    Placeholder for Pro mode implementation using hosted service.
    """
    click.echo()
    click.echo("🚀 Starting Change Monitor (Pro Mode)")
    click.echo("=" * 60)
    click.echo(f"📍 URL: {url}")
    click.echo(f"⏱️  Check Interval: {format_interval(interval)}")
    click.echo("=" * 60)
    click.echo()
    click.echo("ℹ️  Pro Mode uses the hosted monitoring service.")
    click.echo("🔗 Connecting to Agent Search API...")
    click.echo()
    click.echo("⚠️  Pro mode monitoring is not yet implemented.")
    click.echo("   Falling back to Lite mode...")
    click.echo()

    # Fall back to Lite mode
    execute_monitor_lite(url, interval)


def execute_monitor(url: str, pro: bool, interval: int):
    """
    Execute monitoring for a URL.

    Args:
        url: URL to monitor
        pro: Use Pro mode (hosted API) if True, else Lite mode (local)
        interval: Check interval in seconds
    """
    click.echo(f"👁️ Monitoring {url}...")
    click.echo(f" Interval: {format_interval(interval)}")
    click.echo(f" Mode: {'Pro' if pro else 'Lite'}")

    if pro:
        execute_monitor_pro(url, interval)
    else:
        execute_monitor_lite(url, interval)
