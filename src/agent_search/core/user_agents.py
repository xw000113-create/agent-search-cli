"""
User-Agent Rotation Module

Provides rotating User-Agent strings for different browsers and devices
to avoid bot detection.
"""

import random
from typing import List, Optional


class UserAgentRotator:
    """
    Rotates User-Agent strings to simulate different browsers and devices.
    
    Usage:
        rotator = UserAgentRotator()
        headers = {'User-Agent': rotator.get_random()}
    """
    
    def __init__(self):
        self.user_agents = self._load_user_agents()
        self._index = 0
        self._shuffled = False
        
    def _load_user_agents(self) -> List[str]:
        """Load a diverse set of User-Agent strings."""
        return [
            # Chrome on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            
            # Chrome on Linux
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            
            # Firefox on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
            
            # Firefox on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            
            # Firefox on Linux
            "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
            
            # Safari on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
            
            # Edge on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
            
            # Edge on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            
            # Mobile - iPhone Safari
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            
            # Mobile - iPad Safari
            "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
            
            # Mobile - Android Chrome
            "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            
            # Mobile - Android Firefox
            "Mozilla/5.0 (Android 14; Mobile; rv:121.0) Gecko/121.0 Firefox/121.0",
            "Mozilla/5.0 (Android 13; Mobile; rv:120.0) Gecko/120.0 Firefox/120.0",
        ]
    
    def get_random(self) -> str:
        """Get a random User-Agent string."""
        return random.choice(self.user_agents)
    
    def get_sequential(self) -> str:
        """Get User-Agent strings in rotation (cycles through all)."""
        ua = self.user_agents[self._index % len(self.user_agents)]
        self._index += 1
        return ua
    
    def get_by_browser(self, browser: str) -> Optional[str]:
        """
        Get a User-Agent for a specific browser.
        
        Args:
            browser: One of 'chrome', 'firefox', 'safari', 'edge'
        """
        browser = browser.lower()
        candidates = [ua for ua in self.user_agents if browser in ua.lower()]
        return random.choice(candidates) if candidates else None
    
    def get_by_platform(self, platform: str) -> Optional[str]:
        """
        Get a User-Agent for a specific platform.
        
        Args:
            platform: One of 'macintosh', 'windows', 'linux', 'iphone', 'ipad', 'android'
        """
        platform = platform.lower()
        candidates = [ua for ua in self.user_agents if platform in ua.lower()]
        return random.choice(candidates) if candidates else None
    
    def get_desktop(self) -> str:
        """Get a random desktop browser User-Agent."""
        desktop_ua = [ua for ua in self.user_agents if 'Mobile' not in ua]
        return random.choice(desktop_ua)
    
    def get_mobile(self) -> str:
        """Get a random mobile browser User-Agent."""
        mobile_ua = [ua for ua in self.user_agents if 'Mobile' in ua]
        return random.choice(mobile_ua)
    
    def shuffle(self):
        """Shuffle the User-Agent list for random rotation."""
        random.shuffle(self.user_agents)
        self._shuffled = True


# Global singleton for convenience
_ua_rotator: Optional[UserAgentRotator] = None


def get_user_agent_rotator() -> UserAgentRotator:
    """Get the global UserAgentRotator instance."""
    global _ua_rotator
    if _ua_rotator is None:
        _ua_rotator = UserAgentRotator()
    return _ua_rotator


def get_random_user_agent() -> str:
    """Get a random User-Agent string (convenience function)."""
    return get_user_agent_rotator().get_random()
