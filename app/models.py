"""Data models for transcription jobs and results."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QualityPreset(str, Enum):
    """Quality/speed presets for transcription."""

    FAST = "fast"
    BALANCED = "balanced"
    BEST_QUALITY = "best_quality"


class TimestampLevel(str, Enum):
    """Timestamp granularity."""

    NONE = "none"
    WORD = "word"
    UTTERANCE = "utterance"


class TranscriptionOptions(BaseModel):
    """Options for a transcription job."""

    source: str | Path = Field(..., description="URL or file path")
    language: str = Field(default="auto", description="Language code")
    quality: QualityPreset = Field(
        default=QualityPreset.BALANCED, description="Quality preset"
    )
    diarization: bool = Field(
        default=False, description="Enable speaker diarization if supported"
    )
    smart_format: bool = Field(
        default=True, description="Apply smart punctuation and formatting"
    )
    timestamps: TimestampLevel = Field(
        default=TimestampLevel.UTTERANCE, description="Timestamp granularity"
    )
    output_formats: List[str] = Field(
        default=["txt", "srt"], description="Output formats to generate"
    )

    class Config:
        use_enum_values = False


class Segment(BaseModel):
    """A single transcript segment with timing."""

    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Transcript text")
    speaker: Optional[str] = Field(None, description="Speaker ID if diarization enabled")
    confidence: Optional[float] = Field(
        None, description="Confidence score (0.0-1.0) if available"
    )


class TranscriptionResult(BaseModel):
    """Result of a transcription job."""

    text: str = Field(..., description="Full transcript text")
    language: str = Field(..., description="Detected or requested language")
    segments: List[Segment] = Field(..., description="Segments with timestamps")
    duration: float = Field(..., description="Total duration in seconds")
    raw_response: Optional[Dict[str, Any]] = Field(
        None, description="Raw API response for debugging"
    )


@dataclass
class TranscriptionJob:
    """A transcription job in the queue."""

    id: str
    source: str | Path
    status: JobStatus = JobStatus.PENDING
    options: TranscriptionOptions = field(default_factory=TranscriptionOptions)
    result: Optional[TranscriptionResult] = None
    error: Optional[str] = None
    output_paths: Dict[str, Path] = field(default_factory=dict)  # format -> path
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def source_name(self) -> str:
        """Get human-readable source name."""
        if isinstance(self.source, Path):
            return self.source.name
        return self.source[:50]  # truncate URLs

    @property
    def elapsed_time(self) -> Optional[float]:
        """Get elapsed time in seconds, if job has started."""
        if not self.started_at:
            return None
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()
