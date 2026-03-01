"""
Agent Search - Web search for AI agents.

A CLI tool that gives AI agents web search capabilities.
Lite mode is free and self-hosted.
Pro mode is hosted infrastructure.
"""

__version__ = "2.0.0"
__author__ = "Qwert"
__email__ = "hello@qwert.ai"
__license__ = "MIT"

from .core.proxy_chain import ProxyChain
from .core.html_to_markdown import HTMLToMarkdown

__all__ = [
    "ProxyChain",
    "HTMLToMarkdown",
    "__version__",
]
