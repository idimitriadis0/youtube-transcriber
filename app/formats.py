"""Output format handlers for transcripts."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
import json
from datetime import datetime
from app.models import TranscriptionResult, Segment


def seconds_to_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format (hh:mm:ss,ms)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def seconds_to_vtt_time(seconds: float) -> str:
    """Convert seconds to VTT time format (hh:mm:ss.ms)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


class OutputFormatter(ABC):
    """Abstract base for output formatters."""

    @abstractmethod
    def format(self, result: TranscriptionResult) -> str:
        """Format transcription result."""
        pass


class PlainTextFormatter(OutputFormatter):
    """Plain text output (transcript only)."""

    def format(self, result: TranscriptionResult) -> str:
        """Return full transcript as plain text."""
        return result.text


class MarkdownFormatter(OutputFormatter):
    """Markdown output with metadata."""

    def format(self, result: TranscriptionResult) -> str:
        """Format as Markdown with metadata header."""
        lines = []
        lines.append("# Transcript")
        lines.append("")
        lines.append(
            f"**Language:** {result.language} | **Duration:** {result.duration:.1f}s | **Transcribed:** {datetime.now().isoformat()}"
        )
        lines.append("")
        lines.append("---")
        lines.append("")

        # Add segments with timestamps
        for segment in result.segments:
            start = seconds_to_srt_time(segment.start_time)
            end = seconds_to_srt_time(segment.end_time)
            speaker = f" ({segment.speaker})" if segment.speaker else ""
            lines.append(f"**[{start} - {end}]** {segment.text}{speaker}")
            lines.append("")

        return "\n".join(lines)


class SRTFormatter(OutputFormatter):
    """SRT (SubRip) subtitle format."""

    def format(self, result: TranscriptionResult) -> str:
        """Format as SRT with proper line breaks and numbering."""
        lines = []
        for idx, segment in enumerate(result.segments, 1):
            start = seconds_to_srt_time(segment.start_time)
            end = seconds_to_srt_time(segment.end_time)

            # Split text to max ~42 chars per line for readability
            text = self._wrap_text(segment.text, max_width=42)

            lines.append(str(idx))
            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")

        return "\n".join(lines).strip()

    @staticmethod
    def _wrap_text(text: str, max_width: int = 42) -> str:
        """Wrap text to max width, breaking on word boundaries."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            current_line.append(word)
            if len(" ".join(current_line)) > max_width:
                if len(current_line) > 1:
                    current_line.pop()  # Remove last word
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
                    current_line = []

        if current_line:
            lines.append(" ".join(current_line))

        return "\n".join(lines)


class VTTFormatter(OutputFormatter):
    """WebVTT subtitle format."""

    def format(self, result: TranscriptionResult) -> str:
        """Format as WebVTT."""
        lines = ["WEBVTT", ""]

        for segment in result.segments:
            start = seconds_to_vtt_time(segment.start_time)
            end = seconds_to_vtt_time(segment.end_time)

            # Wrap text similar to SRT
            text = SRTFormatter._wrap_text(segment.text, max_width=42)

            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")

        return "\n".join(lines).strip()


class JSONFormatter(OutputFormatter):
    """JSON output with full metadata."""

    def format(self, result: TranscriptionResult) -> str:
        """Format as JSON with pretty printing."""
        data = {
            "metadata": {
                "language": result.language,
                "duration": result.duration,
                "transcribed_at": datetime.now().isoformat(),
                "segment_count": len(result.segments),
            },
            "transcript": result.text,
            "segments": [
                {
                    "start": segment.start_time,
                    "end": segment.end_time,
                    "text": segment.text,
                    "speaker": segment.speaker,
                    "confidence": segment.confidence,
                }
                for segment in result.segments
            ],
        }
        if result.raw_response:
            data["raw_api_response"] = result.raw_response
        return json.dumps(data, indent=2, ensure_ascii=False)


class FormatterFactory:
    """Factory for creating formatters."""

    FORMATTERS = {
        "txt": PlainTextFormatter(),
        "md": MarkdownFormatter(),
        "srt": SRTFormatter(),
        "vtt": VTTFormatter(),
        "json": JSONFormatter(),
    }

    @classmethod
    def get_formatter(cls, format_name: str) -> OutputFormatter:
        """Get formatter by name."""
        formatter = cls.FORMATTERS.get(format_name.lower())
        if not formatter:
            raise ValueError(f"Unknown format: {format_name}")
        return formatter

    @classmethod
    def get_supported_formats(cls) -> List[str]:
        """Get list of supported formats."""
        return list(cls.FORMATTERS.keys())
