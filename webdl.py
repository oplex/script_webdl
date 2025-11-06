#!/usr/bin/env python3
"""
WebDL - wget-style website downloader.

A command-line tool for downloading entire websites for offline viewing
with humanized behavior, link conversion, and incremental updates.

Usage:
    python3 webdl.py example.com
    python3 webdl.py https://example.com/page
    python3 webdl.py example.com --max-depth 5 --max-pages 500
"""

import sys
import logging
import argparse
from urllib.parse import urlparse

from src.crawler import Crawler
from src.config import MAX_DEPTH, MAX_PAGES


def setup_logging(verbose: bool = False):
    """
    Configure logging for the application.

    Args:
        verbose: If True, set log level to DEBUG
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )


def normalize_domain(domain: str) -> str:
    """
    Normalize domain input to full URL.

    Args:
        domain: Domain or URL string

    Returns:
        Full URL with scheme
    """
    domain = domain.strip()

    # Add scheme if missing
    if not domain.startswith(('http://', 'https://')):
        domain = 'https://' + domain

    return domain


def validate_url(url: str) -> bool:
    """
    Validate that URL is properly formed.

    Args:
        url: URL to validate

    Returns:
        True if URL is valid
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description='WebDL - Download websites for offline viewing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s example.com
  %(prog)s https://example.com/page
  %(prog)s example.com --max-depth 5 --max-pages 500
  %(prog)s example.com --verbose

Downloaded sites are saved to: sites/domain/
        """
    )

    parser.add_argument(
        'domain',
        help='Domain or URL to download (e.g., example.com)'
    )

    parser.add_argument(
        '--max-depth',
        type=int,
        default=MAX_DEPTH,
        help=f'Maximum crawl depth (default: {MAX_DEPTH})'
    )

    parser.add_argument(
        '--max-pages',
        type=int,
        default=MAX_PAGES,
        help=f'Maximum number of pages to download (default: {MAX_PAGES})'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose debug logging'
    )

    # Parse arguments
    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Normalize and validate URL
    url = normalize_domain(args.domain)

    if not validate_url(url):
        print(f"Error: Invalid URL: {url}", file=sys.stderr)
        sys.exit(1)

    # Create crawler and start
    try:
        crawler = Crawler(url, max_depth=args.max_depth, max_pages=args.max_pages)
        crawler.crawl()

    except KeyboardInterrupt:
        print("\nDownload interrupted by user")
        sys.exit(0)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
