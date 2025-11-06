#!/usr/bin/env python3
"""
WebDL - wget-style website downloader.

A self-contained command-line tool for downloading entire websites for offline
viewing with humanized behavior, link conversion, and incremental updates.

Auto-setup: Creates venv and installs dependencies on first run.

Usage:
    python3 webdl.py example.com
    python3 webdl.py https://example.com/page
    python3 webdl.py example.com --max-depth 5 --max-pages 500
    python3 webdl.py example.com --no-git  # Skip git commit
"""

import sys
import os
import subprocess
from pathlib import Path


def get_script_dir():
    """Get the directory where this script is located."""
    return Path(__file__).parent.resolve()


def is_venv():
    """Check if currently running in a virtual environment."""
    return (hasattr(sys, 'real_prefix') or
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))


def get_venv_path():
    """Get the path to the venv directory."""
    return get_script_dir() / 'venv'


def get_venv_python():
    """Get the path to the Python executable in venv."""
    venv_path = get_venv_path()
    if sys.platform == 'win32':
        return venv_path / 'Scripts' / 'python.exe'
    return venv_path / 'bin' / 'python'


def setup_environment():
    """
    Bootstrap the environment: create venv if needed, install dependencies.

    Returns:
        True if setup was performed and script needs to restart in venv
    """
    script_dir = get_script_dir()
    venv_path = get_venv_path()
    requirements_file = script_dir / 'requirements.txt'

    # If we're already in venv, check dependencies
    if is_venv():
        try:
            import requests
            import bs4
            return False  # All good, continue
        except ImportError:
            pass  # Need to install dependencies

    # Create venv if it doesn't exist
    if not venv_path.exists():
        print(f"Creating virtual environment at {venv_path}...")
        subprocess.check_call([sys.executable, '-m', 'venv', str(venv_path)])
        print("Virtual environment created.")

    # Get venv Python
    venv_python = get_venv_python()

    if not venv_python.exists():
        print(f"Error: Could not find venv Python at {venv_python}", file=sys.stderr)
        sys.exit(1)

    # Install/upgrade pip
    print("Ensuring pip is up to date...")
    subprocess.check_call([str(venv_python), '-m', 'pip', 'install', '--upgrade', 'pip'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Install requirements if file exists
    if requirements_file.exists():
        print("Installing dependencies...")
        subprocess.check_call([str(venv_python), '-m', 'pip', 'install', '-q', '-r',
                              str(requirements_file)])
        print("Dependencies installed.")

    # If we're not in venv, restart in venv
    if not is_venv():
        print("Restarting in virtual environment...\n")
        os.execv(str(venv_python), [str(venv_python), __file__] + sys.argv[1:])

    return False


def main():
    """Main entry point for the CLI."""
    # Bootstrap environment first
    if '--help' not in sys.argv and '-h' not in sys.argv:
        setup_environment()

    # Now we can import our modules (we're in venv with deps installed)
    import logging
    import argparse
    from urllib.parse import urlparse

    from src.crawler import Crawler
    from src.config import MAX_DEPTH, MAX_PAGES

    def setup_logging(verbose: bool = False):
        """Configure logging for the application."""
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )

    def normalize_domain(domain: str) -> str:
        """Normalize domain input to full URL."""
        domain = domain.strip()
        if not domain.startswith(('http://', 'https://')):
            domain = 'https://' + domain
        return domain

    def validate_url(url: str) -> bool:
        """Validate that URL is properly formed."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    # Parse arguments
    parser = argparse.ArgumentParser(
        description='WebDL - Download websites for offline viewing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s example.com
  %(prog)s https://example.com/page
  %(prog)s example.com --max-depth 5 --max-pages 500
  %(prog)s example.com --verbose
  %(prog)s example.com --no-git

Features:
  - Auto-setup: Creates venv and installs dependencies on first run
  - Humanized crawling: Random delays, browser headers, avoids bot detection
  - Per-site git: Each site gets its own git repo (excludes heavy files)
  - Parallel safe: Run multiple downloads simultaneously
  - Incremental: Re-run to update existing sites

Downloaded sites are saved to: sites/domain/
Each site has its own git repo tracking HTML/CSS/JS changes.
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
        '--no-git',
        action='store_true',
        help='Skip git commit after download'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose debug logging'
    )

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
        crawler = Crawler(
            url,
            max_depth=args.max_depth,
            max_pages=args.max_pages,
            enable_git=not args.no_git
        )
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
