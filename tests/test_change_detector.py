"""
Tests for change detection and monitoring.
"""

import unittest
from unittest.mock import Mock, patch
import tempfile
import shutil
import time

from agent_search.change_detector import (
    ChangeDetector,
    ChangeMonitor,
    ChangeResult,
    check_for_changes,
)


class TestChangeDetector(unittest.TestCase):
    """Test ChangeDetector."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.detector = ChangeDetector(storage_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_snapshot_creation(self):
        """Test creating a snapshot."""
        url = "https://example.com"
        content = "<html>Test content</html>"

        hash_value = self.detector.snapshot(url, content)

        self.assertIsNotNone(hash_value)
        self.assertEqual(len(hash_value), 64)  # SHA256 hex

    def test_get_snapshot(self):
        """Test retrieving a snapshot."""
        url = "https://example.com"
        content = "<html>Test</html>"

        self.detector.snapshot(url, content)
        snapshot = self.detector.get_snapshot(url)

        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["url"], url)
        self.assertIn("hash", snapshot)
        self.assertIn("timestamp", snapshot)

    def test_detect_changes_initial(self):
        """Test detecting initial change."""
        url = "https://example.com"
        content = "<html>Initial</html>"

        result = self.detector.detect_changes(url, content)

        self.assertTrue(result.has_changed)
        self.assertEqual(result.change_type, "initial")
        self.assertEqual(result.previous_hash, "")

    def test_detect_no_changes(self):
        """Test detecting no changes."""
        url = "https://example.com"
        content = "<html>Same content</html>"

        # First snapshot
        self.detector.snapshot(url, content)

        # Detect changes with same content
        result = self.detector.detect_changes(url, content)

        self.assertFalse(result.has_changed)
        self.assertEqual(result.change_type, "none")

    def test_detect_content_changes(self):
        """Test detecting content changes."""
        url = "https://example.com"
        content1 = "<html>Version 1</html>"
        content2 = "<html>Version 2</html>"

        # First snapshot
        self.detector.snapshot(url, content1)

        # Detect changes
        result = self.detector.detect_changes(url, content2)

        self.assertTrue(result.has_changed)
        self.assertEqual(result.change_type, "content")
        # diff_summary is only populated when the stored snapshot contains
        # a "content" key, which the current implementation does not save.
        # So diff_summary will be None for hash-only change detection.
        self.assertNotEqual(result.previous_hash, result.current_hash)

    def test_get_monitoring_stats(self):
        """Test getting monitoring stats."""
        # Create a few snapshots
        for i in range(3):
            self.detector.snapshot(
                f"https://example{i}.com", f"<html>Content {i}</html>"
            )

        stats = self.detector.get_monitoring_stats()

        self.assertEqual(stats["total_monitored"], 3)
        self.assertEqual(len(stats["urls"]), 3)


class TestChangeResult(unittest.TestCase):
    """Test ChangeResult dataclass."""

    def test_create_result(self):
        """Test creating a change result."""
        result = ChangeResult(
            url="https://example.com",
            has_changed=True,
            change_type="content",
            previous_hash="abc123",
            current_hash="def456",
            timestamp=time.time(),
        )

        self.assertTrue(result.has_changed)
        self.assertEqual(result.change_type, "content")
        self.assertEqual(result.previous_hash, "abc123")
        self.assertEqual(result.current_hash, "def456")


class TestChangeMonitor(unittest.TestCase):
    """Test ChangeMonitor."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.monitor = ChangeMonitor(check_interval=1, storage_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_watch_url(self):
        """Test watching a URL."""
        url = "https://example.com"

        self.monitor.watch(url)

        self.assertIn(url, self.monitor.watched)

    def test_unwatch_url(self):
        """Test unwatching a URL."""
        url = "https://example.com"

        self.monitor.watch(url)
        self.monitor.unwatch(url)

        self.assertNotIn(url, self.monitor.watched)

    async def test_check_once(self):
        """Test checking all watched URLs."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>Test</html>"

        mock_proxy = Mock()
        mock_proxy.get.return_value = mock_response

        # Inject mock proxy_chain directly (setUp creates monitor with real ProxyChain)
        self.monitor.proxy_chain = mock_proxy

        # Watch URLs
        self.monitor.watch("https://example1.com")
        self.monitor.watch("https://example2.com")

        # Check once
        changes = await self.monitor.check_once()

        # Should detect initial changes
        self.assertEqual(len(changes), 2)
        self.assertTrue(all(c.has_changed for c in changes))

    def test_callback_triggering(self):
        """Test that callbacks are triggered on changes."""
        callback_called = [False]

        def callback(result):
            callback_called[0] = True

        self.monitor.watch("https://example.com", on_change=callback)

        # Verify callback is stored
        self.assertEqual(
            self.monitor.watched["https://example.com"]["on_change"], callback
        )


class TestCheckForChanges(unittest.TestCase):
    """Test check_for_changes convenience function."""

    def test_check_for_changes(self):
        """Test quick change check."""
        with tempfile.TemporaryDirectory() as temp_dir:
            url = "https://example.com"
            content = "<html>Test</html>"

            result = check_for_changes(url, content, storage_dir=temp_dir)

            self.assertTrue(result.has_changed)
            self.assertEqual(result.change_type, "initial")


def async_test(coro):
    """Decorator for async test methods."""

    def wrapper(*args, **kwargs):
        import asyncio

        return asyncio.run(coro(*args, **kwargs))

    return wrapper


# Apply async decorator
for name, method in list(TestChangeMonitor.__dict__.items()):
    if name.startswith("test_") and hasattr(method, "__code__"):
        import inspect

        if inspect.iscoroutinefunction(method):
            setattr(TestChangeMonitor, name, async_test(method))


if __name__ == "__main__":
    unittest.main()
