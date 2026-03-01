"""
Version utilities.
"""


def get_version() -> str:
    """Get the current version."""
    from agent_search import __version__

    return __version__
