"""
CAPTCHA and Block Page Detector

Detects when responses indicate CAPTCHA challenges or bot blocking,
and provides strategies for handling them.
"""

import re
import time
from typing import Optional, Dict, List, Any
from urllib.parse import urlparse


class CaptchaDetector:
    """
    Detects CAPTCHA and anti-bot blocking pages.
    
    Usage:
        detector = CaptchaDetector()
        
        if detector.is_blocked(response):
            print("Blocked by anti-bot system")
            strategy = detector.get_strategy(response)
    """
    
    def __init__(self):
        # Patterns that indicate CAPTCHA
        self.captcha_patterns = [
            # reCAPTCHA
            r'g-recaptcha',
            r'google\.com/recaptcha',
            r'grecaptcha',
            
            # hCAPTCHA
            r'hcaptcha',
            r'h-captcha',
            
            # Cloudflare
            r'cf-browser-verification',
            r'cf-im-under-attack',
            r'cf-captcha',
            r'Checking your browser',
            r'Please wait while we check your browser',
            r'__cf_bm',
            r'cf_chl_jschl_tk',
            
            # AWS WAF
            r'awswaf',
            r'captcha-aws',
            
            # Generic CAPTCHA
            r'captcha',
            r'CAPTCHA',
            r'Enter the characters',
            r'Security check',
            r'Verification required',
            r'Are you a robot',
            r'Please verify you are human',
        ]
        
        # Patterns that indicate rate limiting/banning
        self.block_patterns = [
            r'rate limit',
            r'Rate limit',
            r'too many requests',
            r'Too Many Requests',
            r'access denied',
            r'Access Denied',
            r'blocked',
            r'Blocked',
            r'403 Forbidden',
            r'Forbidden',
            r'Your IP has been banned',
            r'IP blocked',
            r'automated request',
            r'suspicious activity',
            r'unusual traffic',
            r'Unusual traffic',
        ]
        
        # Page titles that indicate blocking
        self.block_titles = [
            'Access Denied',
            'Forbidden',
            'Blocked',
            'Rate Limited',
            'Security Check',
            'CAPTCHA',
            'Just a moment',
            'Checking your browser',
        ]
        
        # Response codes that typically indicate issues
        self.block_status_codes = [403, 429, 503, 504]
        
        self._compiled_captcha = [re.compile(p, re.IGNORECASE) for p in self.captcha_patterns]
        self._compiled_block = [re.compile(p, re.IGNORECASE) for p in self.block_patterns]
    
    def is_captcha(self, content: str) -> bool:
        """
        Check if content contains CAPTCHA indicators.
        
        Args:
            content: HTML/text content to check
            
        Returns:
            True if CAPTCHA detected
        """
        for pattern in self._compiled_captcha:
            if pattern.search(content):
                return True
        return False
    
    def is_blocked(self, content: str) -> bool:
        """
        Check if content indicates blocking/rate limiting.
        
        Args:
            content: HTML/text content to check
            
        Returns:
            True if blocked
        """
        for pattern in self._compiled_block:
            if pattern.search(content):
                return True
        return False
    
    def is_title_blocked(self, title: str) -> bool:
        """
        Check if page title indicates blocking.
        
        Args:
            title: Page title
            
        Returns:
            True if title indicates blocking
        """
        title_lower = title.lower()
        for block_title in self.block_titles:
            if block_title.lower() in title_lower:
                return True
        return False
    
    def is_rate_limited(self, status_code: int, content: str = '') -> bool:
        """
        Check if response indicates rate limiting.
        
        Args:
            status_code: HTTP status code
            content: Response content
            
        Returns:
            True if rate limited
        """
        if status_code == 429:
            return True
        
        rate_limit_patterns = [
            r'rate limit',
            r'too many requests',
            r'try again later',
            r'retry after',
        ]
        
        for pattern in rate_limit_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        return False
    
    def detect(self, response_or_content, status_code: Optional[int] = None) -> Dict[str, Any]:
        """
        Comprehensive detection of blocking/CAPTCHA.
        
        Args:
            response_or_content: Response object or content string
            status_code: HTTP status code (if not in response object)
            
        Returns:
            Dict with detection results:
                {
                    'is_captcha': bool,
                    'is_blocked': bool,
                    'is_rate_limited': bool,
                    'requires_action': bool,
                    'type': str,  # 'captcha', 'blocked', 'rate_limited', 'none'
                    'confidence': str,  # 'high', 'medium', 'low'
                }
        """
        result = {
            'is_captcha': False,
            'is_blocked': False,
            'is_rate_limited': False,
            'requires_action': False,
            'type': 'none',
            'confidence': 'low',
        }
        
        # Extract content and status code
        if hasattr(response_or_content, 'text'):
            content = response_or_content.text
            status_code = getattr(response_or_content, 'status_code', status_code)
        elif hasattr(response_or_content, 'content'):
            content = response_or_content.content.decode('utf-8', errors='ignore')
            status_code = getattr(response_or_content, 'status_code', status_code)
        else:
            content = str(response_or_content)
        
        # Check status code
        if status_code in [403, 503]:
            result['is_blocked'] = True
            result['confidence'] = 'medium'
        elif status_code == 429:
            result['is_rate_limited'] = True
            result['confidence'] = 'high'
        
        # Check content
        if self.is_captcha(content):
            result['is_captcha'] = True
            result['confidence'] = 'high'
        
        if self.is_blocked(content):
            result['is_blocked'] = True
            result['confidence'] = 'high'
        
        if self.is_rate_limited(status_code or 200, content):
            result['is_rate_limited'] = True
            if status_code == 429:
                result['confidence'] = 'high'
            else:
                result['confidence'] = 'medium'
        
        # Determine if action is required
        result['requires_action'] = (
            result['is_captcha'] or 
            result['is_blocked'] or 
            result['is_rate_limited']
        )
        
        # Determine type
        if result['is_captcha']:
            result['type'] = 'captcha'
        elif result['is_rate_limited']:
            result['type'] = 'rate_limited'
        elif result['is_blocked']:
            result['type'] = 'blocked'
        
        return result
    
    def get_strategy(self, detection_result: Dict[str, Any]) -> str:
        """
        Get recommended strategy based on detection.
        
        Args:
            detection_result: Result from detect()
            
        Returns:
            Strategy string:
                - 'rotate_proxy': Use different proxy
                - 'wait_retry': Wait and retry
                - 'abort': Give up on this request
                - 'continue': No action needed
        """
        if not detection_result['requires_action']:
            return 'continue'
        
        detection_type = detection_result['type']
        confidence = detection_result['confidence']
        
        if detection_type == 'captcha':
            # CAPTCHA usually requires human intervention
            if confidence == 'high':
                return 'rotate_proxy'
            else:
                return 'wait_retry'
        
        elif detection_type == 'rate_limited':
            # Rate limiting - wait and retry with different proxy
            return 'rotate_proxy'
        
        elif detection_type == 'blocked':
            # Blocked - rotate proxy
            return 'rotate_proxy'
        
        return 'wait_retry'
    
    def should_rotate_proxy(self, detection_result: Dict[str, Any]) -> bool:
        """
        Check if proxy rotation is recommended.
        
        Args:
            detection_result: Result from detect()
            
        Returns:
            True if should rotate proxy
        """
        return self.get_strategy(detection_result) == 'rotate_proxy'


class ProxyHealthChecker:
    """
    Checks health of proxy layers before use.
    """
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self._health_cache: Dict[str, Dict[str, Any]] = {}
    
    def check_layer(self, layer_name: str, test_url: str = "https://httpbin.org/ip") -> Dict[str, Any]:
        """
        Check health of a proxy layer.
        
        Args:
            layer_name: Name of the layer (e.g., 'nordvpn', 'aws')
            test_url: URL to use for health check
            
        Returns:
            Health check result
        """
        import requests
        
        result = {
            'layer': layer_name,
            'healthy': False,
            'response_time': None,
            'error': None,
        }
        
        try:
            start_time = time.time()
            response = requests.get(test_url, timeout=self.timeout)
            elapsed = time.time() - start_time
            
            result['response_time'] = round(elapsed, 3)
            
            if response.status_code == 200:
                result['healthy'] = True
                # Cache the result
                self._health_cache[layer_name] = {
                    'healthy': True,
                    'last_checked': time.time(),
                    'response_time': elapsed,
                }
            else:
                result['error'] = f"HTTP {response.status_code}"
                
        except Exception as e:
            result['error'] = str(e)
            self._health_cache[layer_name] = {
                'healthy': False,
                'last_checked': time.time(),
                'error': str(e),
            }
        
        return result
    
    def is_healthy(self, layer_name: str, max_age: float = 300) -> bool:
        """
        Check if a layer is healthy based on cached result.
        
        Args:
            layer_name: Name of the layer
            max_age: Maximum age of cached result in seconds
            
        Returns:
            True if layer is healthy
        """
        if layer_name not in self._health_cache:
            return False
        
        cached = self._health_cache[layer_name]
        age = time.time() - cached.get('last_checked', 0)
        
        if age > max_age:
            return False
        
        return cached.get('healthy', False)
    
    def invalidate(self, layer_name: str):
        """Invalidate cached health status for a layer."""
        if layer_name in self._health_cache:
            del self._health_cache[layer_name]


# Global detector instance
detector = CaptchaDetector()


def detect_blocking(response_or_content, status_code: Optional[int] = None) -> Dict[str, Any]:
    """Convenience function to detect blocking/CAPTCHA."""
    return detector.detect(response_or_content, status_code)


def is_blocked(response_or_content, status_code: Optional[int] = None) -> bool:
    """Convenience function to check if blocked."""
    result = detector.detect(response_or_content, status_code)
    return result['requires_action']
