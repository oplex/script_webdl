"""
Humanized HTTP downloader module.

This module handles HTTP requests with realistic browser behavior including
random delays, user agent rotation, retry logic, and proper error handling
to avoid bot detection.
"""

import time
import requests
from urllib.parse import urljoin, urlparse
from typing import Optional, Tuple
import logging

from .config import (
    get_headers, get_random_delay, DEFAULT_TIMEOUT,
    MAX_RETRIES, RETRY_DELAY, MAX_FILE_SIZE, CHUNK_SIZE
)

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    """Raised when download fails after all retries."""
    pass


class Downloader:
    """
    Handles HTTP downloads with humanized behavior.

    Implements delays, retries, and browser-like headers to avoid
    bot detection while downloading web content.
    """

    def __init__(self, respect_robots=False):
        """
        Initialize the downloader.

        Args:
            respect_robots: Whether to respect robots.txt (default: False)
        """
        self.session = requests.Session()
        self.respect_robots = respect_robots
        self.last_request_time = 0

    def _wait_politely(self):
        """Implement human-like delay between requests."""
        elapsed = time.time() - self.last_request_time
        delay = get_random_delay()

        if elapsed < delay:
            sleep_time = delay - elapsed
            logger.debug(f"Waiting {sleep_time:.2f}s before next request")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def download(self, url: str, referer: Optional[str] = None) -> Tuple[bytes, str, str]:
        """
        Download content from URL with retries and humanization.

        Args:
            url: The URL to download
            referer: Optional referer URL

        Returns:
            Tuple of (content, content_type, final_url)

        Raises:
            DownloadError: If download fails after all retries
        """
        self._wait_politely()

        headers = get_headers()
        if referer:
            headers['Referer'] = referer

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Downloading: {url} (attempt {attempt + 1}/{MAX_RETRIES})")

                response = self.session.get(
                    url,
                    headers=headers,
                    timeout=DEFAULT_TIMEOUT,
                    allow_redirects=True,
                    stream=True
                )
                response.raise_for_status()

                # Check content length
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > MAX_FILE_SIZE:
                    logger.warning(f"Skipping large file: {url} ({content_length} bytes)")
                    raise DownloadError(f"File too large: {content_length} bytes")

                # Download in chunks
                content = bytearray()
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        content.extend(chunk)
                        if len(content) > MAX_FILE_SIZE:
                            raise DownloadError("File size exceeded during download")

                content_type = response.headers.get('content-type', '').split(';')[0].strip()
                final_url = response.url

                logger.info(f"Successfully downloaded: {url} ({len(content)} bytes)")
                return bytes(content), content_type, final_url

            except requests.exceptions.RequestException as e:
                last_error = e
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")

                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                break

        error_msg = f"Failed to download {url} after {MAX_RETRIES} attempts: {last_error}"
        logger.error(error_msg)
        raise DownloadError(error_msg)

    def close(self):
        """Close the session and cleanup resources."""
        self.session.close()


def is_valid_url(url: str) -> bool:
    """
    Check if URL is valid and has proper scheme.

    Args:
        url: URL to validate

    Returns:
        True if URL is valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except Exception:
        return False


def normalize_url(url: str, base_url: str) -> str:
    """
    Normalize and resolve URL relative to base URL.

    Args:
        url: URL to normalize
        base_url: Base URL for resolving relative URLs

    Returns:
        Normalized absolute URL
    """
    # Remove fragments
    url = url.split('#')[0]

    # Join with base URL
    absolute_url = urljoin(base_url, url)

    return absolute_url


def get_domain(url: str) -> str:
    """
    Extract domain from URL.

    Args:
        url: URL to parse

    Returns:
        Domain name (netloc)
    """
    parsed = urlparse(url)
    return parsed.netloc
