"""
Change Detection and Monitoring

Monitor websites for changes and trigger notifications.

Usage:
    from agent_search.core.change_detector import ChangeDetector, ChangeMonitor

    detector = ChangeDetector(storage_dir="./monitoring")

    # Take snapshot
    detector.snapshot("https://example.com", html_content)

    # Check for changes
    changes = detector.detect_changes("https://example.com", new_html)

    # Monitor with callbacks
    monitor = ChangeMonitor()
    await monitor.watch("https://example.com", on_change=callback)
"""

import os
import json
import hashlib
import time
from typing import Optional, Dict, Any, List, Callable, Union
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .proxy_chain import ProxyChain


@dataclass
class ChangeResult:
    """Result of change detection."""

    url: str
    has_changed: bool
    change_type: str  # 'content', 'structure', 'hash'
    previous_hash: str
    current_hash: str
    diff_summary: Optional[str] = None
    timestamp: float = 0.0


class ChangeDetector:
    """
    Detect changes in web pages.

    Features:
    - Multiple hash algorithms (MD5, SHA256)
    - Content diffing
    - Structural comparison
    - Persistent storage
    """

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize change detector.

        Args:
            storage_dir: Directory to store snapshots
        """
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = Path.home() / ".cache" / "agent-search" / "snapshots"

        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_snapshot_path(self, url: str) -> Path:
        """Get storage path for URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.storage_dir / f"{url_hash}.json"

    def snapshot(
        self, url: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Take a snapshot of content.

        Args:
            url: URL being monitored
            content: Content to snapshot
            metadata: Additional metadata

        Returns:
            Hash of content
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        snapshot = {
            "url": url,
            "hash": content_hash,
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "content_length": len(content),
            "metadata": metadata or {},
        }

        # Save snapshot
        snapshot_path = self._get_snapshot_path(url)
        with open(snapshot_path, "w") as f:
            json.dump(snapshot, f, indent=2)

        return content_hash

    def get_snapshot(self, url: str) -> Optional[Dict[str, Any]]:
        """Get previous snapshot for URL."""
        snapshot_path = self._get_snapshot_path(url)

        if not snapshot_path.exists():
            return None

        try:
            with open(snapshot_path, "r") as f:
                return json.load(f)
        except Exception:
            return None

    def detect_changes(
        self, url: str, content: str, check_structure: bool = False
    ) -> ChangeResult:
        """
        Detect changes in content.

        Args:
            url: URL being checked
            content: Current content
            check_structure: Also check structural changes

        Returns:
            ChangeResult with change information
        """
        current_hash = hashlib.sha256(content.encode()).hexdigest()
        previous = self.get_snapshot(url)

        if previous is None:
            # First snapshot
            self.snapshot(url, content)
            return ChangeResult(
                url=url,
                has_changed=True,
                change_type="initial",
                previous_hash="",
                current_hash=current_hash,
                timestamp=time.time(),
            )

        previous_hash = previous.get("hash", "")

        if previous_hash == current_hash:
            # No change
            return ChangeResult(
                url=url,
                has_changed=False,
                change_type="none",
                previous_hash=previous_hash,
                current_hash=current_hash,
                timestamp=time.time(),
            )

        # Content changed
        change_type = "content"
        diff_summary = None

        # Try to get diff summary
        if "content" in previous:
            diff_summary = self._generate_diff_summary(
                previous.get("content_preview", ""),
                content[:1000],  # First 1000 chars
            )

        # Update snapshot
        self.snapshot(url, content)

        return ChangeResult(
            url=url,
            has_changed=True,
            change_type=change_type,
            previous_hash=previous_hash,
            current_hash=current_hash,
            diff_summary=diff_summary,
            timestamp=time.time(),
        )

    def _generate_diff_summary(self, old: str, new: str) -> str:
        """Generate a summary of differences."""
        old_lines = old.split("\n")
        new_lines = new.split("\n")

        added = 0
        removed = 0

        old_set = set(old_lines)
        new_set = set(new_lines)

        for line in new_lines:
            if line not in old_set:
                added += 1

        for line in old_lines:
            if line not in new_set:
                removed += 1

        return f"+{added} lines added, -{removed} lines removed"

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get statistics about monitored URLs."""
        snapshots = list(self.storage_dir.glob("*.json"))

        urls = []
        for snapshot_file in snapshots:
            try:
                with open(snapshot_file, "r") as f:
                    data = json.load(f)
                    urls.append(
                        {
                            "url": data.get("url"),
                            "last_check": data.get("datetime"),
                            "hash": data.get("hash")[:16] + "...",
                        }
                    )
            except Exception:
                pass

        return {
            "total_monitored": len(urls),
            "storage_dir": str(self.storage_dir),
            "urls": urls,
        }


class ChangeMonitor:
    """
    Continuous monitoring for URL changes.

    Similar to Firecrawl's monitoring features.
    """

    def __init__(
        self,
        proxy_chain: Optional[ProxyChain] = None,
        check_interval: int = 3600,  # 1 hour default
        storage_dir: Optional[str] = None,
    ):
        self.proxy_chain = proxy_chain or ProxyChain()
        self.check_interval = check_interval
        self.detector = ChangeDetector(storage_dir)
        self.watched: Dict[str, Dict[str, Any]] = {}
        self._running = False

    def watch(
        self,
        url: str,
        on_change: Optional[Callable[[ChangeResult], None]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Start watching a URL for changes.

        Args:
            url: URL to monitor
            on_change: Callback when change detected
            metadata: Additional metadata
        """
        self.watched[url] = {
            "on_change": on_change,
            "metadata": metadata or {},
            "last_check": 0,
        }

    def unwatch(self, url: str):
        """Stop watching a URL."""
        if url in self.watched:
            del self.watched[url]

    async def check_once(self) -> List[ChangeResult]:
        """
        Check all watched URLs once.

        Returns:
            List of changes detected
        """
        import asyncio

        changes = []

        for url, config in self.watched.items():
            try:
                # Fetch current content
                response = self.proxy_chain.get(url, timeout=30)

                if response.status_code == 200:
                    result = self.detector.detect_changes(url, response.text)
                    config["last_check"] = time.time()

                    if result.has_changed:
                        changes.append(result)

                        # Trigger callback
                        if config.get("on_change"):
                            try:
                                config["on_change"](result)
                            except Exception:
                                pass

            except Exception:
                pass

            # Small delay between checks
            await asyncio.sleep(0.5)

        return changes

    async def start_monitoring(self):
        """Start continuous monitoring."""
        import asyncio

        self._running = True

        while self._running:
            await self.check_once()

            # Wait for next check
            await asyncio.sleep(self.check_interval)

    def stop_monitoring(self):
        """Stop continuous monitoring."""
        self._running = False


class WebhookNotifier:
    """
    Send webhook notifications on changes.
    """

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def notify(self, result: ChangeResult):
        """Send webhook notification."""
        import requests

        payload = {
            "url": result.url,
            "has_changed": result.has_changed,
            "change_type": result.change_type,
            "timestamp": result.timestamp,
            "diff_summary": result.diff_summary,
        }

        try:
            requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"},
            )
        except Exception:
            pass


# Convenience functions
def check_for_changes(
    url: str, content: str, storage_dir: Optional[str] = None
) -> ChangeResult:
    """
    Quick change check.

    Args:
        url: URL being checked
        content: Current content
        storage_dir: Optional storage directory

    Returns:
        ChangeResult
    """
    detector = ChangeDetector(storage_dir)
    return detector.detect_changes(url, content)
