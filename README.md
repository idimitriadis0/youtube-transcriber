# YouTube & Audio Transcription Utility

A production-quality Python desktop application and CLI tool for high-quality AI transcription of YouTube videos and local audio/video files. Features batch processing, multiple output formats (TXT, Markdown, SRT, VTT, JSON), and a clean abstraction layer for plugging in your preferred transcription API.

## Features

✨ **Multi-source support**: YouTube URLs, remote audio/video streams, and local files  
🎯 **Batch processing**: Queue multiple jobs and process sequentially  
📝 **Multiple output formats**: Plain text, Markdown, SRT, VTT, JSON  
⚙️ **Flexible options**: Language, quality presets, speaker diarization, timestamps  
🖥️ **Dual interface**: PySimpleGUI desktop app and Click-based CLI  
🔧 **Clean API abstraction**: Drop in your favorite transcription provider (Deepgram, Whisper, etc.)  
🧪 **Mock backend**: Fully functional with dummy transcriptions for testing  

## Installation

```bash
git clone https://github.com/idimitriadis0/youtube-transcriber.git
cd youtube-transcriber
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Quick Start

### GUI Mode (Desktop Application)

```bash
python main.py
```

### CLI Mode (Command Line)

```bash
# Transcribe YouTube video
python main.py transcribe --url "https://youtu.be/dQw4w9WgXcQ" --output-format txt srt

# Transcribe local file
python main.py transcribe --file audio.mp3 --language en --quality best_quality

# Batch processing
python main.py transcribe --file file1.mp3 --file file2.wav --out-dir ./transcripts

# Show config
python main.py config
```

## Options Reference

| Option | CLI Flag | Values | Default |
|--------|----------|--------|----------|
| Language | `--language` | auto, en, fr, de, es, hi, ja, zh, ru, ar, pt, it | en |
| Quality | `--quality` | fast, balanced, best_quality | balanced |
| Output Formats | `--output-format` | txt, md, srt, vtt, json | txt, srt |
| Diarization | `--diarization` | flag | false |
| Timestamps | `--timestamps` | none, utterance, word | utterance |

## Output Formats

### Plain Text (`.txt`)
Simple transcript without timestamps.

### Markdown (`.md`)
Metadata header + timestamps
```markdown
# Transcript
**Language:** en | **Duration:** 120.5s
**[00:00:05,000 - 00:00:12,500]** Transcript text...
```

### SRT Subtitle (`.srt`)
Standard SRT with `hh:mm:ss,ms` format
```
1
00:00:05,000 --> 00:00:12,500
Transcript text
```

### WebVTT (`.vtt`)
Web Video Text Tracks with `hh:mm:ss.mmm` format

### JSON (`.json`)
Full structured data with segments and metadata

## Configuration

Create `.env` file:

```bash
TRANSCRIBER_OUTPUT_DIR=./my-transcriptions
TRANSCRIBER_PROVIDER=mock  # mock | deepgram | whisper | custom
DEEPGRAM_API_KEY=your-api-key
OPENAI_API_KEY=your-api-key
```

## API Integration

### Current: Mock Backend (Works Out of Box)

No API keys needed. Full workflow testing with realistic dummy transcriptions.

### Add Deepgram

1. Get API key from https://console.deepgram.com
2. Set `DEEPGRAM_API_KEY` in `.env`
3. Set `TRANSCRIBER_PROVIDER=deepgram`
4. Implement `DeepgramTranscriber.transcribe()` in `app/transcriber.py`

### Add Whisper

1. Get API key from https://platform.openai.com/api-keys
2. Set `OPENAI_API_KEY` in `.env`
3. Set `TRANSCRIBER_PROVIDER=whisper`
4. Implement `WhisperTranscriber.transcribe()` in `app/transcriber.py`

### Custom Provider

1. Create class inheriting from `BaseTranscriber`
2. Implement `transcribe()` method
3. Register in `TranscriberFactory.create()`

All TODO hooks are clearly marked in `app/transcriber.py`

## Project Structure

```
app/
  __init__.py       # Package init
  config.py         # Configuration & API setup
  models.py         # Data classes (Job, Options, Result)
  transcriber.py    # API abstraction with TODO hooks
  io_utils.py       # File handling & safe naming
  formats.py        # Output formatters (5 formats)
  gui.py            # PySimpleGUI desktop interface
  cli.py            # Click-based CLI
main.py             # Entry point (GUI or CLI)
requirements.txt
```

## Architecture

**Clean Separation of Concerns:**

```
GUI/CLI (PySimpleGUI or Click)
  ↓
Job Queue & Processor
  ↓
BaseTranscriber (abstraction layer)
  ↓
API Provider (Deepgram, Whisper, Mock, Custom)
  ↓
Formatters → File I/O
```

**Key Principles:**
- Type hints throughout (Python 3.11+)
- Modular, testable components
- No external dependencies in models/core logic
- Mock-first development
- Easy API provider swapping

## Features in Detail

### GUI (PySimpleGUI)
- Add URLs or files via file picker
- Real-time job queue with status display
- Configurable options per job
- Live status log
- Cancel current job safely
- Clear finished jobs

### CLI (Click)
- Batch processing from command line
- Progress bar with completion status
- Colored output for errors/success
- Configuration display
- Flexible argument combinations

### Transcriber Abstraction
- Clean `BaseTranscriber` interface
- `MockTranscriber` for development
- `DeepgramTranscriber` stub (TODO)
- `WhisperTranscriber` stub (TODO)
- Easy factory pattern extension

### Output Formatting
- 5 different formats supported
- Proper timestamp formatting (SRT, VTT)
- Smart text wrapping (SRT/VTT)
- JSON with full metadata
- Markdown with readable structure

### File I/O
- Safe filename sanitization
- URL-to-filename extraction
- YouTube video ID detection
- File format validation
- Output path generation with language suffix

## Data Models

### TranscriptionOptions
```python
class TranscriptionOptions(BaseModel):
    source: str | Path
    language: str = "en"
    quality: QualityPreset = "balanced"
    diarization: bool = False
    smart_format: bool = True
    timestamps: TimestampLevel = "utterance"
    output_formats: List[str] = ["txt", "srt"]
```

### Segment
```python
class Segment(BaseModel):
    start_time: float
    end_time: float
    text: str
    speaker: Optional[str]
    confidence: Optional[float]
```

### TranscriptionResult
```python
class TranscriptionResult(BaseModel):
    text: str
    language: str
    segments: List[Segment]
    duration: float
    raw_response: Optional[Dict]
```

## Development

### Test with Mock Backend
```bash
python main.py transcribe --file test.mp3 --output-format txt srt md vtt json
```

Generates dummy transcriptions in all formats without API keys.

### Adding Custom Formatter

1. Create class in `app/formats.py` inheriting `OutputFormatter`
2. Implement `format()` method
3. Register in `FormatterFactory.FORMATTERS`

### Adding New Provider

1. Create class inheriting `BaseTranscriber` in `app/transcriber.py`
2. Implement `transcribe()` method
3. Register in `TranscriberFactory.create()`
4. Check TODO comments for integration points

## Troubleshooting

### "PySimpleGUI not installed"
```bash
pip install PySimpleGUI
```

### "API key not found"
Ensure `.env` in project root with correct variable names

### "Unsupported format"
Check `FileUtils.SUPPORTED_*_FORMATS` constants

### "Permission denied writing output"
```bash
chmod 755 ./transcriptions
```

## Performance

- Mock backend: ~0.5s per job
- Real providers depend on file size and quality preset
- Sequential processing (safe, no race conditions)
- Can be extended to parallel with ThreadPoolExecutor

## Known Limitations

- Sequential processing only (no concurrent jobs)
- No resume for failed transcriptions
- GUI requires PySimpleGUI (CLI works without)
- Mock transcriber uses generic dummy text

## Future Enhancements

- [ ] Concurrent batch processing
- [ ] Resume failed jobs
- [ ] Local Whisper (openai-whisper) support
- [ ] Web UI alternative
- [ ] Database history
- [ ] Translation integration
- [ ] Subtitle editing UI
- [ ] More provider integrations

## License

MIT - Free to use, modify, and distribute

## Support

For integration help:
1. Check `app/transcriber.py` for TODO hooks
2. Review `app/config.py` for configuration options
3. See RFC in models and data classes for expected formats

---

**Production-ready | Type-safe (Python 3.11+) | Extensible Architecture**
