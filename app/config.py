"""Configuration management for the transcription utility."""

from pathlib import Path
from typing import Dict, List
import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()


class AppConfig:
    """Application configuration."""

    # Output directory (defaults to ./transcriptions)
    OUTPUT_DIR: Path = Path(os.getenv("TRANSCRIBER_OUTPUT_DIR", "./transcriptions"))

    # Supported languages
    LANGUAGES: List[str] = [
        "auto",
        "en",
        "fr",
        "de",
        "es",
        "hi",
        "ja",
        "zh",
        "ru",
        "ar",
        "pt",
        "it",
    ]

    # Quality presets
    QUALITY_PRESETS: Dict[str, dict] = {
        "fast": {"model": "whisper-base", "timeout": 60},
        "balanced": {"model": "whisper-small", "timeout": 120},
        "best_quality": {"model": "whisper-medium", "timeout": 300},
    }

    # Output formats
    OUTPUT_FORMATS: List[str] = ["txt", "md", "srt", "vtt", "json"]

    # Max batch size
    MAX_BATCH_SIZE: int = 50

    # Default configuration
    DEFAULTS: Dict = {
        "language": "en",
        "quality": "balanced",
        "diarization": False,
        "smart_format": True,
        "timestamps": "utterance",  # none | word | utterance
        "output_formats": ["txt", "srt"],
    }

    @classmethod
    def ensure_output_dir(cls) -> None:
        """Create output directory if it doesn't exist."""
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# API Configuration (for plugging in real providers)
class APIConfig:
    """API configuration for transcription providers.

    TODO: Configure with your chosen provider (Deepgram, Whisper, etc.)
    """

    # Example: Deepgram configuration
    DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "")
    DEEPGRAM_API_URL: str = "https://api.deepgram.com/v1/listen"

    # Example: OpenAI Whisper configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_URL: str = "https://api.openai.com/v1/audio/transcriptions"

    # Example: Generic provider configuration
    PROVIDER: str = os.getenv("TRANSCRIBER_PROVIDER", "mock")  # mock | deepgram | whisper | custom

    @classmethod
    def validate(cls) -> bool:
        """Validate that required API keys are present."""
        if cls.PROVIDER == "mock":
            return True
        if cls.PROVIDER == "deepgram" and not cls.DEEPGRAM_API_KEY:
            return False
        if cls.PROVIDER == "whisper" and not cls.OPENAI_API_KEY:
            return False
        return True
