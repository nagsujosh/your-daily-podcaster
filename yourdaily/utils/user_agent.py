#!/usr/bin/env python3
"""
User Agent Utilities

Provides fake user agent functionality for web scraping to avoid detection.
"""

import random

from loguru import logger


class UserAgentManager:
    """Manages fake user agents for web scraping."""

    # Common user agents for different browsers
    USER_AGENTS = [
        # Chrome
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Firefox
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        # Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        # Edge
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        # Mobile Chrome
        "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    ]

    def __init__(self, use_fake_useragent: bool = True):
        """
        Initialize the user agent manager.

        Args:
            use_fake_useragent (bool): Whether to use the fake-useragent library
        """
        self.use_fake_useragent = use_fake_useragent
        self._fake_ua = None

        if use_fake_useragent:
            self._init_fake_useragent()

    def _init_fake_useragent(self) -> None:
        """Initialize the fake-useragent library."""
        try:
            from fake_useragent import UserAgent

            self._fake_ua = UserAgent()
            logger.debug("Successfully initialized fake-useragent library")
        except Exception as e:
            logger.warning(f"Failed to initialize fake-useragent library: {e}")
            self._fake_ua = None

    def get_user_agent(self) -> str:
        """
        Get a random user agent string.

        Returns:
            str: A user agent string
        """
        # Try to use fake-useragent library first
        if self._fake_ua is not None:
            try:
                user_agent = self._fake_ua.random
                logger.debug(f"Using fake-useragent: {user_agent[:50]}...")
                return user_agent
            except Exception as e:
                logger.warning(f"Failed to get user agent from fake-useragent: {e}")

        # Fall back to predefined user agents
        user_agent = random.choice(self.USER_AGENTS)
        logger.debug(f"Using predefined user agent: {user_agent[:50]}...")
        return user_agent

    def get_chrome_user_agent(self) -> str:
        """
        Get a Chrome-specific user agent.

        Returns:
            str: A Chrome user agent string
        """
        chrome_agents = [
            ua for ua in self.USER_AGENTS if "Chrome" in ua and "Edg" not in ua
        ]
        return random.choice(chrome_agents)

    def get_firefox_user_agent(self) -> str:
        """
        Get a Firefox-specific user agent.

        Returns:
            str: A Firefox user agent string
        """
        firefox_agents = [ua for ua in self.USER_AGENTS if "Firefox" in ua]
        return random.choice(firefox_agents)

    def get_mobile_user_agent(self) -> str:
        """
        Get a mobile-specific user agent.

        Returns:
            str: A mobile user agent string
        """
        mobile_agents = [
            ua
            for ua in self.USER_AGENTS
            if "Mobile" in ua or "Android" in ua or "iPhone" in ua
        ]
        return random.choice(mobile_agents)


# Global instance for easy access
_user_agent_manager = None


def get_user_agent_manager() -> UserAgentManager:
    """
    Get the global user agent manager instance.

    Returns:
        UserAgentManager: The global user agent manager
    """
    global _user_agent_manager
    if _user_agent_manager is None:
        _user_agent_manager = UserAgentManager()
    return _user_agent_manager


def get_random_user_agent() -> str:
    """
    Get a random user agent string.

    Returns:
        str: A random user agent string
    """
    return get_user_agent_manager().get_user_agent()


def get_chrome_user_agent() -> str:
    """
    Get a Chrome-specific user agent.

    Returns:
        str: A Chrome user agent string
    """
    return get_user_agent_manager().get_chrome_user_agent()


def get_firefox_user_agent() -> str:
    """
    Get a Firefox-specific user agent.

    Returns:
        str: A Firefox user agent string
    """
    return get_user_agent_manager().get_firefox_user_agent()


def get_mobile_user_agent() -> str:
    """
    Get a mobile-specific user agent.

    Returns:
        str: A mobile user agent string
    """
    return get_user_agent_manager().get_mobile_user_agent()
