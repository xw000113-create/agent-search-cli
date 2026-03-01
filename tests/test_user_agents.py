"""
Tests for user agent module.
"""

import unittest

from agent_search.user_agents import (
    UserAgentRotator,
    get_user_agent_rotator,
    get_random_user_agent,
)


class TestUserAgentRotator(unittest.TestCase):
    """Test UserAgentRotator."""

    def setUp(self):
        """Set up test fixtures."""
        self.rotator = UserAgentRotator()

    def test_initialization(self):
        """Test initialization."""
        self.assertIsNotNone(self.rotator.user_agents)
        self.assertGreater(len(self.rotator.user_agents), 0)

    def test_get_random(self):
        """Test getting random user agent."""
        ua1 = self.rotator.get_random()
        ua2 = self.rotator.get_random()

        self.assertIsInstance(ua1, str)
        self.assertGreater(len(ua1), 10)

        # Could be same or different (it's random)
        self.assertIsInstance(ua2, str)

    def test_get_sequential(self):
        """Test getting sequential user agent."""
        ua1 = self.rotator.get_sequential()
        ua2 = self.rotator.get_sequential()

        # Should be different
        self.assertNotEqual(ua1, ua2)

        # Should cycle through
        initial_count = len(self.rotator.user_agents)
        for i in range(initial_count + 1):
            ua = self.rotator.get_sequential()
            self.assertIsInstance(ua, str)

    def test_get_by_browser(self):
        """Test getting user agent by browser."""
        chrome_ua = self.rotator.get_by_browser("chrome")
        firefox_ua = self.rotator.get_by_browser("firefox")

        self.assertIsNotNone(chrome_ua)
        self.assertIsNotNone(firefox_ua)

        self.assertIn("Chrome", chrome_ua)
        self.assertIn("Firefox", firefox_ua)

    def test_get_by_platform(self):
        """Test getting user agent by platform."""
        mac_ua = self.rotator.get_by_platform("macintosh")
        windows_ua = self.rotator.get_by_platform("windows")

        self.assertIsNotNone(mac_ua)
        self.assertIsNotNone(windows_ua)

        self.assertIn("Macintosh", mac_ua)
        self.assertIn("Windows", windows_ua)

    def test_get_desktop(self):
        """Test getting desktop user agent."""
        ua = self.rotator.get_desktop()

        self.assertIsInstance(ua, str)
        self.assertNotIn("Mobile", ua)

    def test_get_mobile(self):
        """Test getting mobile user agent."""
        ua = self.rotator.get_mobile()

        self.assertIsInstance(ua, str)
        self.assertIn("Mobile", ua)

    def test_shuffle(self):
        """Test shuffling user agents."""
        original_order = self.rotator.user_agents.copy()

        self.rotator.shuffle()

        # Should be shuffled
        self.assertTrue(self.rotator._shuffled)
        # Could be same or different, but shuffle should have been called

    def test_invalid_browser(self):
        """Test getting user agent for invalid browser."""
        ua = self.rotator.get_by_browser("invalid_browser")

        self.assertIsNone(ua)

    def test_invalid_platform(self):
        """Test getting user agent for invalid platform."""
        ua = self.rotator.get_by_platform("invalid_platform")

        self.assertIsNone(ua)


class TestGetUserAgentRotator(unittest.TestCase):
    """Test get_user_agent_rotator function."""

    def test_singleton(self):
        """Test singleton behavior."""
        rotator1 = get_user_agent_rotator()
        rotator2 = get_user_agent_rotator()

        self.assertIs(rotator1, rotator2)

    def test_returns_rotator(self):
        """Test returns UserAgentRotator."""
        rotator = get_user_agent_rotator()

        self.assertIsInstance(rotator, UserAgentRotator)


class TestGetRandomUserAgent(unittest.TestCase):
    """Test get_random_user_agent function."""

    def test_returns_string(self):
        """Test returns a string."""
        ua = get_random_user_agent()

        self.assertIsInstance(ua, str)
        self.assertGreater(len(ua), 10)

    def test_different_calls(self):
        """Test different calls return different agents (usually)."""
        ua1 = get_random_user_agent()
        ua2 = get_random_user_agent()

        # Both should be valid user agents
        self.assertIsInstance(ua1, str)
        self.assertIsInstance(ua2, str)


class TestUserAgentContent(unittest.TestCase):
    """Test user agent content validity."""

    def test_all_uas_valid(self):
        """Test all user agents are valid strings."""
        rotator = UserAgentRotator()

        for ua in rotator.user_agents:
            self.assertIsInstance(ua, str)
            self.assertGreater(len(ua), 10)
            self.assertIn("Mozilla", ua)

    def test_contains_browsers(self):
        """Test user agents contain various browsers."""
        rotator = UserAgentRotator()

        browsers = ["Chrome", "Firefox", "Safari", "Edg"]
        found_browsers = set()

        for ua in rotator.user_agents:
            for browser in browsers:
                if browser in ua:
                    found_browsers.add(browser)

        # Should find most common browsers
        self.assertGreater(len(found_browsers), 2)

    def test_contains_platforms(self):
        """Test user agents contain various platforms."""
        rotator = UserAgentRotator()

        platforms = ["Macintosh", "Windows", "Linux", "iPhone", "Android"]
        found_platforms = set()

        for ua in rotator.user_agents:
            for platform in platforms:
                if platform in ua:
                    found_platforms.add(platform)

        # Should find multiple platforms
        self.assertGreater(len(found_platforms), 2)


if __name__ == "__main__":
    unittest.main()
