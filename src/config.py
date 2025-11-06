"""
Configuration and constants for the website downloader.

This module provides centralized configuration including user agents,
request delays, timeouts, and other settings for humanized web scraping.
"""

import random

# User agents for rotation (mimicking real browsers)
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

# Request settings
DEFAULT_TIMEOUT = 30
MIN_DELAY = 1.0  # Minimum delay between requests (seconds)
MAX_DELAY = 3.0  # Maximum delay between requests (seconds)
MAX_RETRIES = 3
RETRY_DELAY = 2.0

# Download settings
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
CHUNK_SIZE = 8192

# Crawler settings
MAX_DEPTH = 10
MAX_PAGES = 1000

# File extensions to download
DOWNLOADABLE_EXTENSIONS = {
    '.html', '.htm', '.css', '.js', '.json',
    '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico', '.webp',
    '.woff', '.woff2', '.ttf', '.eot', '.otf',
    '.pdf', '.txt', '.xml'
}

# Storage settings
SITES_DIR = 'sites'
INDEX_FILE = 'index.html'


def get_random_user_agent():
    """Return a random user agent string for request headers."""
    return random.choice(USER_AGENTS)


def get_random_delay():
    """Return a random delay between MIN_DELAY and MAX_DELAY."""
    return random.uniform(MIN_DELAY, MAX_DELAY)


def get_headers():
    """
    Generate request headers that mimic a real browser.

    Returns:
        dict: HTTP headers for requests
    """
    return {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }
