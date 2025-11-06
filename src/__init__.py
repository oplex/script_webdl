"""
WebDL - A wget-style website downloader for offline viewing.

This package provides tools for downloading entire websites with
humanized behavior to avoid bot detection, organizing content for
offline viewing, and converting links to work locally.
"""

from .crawler import Crawler
from .downloader import Downloader
from .storage import Storage
from .parser import LinkExtractor, LinkConverter

__version__ = '1.0.0'
__all__ = ['Crawler', 'Downloader', 'Storage', 'LinkExtractor', 'LinkConverter']
