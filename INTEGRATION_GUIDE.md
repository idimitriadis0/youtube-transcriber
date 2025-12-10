# API Integration Guide

This document provides step-by-step instructions for integrating real transcription providers.

## Overview

The application uses a **provider abstraction layer** in `app/transcriber.py`. The system is designed to work with the mock backend out of the box, with clear integration points for real providers.

### Architecture

```python
BaseTranscriber (abstract interface)
  └─ MockTranscriber (works now)
  └─ DeepgramTranscriber (TODO)
  └─ WhisperTranscriber (TODO)
  └─ CustomTranscriber (your provider)
```

All providers must:
1. Inherit from `BaseTranscriber`
2. Implement `transcribe(source, options) -> TranscriptionResult`
3. Return segments with timing information

---

## Deepgram Integration

### Prerequisites

1. Create account at https://console.deepgram.com
2. Create API key in console
3. Choose model: `nova-2` (recommended) or `nova-3` (latest)

### Setup

**1. Configure environment**

`.env`:
```bash
TRANSCRIBER_PROVIDER=deepgram
DEEPGRAM_API_KEY=your-api-key-here
```

**2. Install dependencies (if using local files)**

```bash
pip install requests  # Already in requirements.txt
```

**3. Implement transcriber**

Replace the stub in `app/transcriber.py`:

```python
class DeepgramTranscriber(BaseTranscriber):
    """Deepgram API transcriber."""

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Deepgram API key required")
        self.api_key = api_key

    def transcribe(
        self, source: str | Path, options: TranscriptionOptions
    ) -> TranscriptionResult:
        """Transcribe using Deepgram API."""
        import requests
        from app.models import Segment

        # Map quality to model
        model_map = {
            "fast": "nova-2",
            "balanced": "nova-2",
            "best_quality": "nova-3",
        }
        model = model_map.get(options.quality.value, "nova-2")

        # Prepare request
        headers = {"Authorization": f"Token {self.api_key}"}
        params = {
            "model": model,
            "language": options.language if options.language != "auto" else None,
            "punctuate": options.smart_format,
            "diarize": options.diarization,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        try:
            if isinstance(source, Path):
                # Local file
                with open(source, "rb") as f:
                    response = requests.post(
                        APIConfig.DEEPGRAM_API_URL,
                        headers=headers,
                        params=params,
                        data=f,
                        timeout=300,
                    )
            else:
                # Remote URL
                params["url"] = source
                response = requests.post(
                    APIConfig.DEEPGRAM_API_URL,
                    headers=headers,
                    params=params,
                    timeout=300,
                )

            response.raise_for_status()
            result = response.json()

            # Parse response into TranscriptionResult
            if "error" in result:
                raise TranscriptionError(f"Deepgram error: {result['error']}")

            # Extract transcript
            transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
            
            # Extract segments with timing
            segments = []
            if "words" in result["results"]["channels"][0]["alternatives"][0]:
                words = result["results"]["channels"][0]["alternatives"][0]["words"]
                current_segment_words = []
                current_start = None

                for word in words:
                    if current_start is None:
                        current_start = word["start"]
                    current_segment_words.append(word["word"])

                    # Create segment every N words or at sentence end
                    if len(current_segment_words) >= 15 or word["word"].endswith("."):
                        segment_text = " ".join(current_segment_words)
                        segments.append(
                            Segment(
                                start_time=current_start,
                                end_time=word["end"],
                                text=segment_text,
                                confidence=word.get("confidence", 0.95),
                            )
                        )
                        current_segment_words = []
                        current_start = None

                # Final segment
                if current_segment_words:
                    segments.append(
                        Segment(
                            start_time=current_start,
                            end_time=words[-1]["end"],
                            text=" ".join(current_segment_words),
                        )
                    )
            else:
                # Fallback: create single segment
                segments = [
                    Segment(
                        start_time=0.0,
                        end_time=float(result["metadata"]["duration"]),
                        text=transcript,
                    )
                ]

            # Detect language
            detected_language = result["results"]["channels"][0]["detected_language"]
            
            return TranscriptionResult(
                text=transcript,
                language=detected_language or options.language,
                segments=segments,
                duration=float(result["metadata"]["duration"]),
                raw_response=result,
            )

        except requests.exceptions.RequestException as e:
            raise TranscriptionError(f"Deepgram API error: {e}")
```

### Testing

```bash
python main.py transcribe --file audio.mp3 --quality best_quality
```

---

## OpenAI Whisper Integration

### Prerequisites

1. Create account at https://platform.openai.com
2. Get API key from https://platform.openai.com/api-keys
3. Add billing method

### Setup

**1. Configure environment**

`.env`:
```bash
TRANSCRIBER_PROVIDER=whisper
OPENAI_API_KEY=sk-...
```

**2. Implement transcriber**

```python
class WhisperTranscriber(BaseTranscriber):
    """OpenAI Whisper API transcriber."""

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("OpenAI API key required")
        self.api_key = api_key

    def transcribe(
        self, source: str | Path, options: TranscriptionOptions
    ) -> TranscriptionResult:
        """Transcribe using OpenAI Whisper API."""
        import requests
        from app.models import Segment

        headers = {"Authorization": f"Bearer {self.api_key}"}

        data = {
            "model": "whisper-1",
            "response_format": "verbose_json",  # Get segments
        }

        # Add language if not auto
        if options.language != "auto":
            data["language"] = options.language

        try:
            if isinstance(source, Path):
                # Local file
                with open(source, "rb") as f:
                    files = {"file": (source.name, f, "audio/mpeg")}
                    response = requests.post(
                        APIConfig.OPENAI_API_URL,
                        headers=headers,
                        data=data,
                        files=files,
                        timeout=600,
                    )
            else:
                # Note: Whisper API doesn't support remote URLs directly
                # Would need to download first
                raise TranscriptionError(
                    "Whisper API requires local files. Download URL first."
                )

            response.raise_for_status()
            result = response.json()

            # Parse response
            transcript = result["text"]
            
            # Create segments from Whisper output
            segments = []
            if "segments" in result:
                for seg in result["segments"]:
                    segments.append(
                        Segment(
                            start_time=float(seg["start"]),
                            end_time=float(seg["end"]),
                            text=seg["text"].strip(),
                        )
                    )

            return TranscriptionResult(
                text=transcript,
                language=result.get("language", options.language),
                segments=segments,
                duration=float(result.get("duration", 0)),
                raw_response=result,
            )

        except requests.exceptions.RequestException as e:
            raise TranscriptionError(f"Whisper API error: {e}")
```

### Testing

```bash
python main.py transcribe --file audio.mp3 --language en
```

---

## AssemblyAI Integration (Example)

### Quick Implementation Template

```python
class AssemblyAITranscriber(BaseTranscriber):
    """AssemblyAI transcriber (example template)."""

    API_URL = "https://api.assemblyai.com/v2"

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("AssemblyAI API key required")
        self.api_key = api_key

    def transcribe(
        self, source: str | Path, options: TranscriptionOptions
    ) -> TranscriptionResult:
        """TODO: Implement AssemblyAI transcription.
        
        See: https://www.assemblyai.com/docs
        
        Steps:
        1. Upload file or provide URL
        2. Submit transcription request
        3. Poll for completion
        4. Parse results into segments
        """
        raise NotImplementedError()
```

---

## Custom Provider Integration

For your own API or a provider not listed:

### 1. Create New Class

```python
class MyCustomTranscriber(BaseTranscriber):
    """Your custom transcription provider."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def transcribe(
        self, source: str | Path, options: TranscriptionOptions
    ) -> TranscriptionResult:
        # Your implementation
        pass
```

### 2. Register in Factory

```python
class TranscriberFactory:
    @staticmethod
    def create(provider: Optional[str] = None) -> BaseTranscriber:
        provider = provider or APIConfig.PROVIDER
        
        # ... existing providers ...
        elif provider == "mycustom":
            return MyCustomTranscriber(APIConfig.CUSTOM_API_KEY)
        else:
            raise ValueError(f"Unknown provider: {provider}")
```

### 3. Configure Environment

```bash
TRANSCRIBER_PROVIDER=mycustom
CUSTOM_API_KEY=your-key
```

---

## Key Data Classes

### Input: TranscriptionOptions

```python
class TranscriptionOptions(BaseModel):
    source: str | Path          # File path or URL
    language: str = "auto"      # Language code
    quality: str = "balanced"   # fast | balanced | best_quality
    diarization: bool = False   # Speaker identification
    smart_format: bool = True   # Punctuation, etc.
    timestamps: str = "utterance"  # Granularity
    output_formats: List[str]   # Which formats to save
```

### Output: TranscriptionResult

```python
class TranscriptionResult(BaseModel):
    text: str                   # Full transcript
    language: str               # Detected language
    segments: List[Segment]     # Timestamped segments
    duration: float             # Total duration in seconds
    raw_response: Optional[Dict]  # Raw API response
```

### Segment Structure

```python
class Segment(BaseModel):
    start_time: float           # Seconds
    end_time: float             # Seconds
    text: str                   # Segment text
    speaker: Optional[str] = None  # If diarization
    confidence: Optional[float] = None  # 0.0-1.0
```

---

## Testing Your Implementation

### Unit Test Template

```python
from app.models import TranscriptionOptions, QualityPreset
from app.transcriber import MyCustomTranscriber

def test_my_transcriber():
    transcriber = MyCustomTranscriber(api_key="test-key")
    
    options = TranscriptionOptions(
        source="test.mp3",
        language="en",
        quality=QualityPreset.BALANCED,
    )
    
    result = transcriber.transcribe("test.mp3", options)
    
    assert result.text
    assert len(result.segments) > 0
    assert result.segments[0].start_time >= 0
    assert result.segments[0].end_time > result.segments[0].start_time
```

### CLI Testing

```bash
# Test with local file
python main.py transcribe --file test.mp3 --output-format txt json

# Test with URL
python main.py transcribe --url "https://example.com/audio.mp3" --language en

# Test batch
python main.py transcribe --file file1.mp3 --file file2.mp3 --out-dir ./out
```

### GUI Testing

```bash
# Launch GUI
python main.py

# Add URLs/files in GUI
# Configure options
# Click "Start"
# Check output directory
```

---

## Cost Estimation

### Deepgram
- **nova-2**: $0.0043 per minute
- **nova-3**: $0.0055 per minute
- Example: 1 hour = $0.26 (nova-2)

### OpenAI Whisper
- $0.02 per minute of audio
- Example: 1 hour = $1.20

### AssemblyAI
- $0.0117 per minute
- Example: 1 hour = $0.70

---

## Troubleshooting

### "API key invalid"
- Verify key format in `.env`
- Check if key has required scopes/permissions
- Regenerate key if needed

### "Timeout error"
- Increase timeout parameter
- Check internet connection
- Try smaller files first

### "Rate limit exceeded"
- Implement exponential backoff
- Add delay between requests
- Consider upgrading API plan

### "Segments not created"
- Check if API returns word-level timing
- Implement fallback to create single segment
- Adjust segment size threshold

---

## Performance Tips

1. **Batch smaller files**: <30 minutes each for faster processing
2. **Use balanced quality**: Good balance between speed and accuracy
3. **Disable features if not needed**: Diarization, formatting add time
4. **Cache results**: Store raw JSON response for later reprocessing
5. **Parallel processing**: Could extend with ThreadPoolExecutor (see Future Enhancements)

---

## References

- **Deepgram**: https://developers.deepgram.com/
- **OpenAI Whisper**: https://platform.openai.com/docs/guides/speech-to-text
- **AssemblyAI**: https://www.assemblyai.com/docs
- **Pydantic Models**: https://docs.pydantic.dev/v2/

---

Have questions? Check the TODO comments in `app/transcriber.py` for specific integration hints.
