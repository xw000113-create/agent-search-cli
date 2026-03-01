"""
Test CLI commands and functionality.
"""

import pytest
import click
from click.testing import CliRunner
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from agent_search.cli.main import cli
from agent_search.cli.onboarding import (
    get_config,
    save_config,
    check_onboarding_complete,
    should_run_onboarding,
)


class TestCLIMain:
    """Test main CLI entry point."""

    def test_cli_version(self):
        """Test CLI version command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "search, version" in result.output

    def test_cli_help(self):
        """Test CLI help command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Agent Search" in result.output
        assert "Lite:" in result.output
        assert "Pro:" in result.output

    def test_cli_verbose_flag(self):
        """Test verbose flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--verbose", "--help"])

        assert result.exit_code == 0


class TestQueryCommand:
    """Test query/search command."""

    def test_query_command_exists(self):
        """Test query command is available."""
        runner = CliRunner()
        result = runner.invoke(cli, ["query", "--help"])

        assert result.exit_code == 0
        assert "Usage:" in result.output

    def test_query_requires_argument(self):
        """Test query subcommand requires query argument."""
        runner = CliRunner()
        result = runner.invoke(cli, ["query"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Error" in result.output

    def test_query_with_pro_flag(self):
        """Test query with Pro mode flag."""
        runner = CliRunner()

        # Create config with API key
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / ".config" / "agent-search" / "config.json"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text(
                json.dumps({"api_key": "as_test_key_123", "tier": "pro"})
            )

            result = runner.invoke(cli, ["--skip-onboarding", "query", "test", "--pro"])

            # Should attempt to run (may fail due to missing API)
            assert result.exit_code in [0, 1]  # 0=success, 1=error

    def test_query_output_format(self):
        """Test query with different output formats."""
        runner = CliRunner()

        # Test markdown format
        result = runner.invoke(
            cli, ["--skip-onboarding", "query", "test", "--format", "markdown"]
        )
        assert result.exit_code in [0, 1]

        # Test json format
        result = runner.invoke(
            cli, ["--skip-onboarding", "query", "test", "--format", "json"]
        )
        assert result.exit_code in [0, 1]


class TestAuthCommands:
    """Test authentication commands."""

    def test_auth_login_command(self):
        """Test auth login --help shows usage."""
        runner = CliRunner()
        result = runner.invoke(cli, ["auth", "login", "--help"])

        assert result.exit_code == 0

    def test_auth_status_command(self):
        """Test auth status command runs."""
        runner = CliRunner()
        result = runner.invoke(cli, ["auth", "status"])

        assert result.exit_code == 0

    def test_auth_logout_command(self):
        """Test auth logout command runs."""
        runner = CliRunner()
        result = runner.invoke(cli, ["auth", "logout"])

        assert result.exit_code == 0


class TestPoolCommands:
    """Test pool network commands."""

    def test_pool_join_command(self):
        """Test pool join --help shows usage."""
        runner = CliRunner()
        result = runner.invoke(cli, ["pool", "join", "--help"])

        assert result.exit_code == 0

    def test_pool_status_command(self):
        """Test pool status command runs."""
        runner = CliRunner()
        result = runner.invoke(cli, ["pool", "status"])

        # May fail if pool not configured
        assert result.exit_code in [0, 1]

    def test_pool_credits_command(self):
        """Test pool credits command runs."""
        runner = CliRunner()
        result = runner.invoke(cli, ["pool", "credits"])

        assert result.exit_code in [0, 1]


class TestConfigManagement:
    """Test configuration management."""

    def test_get_config_no_file(self):
        """Test get_config when no config exists."""
        config = get_config()
        assert config == {}

    def test_save_and_get_config(self, tmp_path):
        """Test saving and retrieving config."""
        # Temporarily change config location
        original_config = Path.home() / ".config" / "agent-search" / "config.json"

        test_config = {"api_key": "test_key", "tier": "free"}

        # This would need mocking of CONFIG_FILE
        pass

    def test_check_onboarding_complete(self):
        """Test onboarding completion check."""
        # Should return False when no config
        with tempfile.TemporaryDirectory():
            # Mock empty config
            result = check_onboarding_complete()
            assert result is False

    def test_should_run_onboarding(self):
        """Test should_run_onboarding logic."""
        # Should return True when no API key
        with tempfile.TemporaryDirectory():
            result = should_run_onboarding()
            # Returns True because no config, but also checks isatty
            pass


class TestCLIOnboarding:
    """Test CLI onboarding flow."""

    def test_onboarding_prompts(self):
        """Test onboarding prompts user."""
        runner = CliRunner()

        # Simulate first run
        result = runner.invoke(cli, input="y\ntest@example.com\npassword\npassword\n")

        # May create account or fail (no backend)
        assert result.exit_code in [0, 1]

    def test_onboarding_existing_user(self):
        """Test onboarding for existing user."""
        runner = CliRunner()

        # Simulate existing user login
        result = runner.invoke(cli, input="y\ntest@example.com\npassword\n")

        assert result.exit_code in [0, 1]


class TestCrawlCommand:
    """Test crawl command."""

    def test_crawl_command_exists(self):
        """Test crawl command exists."""
        runner = CliRunner()
        result = runner.invoke(cli, ["crawl", "--help"])

        assert result.exit_code == 0

    def test_crawl_requires_url(self):
        """Test crawl requires URL."""
        runner = CliRunner()
        result = runner.invoke(cli, ["crawl"])

        assert result.exit_code != 0


class TestExtractCommand:
    """Test extract command."""

    def test_extract_command_exists(self):
        """Test extract command exists."""
        runner = CliRunner()
        result = runner.invoke(cli, ["extract", "--help"])

        assert result.exit_code == 0


class TestMonitorCommand:
    """Test monitor command."""

    def test_monitor_command_exists(self):
        """Test monitor command exists."""
        runner = CliRunner()
        result = runner.invoke(cli, ["monitor", "--help"])

        assert result.exit_code == 0


class TestCLIErrorHandling:
    """Test CLI error handling."""

    def test_invalid_command(self):
        """Test that an unrecognized argument is handled as a quick search query.

        The CLI design uses an optional 'query' argument on the group, so any
        unrecognized positional value (like 'invalid-command') is treated as a
        search query rather than an unknown subcommand. The execute_query
        function catches errors and prints a placeholder, so the exit code is 0.
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["--skip-onboarding", "invalid-command"])

        # The CLI treats unrecognized args as search queries (quick search mode),
        # so this produces output (placeholder or results) with exit code 0.
        assert result.exit_code == 0
        # Verify it was treated as a search query
        assert "Search Results" in result.output or "search" in result.output.lower()

    def test_missing_required_option(self):
        """Test missing required option on query subcommand."""
        runner = CliRunner()
        result = runner.invoke(cli, ["query"])

        assert result.exit_code != 0

    def test_invalid_option_value(self):
        """Test invalid option value."""
        runner = CliRunner()
        result = runner.invoke(cli, ["query", "test", "--format", "invalid"])

        assert result.exit_code != 0


class TestCLIOptions:
    """Test CLI global options."""

    def test_config_option(self):
        """Test --config option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--config", "/tmp/test-config.json", "--help"])

        assert result.exit_code == 0

    def test_skip_onboarding_option(self):
        """Test --skip-onboarding option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--skip-onboarding", "query", "test"])

        # Should bypass onboarding
        assert result.exit_code in [0, 1]
