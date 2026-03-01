#!/usr/bin/env python3
"""
Demo script showing the Proxy Toolkit CLI in action.

This demonstrates the complete workflow:
1. CLI help and commands
2. Pool network participation
3. Scraping in Lite and Pro modes
4. Auth and status commands
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a CLI command and show output."""
    print(f"\n{'=' * 70}")
    print(f"COMMAND: {cmd}")
    print(f"{'=' * 70}")
    print(f"Description: {description}\n")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent.parent.parent),
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
    except Exception as e:
        print(f"Error: {e}")


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                    PROXY TOOLKIT CLI DEMO                            ║
║             Lite vs Pro with Proxy Pool Network                     ║
╚══════════════════════════════════════════════════════════════════════╝
""")

    # 1. Show help
    run_command("python3 -m proxy_toolkit --help", "Show main CLI help")

    # 2. Show version
    run_command("python3 -m proxy_toolkit --version", "Show version information")

    # 3. Show scrape help
    run_command("python3 -m proxy_toolkit scrape --help", "Show scrape command help")

    # 4. Show pool commands
    run_command("python3 -m proxy_toolkit pool --help", "Show pool subcommands")

    # 5. Join pool
    run_command(
        "echo 'y' | python3 -m proxy_toolkit pool join",
        "Join Proxy Pool Network (simulated)",
    )

    # 6. Check pool status
    run_command(
        "python3 -m proxy_toolkit pool status", "Check pool participation status"
    )

    # 7. View pool stats
    run_command("python3 -m proxy_toolkit pool stats", "View global pool statistics")

    # 8. Check credits
    run_command("python3 -m proxy_toolkit pool credits", "View earned credits")

    # 9. Leave pool
    run_command("python3 -m proxy_toolkit pool leave", "Leave Proxy Pool Network")

    # 10. Auth status
    run_command("python3 -m proxy_toolkit auth status", "Check authentication status")

    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                        DEMO COMPLETE                                ║
║                                                                      ║
║  The Proxy Toolkit CLI supports:                                     ║
║  • Lite mode (self-hosted, free)                                    ║
║  • Pro mode (hosted, paid)                                          ║
║  • Proxy Pool Network (community-powered)                             ║
║                                                                      ║
║  Key Commands:                                                      ║
║  • proxy-toolkit scrape <url> [--pro]                               ║
║  • proxy-toolkit pool join                                          ║
║  • proxy-toolkit pool status                                        ║
║  • proxy-toolkit pool credits                                       ║
║                                                                      ║
║  Documentation: docs/business-model.md                             ║
╚══════════════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
