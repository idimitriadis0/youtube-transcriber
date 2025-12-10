"""File I/O utilities for handling inputs and generating output paths."""

import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs
import mimetypes


class FileUtils:
    """Utilities for file operations."""

    SAFE_FILENAME_PATTERN = re.compile(r"[^\w\-. ]", re.UNICODE)
    MULTIPLE_DOTS = re.compile(r"\.{2,}")
    MULTIPLE_SPACES = re.compile(r" {2,}")

    SUPPORTED_AUDIO_FORMATS = {
        ".mp3",
        ".wav",
        ".m4a",
        ".flac",
        ".ogg",
        ".aac",
        ".wma",
    }
    SUPPORTED_VIDEO_FORMATS = {
        ".mp4",
        ".webm",
        ".mkv",
        ".avi",
        ".mov",
        ".flv",
        ".m4v",
    }

    @classmethod
    def sanitize_filename(cls, filename: str, max_length: int = 200) -> str:
        """Sanitize filename to be safe across filesystems.

        Args:
            filename: Original filename or title
            max_length: Maximum length for the filename

        Returns:
            Safe filename
        """
        # Remove unsafe characters
        safe = cls.SAFE_FILENAME_PATTERN.sub("-", filename)
        # Replace multiple dots with single
        safe = cls.MULTIPLE_DOTS.sub(".", safe)
        # Replace multiple spaces with single
        safe = cls.MULTIPLE_SPACES.sub(" ", safe)
        # Strip leading/trailing spaces and dots
        safe = safe.strip(" .")
        # Limit length
        if len(safe) > max_length:
            safe = safe[:max_length].rsplit(" ", 1)[0].rstrip(".")
        return safe or "transcript"

    @classmethod
    def generate_output_path(
        cls,
        base_name: str,
        language: str,
        format: str,
        output_dir: Path,
    ) -> Path:
        """Generate output path with format suffix.

        Args:
            base_name: Base filename (without extension)
            language: Language code
            format: Output format (txt, srt, etc.)
            output_dir: Output directory

        Returns:
            Full output path
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{base_name}.{language}.{format}"
        return output_dir / filename

    @classmethod
    def extract_base_name(cls, source: str | Path) -> str:
        """Extract base name from file path or URL.

        Args:
            source: File path or URL

        Returns:
            Safe base filename
        """
        if isinstance(source, Path):
            # Remove extension
            name = source.stem
        else:
            # Try to extract from URL
            name = cls._extract_from_url(source)

        return cls.sanitize_filename(name)

    @classmethod
    def _extract_from_url(cls, url: str) -> str:
        """Extract title/ID from URL.

        Handles YouTube, Vimeo, and generic URLs.
        """
        # YouTube
        if "youtube.com" in url or "youtu.be" in url:
            # Try to get video ID
            if "youtu.be/" in url:
                video_id = url.split("youtu.be/")[-1].split("?")[0]
            else:
                parsed = parse_qs(urlparse(url).query)
                video_id = parsed.get("v", [""])[0]
            return video_id or "youtube-video"

        # Generic URL: extract domain and path
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        path = parsed.path.strip("/").split("/")[-1]
        return path or domain or "recording"

    @classmethod
    def is_valid_file(cls, path: Path) -> bool:
        """Check if file is a supported audio or video format."""
        suffix = path.suffix.lower()
        return suffix in (cls.SUPPORTED_AUDIO_FORMATS | cls.SUPPORTED_VIDEO_FORMATS)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        """Basic URL validation."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False


class InputValidator:
    """Validate input sources and options."""

    @staticmethod
    def validate_urls(urls: str) -> tuple[list[str], list[str]]:
        """Parse and validate URLs from text input.

        Args:
            urls: Newline-separated URLs

        Returns:
            Tuple of (valid_urls, error_messages)
        """
        valid = []
        errors = []

        for line in urls.strip().split("\n"):
            url = line.strip()
            if not url:
                continue
            if FileUtils.is_valid_url(url):
                valid.append(url)
            else:
                errors.append(f"Invalid URL: {url}")

        return valid, errors

    @staticmethod
    def validate_files(paths: list[Path]) -> tuple[list[Path], list[str]]:
        """Validate file paths.

        Args:
            paths: File paths to validate

        Returns:
            Tuple of (valid_files, error_messages)
        """
        valid = []
        errors = []

        for path in paths:
            if not path.exists():
                errors.append(f"File not found: {path}")
            elif not path.is_file():
                errors.append(f"Not a file: {path}")
            elif not FileUtils.is_valid_file(path):
                errors.append(f"Unsupported format: {path.suffix}")
            else:
                valid.append(path)

        return valid, errors
