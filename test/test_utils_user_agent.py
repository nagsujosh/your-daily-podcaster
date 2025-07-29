#!/usr/bin/env python3
"""
Unit tests for yourdaily.utils.user_agent module.
"""

from unittest.mock import MagicMock, patch

from yourdaily.utils.user_agent import (
    UserAgentManager,
    get_chrome_user_agent,
    get_firefox_user_agent,
    get_mobile_user_agent,
    get_random_user_agent,
    get_user_agent_manager,
)


class TestUserAgentManager:
    """Test cases for UserAgentManager class."""

    def test_init_default_parameters(self):
        """Test UserAgentManager initialization with default parameters."""
        manager = UserAgentManager()

        assert manager.use_fake_useragent is True
        # _fake_ua should be set if fake-useragent is available, otherwise None
        assert hasattr(manager, "_fake_ua")

    def test_init_disable_fake_useragent(self):
        """Test UserAgentManager initialization with fake-useragent disabled."""
        manager = UserAgentManager(use_fake_useragent=False)

        assert manager.use_fake_useragent is False
        assert manager._fake_ua is None

    def test_get_user_agent_without_fake_useragent(self):
        """Test getting user agent when fake-useragent library is not available."""
        manager = UserAgentManager(use_fake_useragent=False)
        user_agent = manager.get_user_agent()

        assert isinstance(user_agent, str)
        assert len(user_agent) > 0
        assert "Mozilla" in user_agent

    @patch("fake_useragent.UserAgent")
    def test_get_user_agent_with_fake_useragent(self, mock_user_agent_class):
        """Test getting user agent when fake-useragent library is available."""
        mock_ua = MagicMock()
        mock_ua.random = "Fake User Agent String"
        mock_user_agent_class.return_value = mock_ua

        manager = UserAgentManager(use_fake_useragent=True)
        user_agent = manager.get_user_agent()

        assert user_agent == "Fake User Agent String"

    def test_get_chrome_user_agent(self):
        """Test getting Chrome-specific user agent."""
        manager = UserAgentManager(use_fake_useragent=False)
        user_agent = manager.get_chrome_user_agent()

        assert isinstance(user_agent, str)
        assert "Chrome" in user_agent
        assert "Edg" not in user_agent  # Should not be Edge

    def test_get_firefox_user_agent(self):
        """Test getting Firefox-specific user agent."""
        manager = UserAgentManager(use_fake_useragent=False)
        user_agent = manager.get_firefox_user_agent()

        assert isinstance(user_agent, str)
        assert "Firefox" in user_agent

    def test_get_mobile_user_agent(self):
        """Test getting mobile-specific user agent."""
        manager = UserAgentManager(use_fake_useragent=False)
        user_agent = manager.get_mobile_user_agent()

        assert isinstance(user_agent, str)
        assert any(keyword in user_agent for keyword in ["Mobile", "Android", "iPhone"])

    def test_user_agents_list_not_empty(self):
        """Test that the predefined user agents list is not empty."""
        manager = UserAgentManager()

        assert len(manager.USER_AGENTS) > 0
        for ua in manager.USER_AGENTS:
            assert isinstance(ua, str)
            assert "Mozilla" in ua

    @patch("fake_useragent.UserAgent")
    def test_fake_useragent_fallback(self, mock_user_agent_class):
        """Test fallback to predefined user agents when fake-useragent fails."""
        mock_user_agent_class.side_effect = Exception("Fake error")

        manager = UserAgentManager(use_fake_useragent=True)
        user_agent = manager.get_user_agent()

        assert isinstance(user_agent, str)
        assert "Mozilla" in user_agent


class TestUserAgentFunctions:
    """Test cases for the convenience functions."""

    def test_get_user_agent_manager(self):
        """Test getting the global user agent manager."""
        manager = get_user_agent_manager()

        assert isinstance(manager, UserAgentManager)
        assert manager.use_fake_useragent is True

    def test_get_random_user_agent(self):
        """Test getting a random user agent."""
        user_agent = get_random_user_agent()

        assert isinstance(user_agent, str)
        assert len(user_agent) > 0
        assert "Mozilla" in user_agent

    def test_get_chrome_user_agent_function(self):
        """Test getting Chrome user agent via function."""
        user_agent = get_chrome_user_agent()

        assert isinstance(user_agent, str)
        assert "Chrome" in user_agent
        assert "Edg" not in user_agent

    def test_get_firefox_user_agent_function(self):
        """Test getting Firefox user agent via function."""
        user_agent = get_firefox_user_agent()

        assert isinstance(user_agent, str)
        assert "Firefox" in user_agent

    def test_get_mobile_user_agent_function(self):
        """Test getting mobile user agent via function."""
        user_agent = get_mobile_user_agent()

        assert isinstance(user_agent, str)
        assert any(keyword in user_agent for keyword in ["Mobile", "Android", "iPhone"])

    def test_global_manager_singleton(self):
        """Test that the global manager is a singleton."""
        manager1 = get_user_agent_manager()
        manager2 = get_user_agent_manager()

        assert manager1 is manager2


class TestUserAgentIntegration:
    """Integration tests for user agent functionality."""

    def test_user_agent_variety(self):
        """Test that different user agent functions return different strings."""
        random_ua = get_random_user_agent()
        chrome_ua = get_chrome_user_agent()
        firefox_ua = get_firefox_user_agent()
        mobile_ua = get_mobile_user_agent()

        # All should be different strings
        ua_list = [random_ua, chrome_ua, firefox_ua, mobile_ua]
        assert len(set(ua_list)) >= 2  # At least some should be different

        # All should be valid user agent strings
        for ua in ua_list:
            assert isinstance(ua, str)
            assert "Mozilla" in ua
            assert len(ua) > 20

    def test_user_agent_consistency(self):
        """Test that the same function returns consistent format."""
        manager = UserAgentManager(use_fake_useragent=False)

        # Test multiple calls to same function
        chrome_ua1 = manager.get_chrome_user_agent()
        chrome_ua2 = manager.get_chrome_user_agent()

        # Should both be Chrome user agents
        assert "Chrome" in chrome_ua1
        assert "Chrome" in chrome_ua2
        assert "Edg" not in chrome_ua1
        assert "Edg" not in chrome_ua2
