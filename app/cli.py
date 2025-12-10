"""Command-line interface for the transcription utility."""

import click
from pathlib import Path
from typing import List
from app.transcriber import TranscriberFactory, TranscriptionError
from app.models import TranscriptionOptions
from app.io_utils import FileUtils, InputValidator
from app.formats import FormatterFactory
from app.config import AppConfig


@click.group()
def cli():
    """YouTube & Audio Transcription Utility."""
    AppConfig.ensure_output_dir()


@cli.command()
@click.option(
    "--url",
    multiple=True,
    help="URL to transcribe (can be used multiple times)",
)
@click.option(
    "--file",
    "files",
    multiple=True,
    type=click.Path(exists=True),
    help="Local file to transcribe (can be used multiple times)",
)
@click.option(
    "--language",
    default="en",
    help="Language code (en, fr, de, etc.)",
)
@click.option(
    "--quality",
    type=click.Choice(["fast", "balanced", "best_quality"]),
    default="balanced",
    help="Quality preset",
)
@click.option(
    "--output-format",
    "output_formats",
    multiple=True,
    type=click.Choice(["txt", "md", "srt", "vtt", "json"]),
    default=["txt", "srt"],
    help="Output format (can be used multiple times)",
)
@click.option(
    "--out-dir",
    type=click.Path(),
    default=None,
    help="Output directory (default: ./transcriptions)",
)
@click.option(
    "--diarization",
    is_flag=True,
    help="Enable speaker diarization",
)
@click.option(
    "--timestamps",
    type=click.Choice(["none", "utterance", "word"]),
    default="utterance",
    help="Timestamp granularity",
)
def transcribe(
    url: tuple,
    files: tuple,
    language: str,
    quality: str,
    output_format: tuple,
    out_dir: str,
    diarization: bool,
    timestamps: str,
):
    """Transcribe audio/video sources.

    Examples:

    \b
    # Transcribe a YouTube video
    python main.py transcribe --url "https://youtu.be/..." --output-format txt srt

    \b
    # Transcribe a local file
    python main.py transcribe --file ./audio.mp3 --language en --quality best_quality

    \b
    # Batch processing
    python main.py transcribe --file file1.mp3 --file file2.wav --out-dir ./transcripts
    """

    if not url and not files:
        click.echo(click.style("Error: Provide at least one --url or --file", fg="red"))
        return

    output_dir = Path(out_dir) if out_dir else AppConfig.OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Validate inputs
    valid_urls = []
    valid_files = []

    if url:
        valid_urls, url_errors = InputValidator.validate_urls("\n".join(url))
        for error in url_errors:
            click.echo(click.style(f"Warning: {error}", fg="yellow"))

    if files:
        paths = [Path(f) for f in files]
        valid_files, file_errors = InputValidator.validate_files(paths)
        for error in file_errors:
            click.echo(click.style(f"Warning: {error}", fg="yellow"))

    if not valid_urls and not valid_files:
        click.echo(click.style("Error: No valid inputs provided", fg="red"))
        return

    # Create options
    options = TranscriptionOptions(
        source="temp",
        language=language,
        quality=quality,
        diarization=diarization,
        smart_format=True,
        timestamps=timestamps,
        output_formats=list(output_format),
    )

    # Create transcriber
    transcriber = TranscriberFactory.create()

    # Process all sources
    all_sources = [("url", u) for u in valid_urls] + [("file", f) for f in valid_files]
    completed = 0
    failed = 0

    with click.progressbar(
        all_sources,
        label="Transcribing",
        show_pos=True,
    ) as bar:
        for source_type, source in bar:
            try:
                click.echo(
                    click.style(
                        f"\nProcessing {source_type}: {source}",
                        fg="cyan",
                    )
                )

                # Update options with current source
                options.source = source

                # Transcribe
                result = transcriber.transcribe(source, options)

                # Save outputs
                base_name = FileUtils.extract_base_name(source)
                saved_files = []

                for fmt in options.output_formats:
                    formatter = FormatterFactory.get_formatter(fmt)
                    output = formatter.format(result)
                    output_path = FileUtils.generate_output_path(
                        base_name,
                        result.language,
                        fmt,
                        output_dir,
                    )
                    output_path.write_text(output, encoding="utf-8")
                    saved_files.append(output_path)

                click.echo(
                    click.style(
                        f"  ✓ Saved to:\n    "
                        + "\n    ".join(str(p.absolute()) for p in saved_files),
                        fg="green",
                    )
                )
                completed += 1

            except TranscriptionError as e:
                click.echo(
                    click.style(
                        f"  ✗ Transcription failed: {e}",
                        fg="red",
                    )
                )
                failed += 1
            except Exception as e:
                click.echo(
                    click.style(
                        f"  ✗ Error: {e}",
                        fg="red",
                    )
                )
                failed += 1

    # Summary
    click.echo()
    click.echo(click.style("=", fg="blue") * 40)
    click.echo(
        click.style(
            f"Summary: {completed} completed, {failed} failed",
            fg="green" if failed == 0 else "yellow",
        )
    )
    click.echo(click.style("=", fg="blue") * 40)


@cli.command()
def config():
    """Show configuration."""
    click.echo("Current Configuration:")
    click.echo(f"  Output Directory: {AppConfig.OUTPUT_DIR}")
    click.echo(f"  Supported Languages: {', '.join(AppConfig.LANGUAGES)}")
    click.echo(f"  Output Formats: {', '.join(AppConfig.OUTPUT_FORMATS)}")
    click.echo(f"  Quality Presets: {', '.join(AppConfig.QUALITY_PRESETS.keys())}")


if __name__ == "__main__":
    cli()
