"""
HTML parser and link converter for offline viewing.

This module parses HTML content, extracts links, and converts them
to work correctly when viewing the website offline.
"""

import re
import logging
from urllib.parse import urljoin, urlparse, urlunparse
from typing import Set, List, Tuple
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class LinkExtractor:
    """
    Extracts and processes links from HTML content.

    Finds all URLs in HTML including links, scripts, stylesheets,
    images, and other resources.
    """

    # HTML tags and attributes that contain URLs
    URL_ATTRIBUTES = {
        'a': ['href'],
        'link': ['href'],
        'script': ['src'],
        'img': ['src', 'srcset', 'data-src'],
        'source': ['src', 'srcset'],
        'iframe': ['src'],
        'embed': ['src'],
        'object': ['data'],
        'video': ['src', 'poster'],
        'audio': ['src'],
        'form': ['action'],
    }

    def __init__(self, base_url: str):
        """
        Initialize the link extractor.

        Args:
            base_url: Base URL for resolving relative links
        """
        self.base_url = base_url
        self.base_domain = urlparse(base_url).netloc

    def extract_links(self, html: str) -> Set[str]:
        """
        Extract all links from HTML content.

        Args:
            html: HTML content as string

        Returns:
            Set of absolute URLs found in the HTML
        """
        links = set()

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Extract from tags
            for tag_name, attributes in self.URL_ATTRIBUTES.items():
                for tag in soup.find_all(tag_name):
                    for attr in attributes:
                        url = tag.get(attr)
                        if url:
                            # Handle srcset which can have multiple URLs
                            if attr == 'srcset':
                                urls = self._parse_srcset(url)
                                links.update(urls)
                            else:
                                absolute_url = urljoin(self.base_url, url)
                                links.add(absolute_url)

            # Extract from CSS imports
            style_tags = soup.find_all('style')
            for style in style_tags:
                if style.string:
                    css_urls = self._extract_css_urls(style.string)
                    links.update(css_urls)

            # Extract from inline styles
            for tag in soup.find_all(style=True):
                css_urls = self._extract_css_urls(tag['style'])
                links.update(css_urls)

        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")

        return links

    def _parse_srcset(self, srcset: str) -> List[str]:
        """
        Parse srcset attribute which contains multiple URLs.

        Args:
            srcset: srcset attribute value

        Returns:
            List of absolute URLs
        """
        urls = []
        parts = srcset.split(',')

        for part in parts:
            url = part.strip().split()[0]
            if url:
                absolute_url = urljoin(self.base_url, url)
                urls.append(absolute_url)

        return urls

    def _extract_css_urls(self, css: str) -> Set[str]:
        """
        Extract URLs from CSS content.

        Args:
            css: CSS content as string

        Returns:
            Set of absolute URLs found in CSS
        """
        urls = set()
        pattern = r'url\(["\']?([^"\'()]+)["\']?\)'
        matches = re.findall(pattern, css)

        for match in matches:
            absolute_url = urljoin(self.base_url, match)
            urls.add(absolute_url)

        return urls

    def is_same_domain(self, url: str) -> bool:
        """
        Check if URL belongs to the same domain.

        Args:
            url: URL to check

        Returns:
            True if URL is from same domain, False otherwise
        """
        try:
            domain = urlparse(url).netloc
            return domain == self.base_domain or domain.endswith(f'.{self.base_domain}')
        except Exception:
            return False


class LinkConverter:
    """
    Converts absolute URLs to relative paths for offline viewing.

    Rewrites links in HTML, CSS, and other content to work when
    viewing the downloaded website offline.
    """

    def __init__(self, base_domain: str):
        """
        Initialize the link converter.

        Args:
            base_domain: Base domain of the website
        """
        self.base_domain = base_domain

    def convert_html(self, html: str, page_url: str, url_map: dict) -> str:
        """
        Convert all URLs in HTML to relative paths.

        Args:
            html: HTML content to convert
            page_url: URL of the current page
            url_map: Mapping of absolute URLs to local file paths

        Returns:
            Converted HTML content
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Convert URLs in tags
            for tag_name, attributes in LinkExtractor.URL_ATTRIBUTES.items():
                for tag in soup.find_all(tag_name):
                    for attr in attributes:
                        url = tag.get(attr)
                        if url and attr != 'srcset':
                            absolute_url = urljoin(page_url, url)
                            if absolute_url in url_map:
                                relative_path = self._get_relative_path(
                                    page_url, absolute_url, url_map
                                )
                                tag[attr] = relative_path
                        elif url and attr == 'srcset':
                            tag[attr] = self._convert_srcset(url, page_url, url_map)

            # Convert URLs in style tags
            for style_tag in soup.find_all('style'):
                if style_tag.string:
                    style_tag.string = self._convert_css(
                        style_tag.string, page_url, url_map
                    )

            # Convert inline styles
            for tag in soup.find_all(style=True):
                tag['style'] = self._convert_css(tag['style'], page_url, url_map)

            return str(soup)

        except Exception as e:
            logger.error(f"Error converting HTML: {e}")
            return html

    def _convert_srcset(self, srcset: str, page_url: str, url_map: dict) -> str:
        """Convert URLs in srcset attribute."""
        parts = srcset.split(',')
        converted_parts = []

        for part in parts:
            tokens = part.strip().split()
            if tokens:
                url = tokens[0]
                absolute_url = urljoin(page_url, url)
                if absolute_url in url_map:
                    relative_path = self._get_relative_path(page_url, absolute_url, url_map)
                    tokens[0] = relative_path
                converted_parts.append(' '.join(tokens))

        return ', '.join(converted_parts)

    def _convert_css(self, css: str, page_url: str, url_map: dict) -> str:
        """Convert URLs in CSS content."""
        def replace_url(match):
            url = match.group(1)
            absolute_url = urljoin(page_url, url)
            if absolute_url in url_map:
                relative_path = self._get_relative_path(page_url, absolute_url, url_map)
                return f'url({relative_path})'
            return match.group(0)

        pattern = r'url\(["\']?([^"\'()]+)["\']?\)'
        return re.sub(pattern, replace_url, css)

    def _get_relative_path(self, from_url: str, to_url: str, url_map: dict) -> str:
        """
        Calculate relative path between two URLs.

        Args:
            from_url: Source URL
            to_url: Target URL
            url_map: URL to file path mapping

        Returns:
            Relative path from source to target
        """
        if to_url not in url_map:
            return to_url

        from_path = url_map.get(from_url, '')
        to_path = url_map[to_url]

        if not from_path:
            return to_path

        # Calculate relative path
        from_parts = from_path.split('/')
        to_parts = to_path.split('/')

        # Find common prefix
        common_length = 0
        for i, (a, b) in enumerate(zip(from_parts[:-1], to_parts[:-1])):
            if a == b:
                common_length = i + 1
            else:
                break

        # Build relative path
        up_levels = len(from_parts) - common_length - 1
        relative = '../' * up_levels + '/'.join(to_parts[common_length:])

        return relative or '.'
