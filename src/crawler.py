"""
Web crawler for recursive website downloading.

This module coordinates the downloading process, managing the queue of URLs
to download, tracking visited pages, and orchestrating the link extraction
and conversion process.
"""

import logging
from urllib.parse import urlparse, urljoin
from collections import deque
from typing import Set, Dict, Optional
import sys

from .downloader import Downloader, DownloadError, normalize_url, get_domain
from .parser import LinkExtractor, LinkConverter
from .storage import Storage
from .contacts import ContactExtractor
from .config import MAX_DEPTH, MAX_PAGES, DOWNLOADABLE_EXTENSIONS

logger = logging.getLogger(__name__)


class Crawler:
    """
    Recursive web crawler for downloading entire websites.

    Manages the crawl queue, tracks visited URLs, downloads pages,
    extracts links, and converts content for offline viewing.
    """

    def __init__(self, start_url: str, max_depth: int = MAX_DEPTH,
                 max_pages: int = MAX_PAGES, enable_git: bool = True):
        """
        Initialize the crawler.

        Args:
            start_url: Starting URL to crawl from
            max_depth: Maximum depth to crawl
            max_pages: Maximum number of pages to download
            enable_git: Whether to initialize git and commit changes
        """
        self.start_url = normalize_url(start_url, start_url)
        self.domain = get_domain(self.start_url)
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.enable_git = enable_git

        self.downloader = Downloader()
        self.storage = Storage(self.domain)
        self.link_extractor = LinkExtractor(self.start_url)
        self.link_converter = LinkConverter(self.domain)

        # Crawl state
        self.queue = deque([(self.start_url, 0)])  # (url, depth)
        self.visited = set()
        self.url_map = {}  # Maps URLs to local file paths
        self.pending_conversions = []  # HTML pages that need link conversion

        # Initialize git if enabled
        if self.enable_git:
            self.storage.init_git()

        logger.info(f"Initialized crawler for {self.domain}")

    def crawl(self):
        """
        Start crawling from the starting URL.

        Downloads pages recursively up to max_depth and max_pages,
        then converts all links for offline viewing.
        """
        logger.info(f"Starting crawl of {self.start_url}")
        logger.info(f"Max depth: {self.max_depth}, Max pages: {self.max_pages}")

        try:
            # Phase 1: Download all pages
            self._download_phase()

            # Phase 2: Convert links in HTML pages
            self._conversion_phase()

            # Phase 3: Extract contact information
            self._extract_contacts()

            # Phase 4: Commit to git if enabled
            if self.enable_git:
                logger.info("")
                logger.info("=" * 60)
                logger.info("PHASE 4: Committing changes to git")
                logger.info("=" * 60)
                self.storage.git_commit()

            # Show statistics
            self._print_stats()

        except KeyboardInterrupt:
            logger.info("\nCrawl interrupted by user")
            self._print_stats()
            sys.exit(0)

        finally:
            self.downloader.close()

    def _download_phase(self):
        """Download all pages in the queue."""
        logger.info("=" * 60)
        logger.info("PHASE 1: Downloading pages")
        logger.info("=" * 60)

        while self.queue and len(self.visited) < self.max_pages:
            url, depth = self.queue.popleft()

            if url in self.visited:
                continue

            if depth > self.max_depth:
                logger.debug(f"Skipping {url} (max depth reached)")
                continue

            self.visited.add(url)

            try:
                # Download the page
                content, content_type, final_url = self.downloader.download(url)

                # Save to storage
                file_path = self.storage.save_file(final_url, content, content_type)
                self.url_map[final_url] = file_path

                # If it's HTML, extract links
                if content_type.startswith('text/html'):
                    self._process_html(final_url, content, depth)

                # Progress indicator
                print(f"[{len(self.visited)}/{self.max_pages}] {url}", flush=True)

            except DownloadError as e:
                logger.warning(f"Failed to download {url}: {e}")
                continue

            except Exception as e:
                logger.error(f"Unexpected error downloading {url}: {e}")
                continue

    def _process_html(self, url: str, content: bytes, depth: int):
        """
        Process HTML content and extract links.

        Args:
            url: URL of the page
            content: HTML content bytes
            depth: Current crawl depth
        """
        try:
            html = content.decode('utf-8', errors='ignore')
            self.link_extractor.base_url = url

            # Extract all links
            links = self.link_extractor.extract_links(html)

            # Save for later conversion
            self.pending_conversions.append((url, html))

            # Add same-domain HTML links to queue
            for link in links:
                if self._should_crawl(link, depth):
                    self.queue.append((link, depth + 1))

                # Download resources from this domain
                if self._should_download(link):
                    if link not in self.visited and link not in [u for u, _ in self.queue]:
                        self.queue.append((link, depth + 1))

        except Exception as e:
            logger.error(f"Error processing HTML from {url}: {e}")

    def _should_crawl(self, url: str, current_depth: int) -> bool:
        """
        Determine if URL should be crawled (followed for more links).

        Args:
            url: URL to check
            current_depth: Current crawl depth

        Returns:
            True if URL should be crawled
        """
        if url in self.visited:
            return False

        if current_depth >= self.max_depth:
            return False

        if not self.link_extractor.is_same_domain(url):
            return False

        # Only crawl HTML pages
        parsed = urlparse(url)
        path = parsed.path.lower()

        # Skip if has non-HTML extension
        for ext in DOWNLOADABLE_EXTENSIONS:
            if path.endswith(ext) and ext not in ('.html', '.htm'):
                return False

        return True

    def _should_download(self, url: str) -> bool:
        """
        Determine if URL should be downloaded (even if not crawled).

        Args:
            url: URL to check

        Returns:
            True if URL should be downloaded
        """
        if url in self.visited:
            return False

        if not self.link_extractor.is_same_domain(url):
            return False

        # Check if extension is downloadable
        parsed = urlparse(url)
        path = parsed.path.lower()

        # Download if no extension or known extension
        if '.' not in path.split('/')[-1]:
            return True

        for ext in DOWNLOADABLE_EXTENSIONS:
            if path.endswith(ext):
                return True

        return False

    def _conversion_phase(self):
        """Convert links in all HTML pages to relative paths."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("PHASE 2: Converting links for offline viewing")
        logger.info("=" * 60)

        for i, (url, html) in enumerate(self.pending_conversions):
            try:
                converted_html = self.link_converter.convert_html(
                    html, url, self.url_map
                )

                # Save converted HTML
                file_path = self.url_map[url]
                full_path = self.storage.site_dir / file_path

                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(converted_html)

                print(f"[{i+1}/{len(self.pending_conversions)}] Converted {url}", flush=True)

            except Exception as e:
                logger.error(f"Error converting {url}: {e}")

    def _extract_contacts(self):
        """Extract contact information from downloaded pages and git history."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("PHASE 3: Extracting contact information")
        logger.info("=" * 60)

        try:
            extractor = ContactExtractor(self.storage.site_dir, self.domain)
            extractor.extract_all()
        except Exception as e:
            logger.error(f"Error extracting contacts: {e}")

    def _print_stats(self):
        """Print crawl statistics."""
        stats = self.storage.get_stats()

        logger.info("")
        logger.info("=" * 60)
        logger.info("CRAWL COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Domain: {stats['domain']}")
        logger.info(f"Pages downloaded: {len(self.visited)}")
        logger.info(f"Total files: {stats['total_files']}")
        logger.info(f"Total size: {stats['total_size'] / (1024*1024):.2f} MB")
        logger.info(f"Saved to: {stats['directory']}")
        logger.info("=" * 60)
