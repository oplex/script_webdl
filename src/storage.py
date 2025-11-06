"""
Storage and file organization system.

This module manages the local storage of downloaded content,
organizing files into a sites/domain/ structure and handling
file naming, paths, and incremental updates.
"""

import os
import hashlib
import json
import logging
from pathlib import Path
from urllib.parse import urlparse, unquote
from typing import Optional, Dict
from datetime import datetime

from .config import SITES_DIR, INDEX_FILE

logger = logging.getLogger(__name__)


class Storage:
    """
    Manages local storage of downloaded website content.

    Organizes files by domain, handles path generation, and tracks
    download metadata for incremental updates.
    """

    def __init__(self, domain: str, base_dir: str = SITES_DIR):
        """
        Initialize storage for a domain.

        Args:
            domain: Domain name (e.g., 'example.com')
            base_dir: Base directory for storing sites
        """
        self.domain = domain
        self.base_dir = Path(base_dir)
        self.site_dir = self.base_dir / self._sanitize_domain(domain)
        self.metadata_file = self.site_dir / '.metadata.json'
        self.metadata = {}

        self._ensure_directory()
        self._load_metadata()

    def _sanitize_domain(self, domain: str) -> str:
        """
        Sanitize domain name for use as directory name.

        Args:
            domain: Domain name to sanitize

        Returns:
            Sanitized domain name safe for filesystem
        """
        # Remove port numbers
        domain = domain.split(':')[0]
        # Replace invalid characters
        safe_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_')
        sanitized = ''.join(c if c in safe_chars else '_' for c in domain)
        return sanitized

    def _ensure_directory(self):
        """Create site directory if it doesn't exist."""
        self.site_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Site directory: {self.site_dir}")

    def _load_metadata(self):
        """Load download metadata from file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                logger.info(f"Loaded metadata for {len(self.metadata)} files")
            except Exception as e:
                logger.warning(f"Failed to load metadata: {e}")
                self.metadata = {}

    def _save_metadata(self):
        """Save download metadata to file."""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")

    def url_to_path(self, url: str) -> str:
        """
        Convert URL to local file path.

        Args:
            url: URL to convert

        Returns:
            Local file path relative to site directory
        """
        parsed = urlparse(url)
        path = unquote(parsed.path)

        # Handle root or directory paths
        if not path or path == '/':
            return INDEX_FILE

        if path.endswith('/'):
            return path.lstrip('/') + INDEX_FILE

        # Remove leading slash
        path = path.lstrip('/')

        # Add index.html to paths without extension
        if not os.path.splitext(path)[1]:
            path = os.path.join(path, INDEX_FILE)

        return path

    def save_file(self, url: str, content: bytes, content_type: str) -> str:
        """
        Save downloaded content to file.

        Args:
            url: URL of the content
            content: Content bytes
            content_type: MIME type of content

        Returns:
            Local file path where content was saved
        """
        file_path = self.url_to_path(url)
        full_path = self.site_dir / file_path

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        try:
            # Handle text content with proper encoding
            if content_type.startswith('text/') or content_type in (
                'application/javascript', 'application/json', 'application/xml'
            ):
                try:
                    text = content.decode('utf-8')
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(text)
                except UnicodeDecodeError:
                    # Fallback to binary write
                    with open(full_path, 'wb') as f:
                        f.write(content)
            else:
                # Binary content
                with open(full_path, 'wb') as f:
                    f.write(content)

            # Update metadata
            content_hash = hashlib.md5(content).hexdigest()
            self.metadata[url] = {
                'path': file_path,
                'content_type': content_type,
                'size': len(content),
                'hash': content_hash,
                'timestamp': datetime.utcnow().isoformat(),
            }
            self._save_metadata()

            logger.info(f"Saved: {file_path} ({len(content)} bytes)")
            return file_path

        except Exception as e:
            logger.error(f"Failed to save {file_path}: {e}")
            raise

    def get_file_path(self, url: str) -> Optional[Path]:
        """
        Get local file path for URL if it exists.

        Args:
            url: URL to look up

        Returns:
            Path object if file exists, None otherwise
        """
        if url in self.metadata:
            file_path = self.metadata[url]['path']
            full_path = self.site_dir / file_path
            if full_path.exists():
                return full_path
        return None

    def is_downloaded(self, url: str) -> bool:
        """
        Check if URL has been downloaded.

        Args:
            url: URL to check

        Returns:
            True if URL exists in metadata and file exists
        """
        return self.get_file_path(url) is not None

    def needs_update(self, url: str, content: bytes) -> bool:
        """
        Check if downloaded file needs updating.

        Args:
            url: URL to check
            content: New content to compare

        Returns:
            True if content has changed or doesn't exist
        """
        if url not in self.metadata:
            return True

        new_hash = hashlib.md5(content).hexdigest()
        old_hash = self.metadata[url].get('hash')

        return new_hash != old_hash

    def get_site_directory(self) -> Path:
        """
        Get the site directory path.

        Returns:
            Path object for site directory
        """
        return self.site_dir

    def get_stats(self) -> Dict:
        """
        Get download statistics.

        Returns:
            Dictionary with download stats
        """
        total_size = sum(meta.get('size', 0) for meta in self.metadata.values())
        return {
            'domain': self.domain,
            'total_files': len(self.metadata),
            'total_size': total_size,
            'directory': str(self.site_dir),
        }
