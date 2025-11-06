"""
Git operations for per-site version control.

This module handles git initialization, .gitignore creation,
and automatic commits for downloaded websites.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class GitManager:
    """
    Manages git operations for a site directory.

    Handles initialization, .gitignore creation, and commits
    while excluding heavy files from version control.
    """

    # Files to exclude from git (heavy binary files)
    GITIGNORE_TEMPLATE = """# Heavy files - exclude from git
*.jpg
*.jpeg
*.png
*.gif
*.webp
*.svg
*.ico
*.bmp
*.tiff
*.mp4
*.avi
*.mov
*.wmv
*.flv
*.webm
*.mp3
*.wav
*.ogg
*.pdf
*.zip
*.tar
*.gz
*.rar
*.7z
*.exe
*.dmg
*.pkg
*.deb
*.rpm

# Metadata
.metadata.json
"""

    def __init__(self, site_dir: Path):
        """
        Initialize git manager for a site directory.

        Args:
            site_dir: Path to the site directory
        """
        self.site_dir = site_dir
        self.git_dir = site_dir / '.git'

    def init_repo(self):
        """
        Initialize git repository for the site with appropriate gitignore.

        Creates a .gitignore that excludes heavy files (images, videos, PDFs)
        while tracking HTML, CSS, JS, and other text files.
        """
        # Initialize git repo if not exists
        if not self.git_dir.exists():
            try:
                subprocess.run(
                    ['git', 'init'],
                    cwd=self.site_dir,
                    check=True,
                    capture_output=True
                )
                logger.info(f"Initialized git repository in {self.site_dir}")
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to initialize git: {e}")
                return
            except FileNotFoundError:
                logger.warning("git not found, skipping git initialization")
                return

        # Create .gitignore for heavy files
        gitignore_path = self.site_dir / '.gitignore'
        try:
            with open(gitignore_path, 'w', encoding='utf-8') as f:
                f.write(self.GITIGNORE_TEMPLATE)
            logger.info("Created .gitignore for heavy files")
        except Exception as e:
            logger.warning(f"Failed to create .gitignore: {e}")

    def commit(self, message: Optional[str] = None, stats: Optional[dict] = None):
        """
        Commit changes to the site's git repository.

        Args:
            message: Optional commit message. Auto-generated if not provided.
            stats: Optional stats dict for auto-generating message
        """
        if not self.git_dir.exists():
            logger.warning("Git repository not initialized, skipping commit")
            return

        try:
            # Add all files
            subprocess.run(
                ['git', 'add', '-A'],
                cwd=self.site_dir,
                check=True,
                capture_output=True
            )

            # Check if there are changes to commit
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.site_dir,
                check=True,
                capture_output=True,
                text=True
            )

            if not result.stdout.strip():
                logger.info("No changes to commit")
                return

            # Generate commit message if not provided
            if not message:
                if stats:
                    domain = stats.get('domain', 'unknown')
                    total_files = stats.get('total_files', 0)
                    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                    message = f"Update {domain} - {total_files} files - {timestamp}"
                else:
                    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                    message = f"Update site - {timestamp}"

            # Commit
            subprocess.run(
                ['git', 'commit', '-m', message],
                cwd=self.site_dir,
                check=True,
                capture_output=True
            )

            logger.info(f"Committed changes: {message}")

        except subprocess.CalledProcessError as e:
            logger.warning(f"Git commit failed: {e}")
        except FileNotFoundError:
            logger.warning("git not found, skipping commit")

    def is_initialized(self) -> bool:
        """
        Check if git repository is initialized.

        Returns:
            True if .git directory exists
        """
        return self.git_dir.exists()
