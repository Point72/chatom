"""Tests for backend configuration modules.

This module tests the Slack configuration classes.
"""

from pydantic import SecretStr

from chatom.slack.config import SlackConfig


class TestSlackConfig:
    """Tests for SlackConfig class."""

    def test_create_slack_config(self):
        """Test creating a Slack config with basic settings."""
        config = SlackConfig(
            bot_token=SecretStr("xoxb-test-token"),
            team_id="T12345",
        )
        assert config.bot_token_str == "xoxb-test-token"
        assert config.team_id == "T12345"

    def test_slack_config_defaults(self):
        """Test Slack config default values."""
        config = SlackConfig()
        assert config.bot_token_str == ""
        assert config.app_token_str == ""
        assert config.signing_secret_str == ""
        assert config.team_id == ""
        assert config.default_channel == ""
        assert config.socket_mode is False

    def test_bot_token_str_property(self):
        """Test bot_token_str property returns plain string."""
        config = SlackConfig(bot_token=SecretStr("xoxb-token-value"))
        assert config.bot_token_str == "xoxb-token-value"

    def test_app_token_str_property(self):
        """Test app_token_str property returns plain string."""
        config = SlackConfig(app_token=SecretStr("xapp-token-value"))
        assert config.app_token_str == "xapp-token-value"

    def test_signing_secret_str_property(self):
        """Test signing_secret_str property returns plain string."""
        config = SlackConfig(signing_secret=SecretStr("signing-secret-123"))
        assert config.signing_secret_str == "signing-secret-123"

    def test_has_socket_mode_with_socket_mode_enabled(self):
        """Test has_socket_mode returns True when socket_mode is True."""
        config = SlackConfig(socket_mode=True)
        assert config.has_socket_mode is True

    def test_has_socket_mode_with_app_token(self):
        """Test has_socket_mode returns True when app_token is set."""
        config = SlackConfig(app_token=SecretStr("xapp-test-token"))
        assert config.has_socket_mode is True

    def test_has_socket_mode_false(self):
        """Test has_socket_mode returns False when neither is set."""
        config = SlackConfig()
        assert config.has_socket_mode is False
