"""
Contact information extractor for downloaded websites.

Scans HTML pages and git history to extract emails, phone numbers,
and social media handles with deduplication.
"""

import re
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class ContactExtractor:
    """Extracts and stores contact information from website content."""

    # Regex patterns
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', re.I)
    PHONE_PATTERN = re.compile(r'(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', re.I)
    TWITTER_PATTERN = re.compile(r'(?:https?://)?(?:www\.)?twitter\.com/([a-zA-Z0-9_]{1,15})', re.I)
    LINKEDIN_PATTERN = re.compile(r'(?:https?://)?(?:www\.)?linkedin\.com/(?:in|company)/([a-zA-Z0-9-]+)', re.I)
    FACEBOOK_PATTERN = re.compile(r'(?:https?://)?(?:www\.)?facebook\.com/([a-zA-Z0-9.]+)', re.I)
    GITHUB_PATTERN = re.compile(r'(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9-]+)', re.I)
    INSTAGRAM_PATTERN = re.compile(r'(?:https?://)?(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)', re.I)

    EXCLUDE_PATTERNS = {
        'example.com', 'example.org', 'test.com', 'localhost',
        'placeholder', 'youremail', 'your-email', 'email@example',
        'noreply', 'no-reply'
    }

    def __init__(self, site_dir: Path, domain: str):
        self.site_dir = site_dir
        self.domain = domain
        self.contacts_file = site_dir / 'contacts.json'
        self.contacts = self._load_contacts()

    def _load_contacts(self) -> Dict:
        """Load existing contacts from JSON file."""
        if self.contacts_file.exists():
            try:
                with open(self.contacts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load contacts: {e}")

        return {
            'domain': self.domain,
            'last_updated': None,
            'emails': [],
            'phones': [],
            'social_media': {
                'twitter': [], 'linkedin': [], 'facebook': [],
                'github': [], 'instagram': []
            }
        }

    def _save_contacts(self):
        """Save contacts to JSON file."""
        self.contacts['last_updated'] = datetime.utcnow().isoformat()
        try:
            with open(self.contacts_file, 'w', encoding='utf-8') as f:
                json.dump(self.contacts, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved contacts to {self.contacts_file}")
        except Exception as e:
            logger.error(f"Failed to save contacts: {e}")

    def _is_valid_email(self, email: str) -> bool:
        """Check if email is valid and not a placeholder."""
        email_lower = email.lower()
        for pattern in self.EXCLUDE_PATTERNS:
            if pattern in email_lower:
                return False

        parts = email.split('@')
        if len(parts) != 2:
            return False

        domain = parts[1].lower()
        return domain not in ['example.com', 'test.com', 'example.org']

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to consistent format."""
        return re.sub(r'[^\d+]', '', phone)

    def extract_from_text(self, text: str) -> Dict:
        """Extract contact information from text."""
        found = {
            'emails': set(), 'phones': set(),
            'twitter': set(), 'linkedin': set(), 'facebook': set(),
            'github': set(), 'instagram': set()
        }

        # Extract emails
        for match in self.EMAIL_PATTERN.finditer(text):
            email = match.group(0).lower()
            if self._is_valid_email(email):
                found['emails'].add(email)

        # Extract phone numbers
        for match in self.PHONE_PATTERN.finditer(text):
            phone = self._normalize_phone(match.group(0))
            if len(phone) >= 10:
                found['phones'].add(phone)

        # Extract social media handles
        for match in self.TWITTER_PATTERN.finditer(text):
            found['twitter'].add(match.group(1))
        for match in self.LINKEDIN_PATTERN.finditer(text):
            found['linkedin'].add(match.group(1))
        for match in self.FACEBOOK_PATTERN.finditer(text):
            found['facebook'].add(match.group(1))
        for match in self.GITHUB_PATTERN.finditer(text):
            found['github'].add(match.group(1))
        for match in self.INSTAGRAM_PATTERN.finditer(text):
            found['instagram'].add(match.group(1))

        return found

    def scan_directory(self):
        """Scan all HTML files in site directory for contacts."""
        logger.info(f"Scanning {self.site_dir} for contact information...")

        total_found = {
            'emails': set(), 'phones': set(),
            'twitter': set(), 'linkedin': set(), 'facebook': set(),
            'github': set(), 'instagram': set()
        }

        html_files = list(self.site_dir.glob('**/*.html')) + \
                     list(self.site_dir.glob('**/*.htm'))

        for html_file in html_files:
            if '.git' in html_file.parts:
                continue

            try:
                with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    found = self.extract_from_text(content)
                    for key in total_found:
                        total_found[key].update(found[key])
            except Exception as e:
                logger.warning(f"Failed to scan {html_file}: {e}")

        self._merge_contacts(total_found)
        logger.info(f"Found {len(total_found['emails'])} emails, "
                   f"{len(total_found['phones'])} phones")

    def scan_git_history(self):
        """Scan git history for contact information."""
        git_dir = self.site_dir / '.git'
        if not git_dir.exists():
            logger.debug("No git repository, skipping history scan")
            return

        try:
            result = subprocess.run(
                ['git', 'log', '--all', '--pretty=format:', '--name-only'],
                cwd=self.site_dir, capture_output=True, text=True, check=True
            )

            files = set(result.stdout.strip().split('\n'))
            total_found = {
                'emails': set(), 'phones': set(),
                'twitter': set(), 'linkedin': set(), 'facebook': set(),
                'github': set(), 'instagram': set()
            }

            for file_path in files:
                if not file_path or not file_path.endswith(('.html', '.htm')):
                    continue

                try:
                    result = subprocess.run(
                        ['git', 'show', f'HEAD:{file_path}'],
                        cwd=self.site_dir, capture_output=True, text=True, check=False
                    )

                    if result.returncode == 0:
                        found = self.extract_from_text(result.stdout)
                        for key in total_found:
                            total_found[key].update(found[key])
                except Exception as e:
                    logger.debug(f"Failed to scan git history for {file_path}: {e}")

            self._merge_contacts(total_found)

        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to scan git history: {e}")
        except FileNotFoundError:
            logger.warning("git not found, skipping history scan")

    def _merge_contacts(self, found: Dict):
        """Merge found contacts with existing contacts (deduplication)."""
        # Merge emails
        existing_emails = set(self.contacts['emails'])
        new_emails = found['emails'] - existing_emails
        if new_emails:
            self.contacts['emails'].extend(sorted(new_emails))
            logger.info(f"Added {len(new_emails)} new emails")

        # Merge phones
        existing_phones = set(self.contacts['phones'])
        new_phones = found['phones'] - existing_phones
        if new_phones:
            self.contacts['phones'].extend(sorted(new_phones))
            logger.info(f"Added {len(new_phones)} new phone numbers")

        # Merge social media
        for platform in ['twitter', 'linkedin', 'facebook', 'github', 'instagram']:
            existing = set(self.contacts['social_media'][platform])
            new_handles = found[platform] - existing
            if new_handles:
                self.contacts['social_media'][platform].extend(sorted(new_handles))
                logger.info(f"Added {len(new_handles)} new {platform} handles")

    def extract_all(self):
        """Extract all contacts from directory and git history."""
        logger.info("=" * 60)
        logger.info("EXTRACTING CONTACT INFORMATION")
        logger.info("=" * 60)

        self.scan_directory()
        self.scan_git_history()
        self._save_contacts()
        self._print_summary()

    def _print_summary(self):
        """Print summary of extracted contacts."""
        logger.info("")
        logger.info("Contact Information Summary:")
        logger.info(f"  Emails: {len(self.contacts['emails'])}")
        logger.info(f"  Phones: {len(self.contacts['phones'])}")

        for platform, handles in self.contacts['social_media'].items():
            if handles:
                logger.info(f"  {platform.capitalize()}: {len(handles)}")

        logger.info(f"  Saved to: {self.contacts_file}")
        logger.info("=" * 60)
