"""GUI for the transcription utility using PySimpleGUI."""

import PySimpleGUI as sg
from pathlib import Path
from typing import List, Optional, Dict, Callable
import threading
from datetime import datetime
from app.models import TranscriptionJob, TranscriptionOptions, JobStatus, QualityPreset
from app.io_utils import FileUtils, InputValidator
from app.transcriber import TranscriberFactory, TranscriptionError
from app.formats import FormatterFactory
from app.config import AppConfig

# Set PySimpleGUI theme
sg.theme("Dark Blue 3")


class TranscriptionGUI:
    """Main GUI application for transcription."""

    def __init__(self):
        """Initialize the GUI."""
        self.jobs: List[TranscriptionJob] = []
        self.current_job_index: Optional[int] = None
        self.running = False
        self.cancel_requested = False
        self.output_dir = AppConfig.OUTPUT_DIR
        self.status_log: List[str] = []

        # Create transcriber
        self.transcriber = TranscriberFactory.create()
        AppConfig.ensure_output_dir()

    def run(self) -> None:
        """Run the GUI application."""
        window = self._create_window()

        while True:
            event, values = window.read(timeout=100)

            if event == sg.WINDOW_CLOSED or event == "Exit":
                break

            # Route events
            if event == "-ADD-URLS-":
                self._handle_add_urls(window, values)
            elif event == "-ADD-FILES-":
                self._handle_add_files(window, values)
            elif event == "-SELECT-OUTPUT-DIR-":
                self._handle_select_output_dir(window)
            elif event == "-START-":
                self._handle_start(window, values)
            elif event == "-CANCEL-":
                self._handle_cancel()
            elif event == "-CLEAR-FINISHED-":
                self._handle_clear_finished(window)

            # Update displays
            self._update_job_table(window)
            self._update_status_display(window)

        window.close()

    def _create_window(self) -> sg.Window:
        """Create the main GUI window."""
        layout = [
            [sg.Text("YouTube & Audio Transcription Utility", font=("Arial", 16, "bold"))],
            [sg.Text("Add sources to transcribe")],
            [
                sg.Multiline(
                    size=(60, 5),
                    key="-URLS-INPUT-",
                    tooltip="Paste URLs here (one per line)",
                ),
                sg.Column(
                    [
                        [sg.Button("Add URLs", key="-ADD-URLS-")],
                        [sg.Button("Add Files", key="-ADD-FILES-")],
                    ]
                ),
            ],
            [sg.Text("")],
            [sg.Text("Transcription Options")],
            [
                sg.Column(
                    [
                        [
                            sg.Text("Language:"),
                            sg.Combo(
                                AppConfig.LANGUAGES,
                                default_value="en",
                                key="-LANGUAGE-",
                                readonly=True,
                            ),
                        ],
                        [
                            sg.Text("Quality:"),
                            sg.Combo(
                                ["fast", "balanced", "best_quality"],
                                default_value="balanced",
                                key="-QUALITY-",
                                readonly=True,
                            ),
                        ],
                        [
                            sg.Text("Timestamps:"),
                            sg.Combo(
                                ["none", "utterance", "word"],
                                default_value="utterance",
                                key="-TIMESTAMPS-",
                                readonly=True,
                            ),
                        ],
                    ],
                    vertical_alignment="top",
                ),
                sg.Column(
                    [
                        [sg.Checkbox("Smart Formatting", default=True, key="-SMART-FORMAT-")],
                        [sg.Checkbox("Speaker Diarization", default=False, key="-DIARIZATION-")],
                    ],
                    vertical_alignment="top",
                ),
            ],
            [
                sg.Text("Output Formats:"),
                sg.Checkbox("Text", default=True, key="-FORMAT-TXT-"),
                sg.Checkbox("Markdown", default=False, key="-FORMAT-MD-"),
                sg.Checkbox("SRT", default=True, key="-FORMAT-SRT-"),
                sg.Checkbox("VTT", default=False, key="-FORMAT-VTT-"),
                sg.Checkbox("JSON", default=False, key="-FORMAT-JSON-"),
            ],
            [
                sg.Text("Output Directory:"),
                sg.InputText(str(self.output_dir), key="-OUTPUT-DIR-", disabled=True),
                sg.Button("Browse", key="-SELECT-OUTPUT-DIR-"),
            ],
            [sg.Text("")],
            [sg.Text("Transcription Jobs")],
            [
                sg.Table(
                    values=[],
                    headings=["Source", "Status", "Language", "Quality"],
                    max_col_widths=[30, 12, 8, 12],
                    size=(60, 8),
                    key="-JOBS-TABLE-",
                    row_height=20,
                    auto_size_columns=False,
                )
            ],
            [
                sg.Multiline(
                    size=(60, 4),
                    key="-STATUS-",
                    disabled=True,
                    background_color="black",
                    text_color="white",
                )
            ],
            [
                sg.Button("Start", key="-START-", size=(12, 1)),
                sg.Button("Cancel", key="-CANCEL-", size=(12, 1)),
                sg.Button("Clear Finished", key="-CLEAR-FINISHED-", size=(12, 1)),
                sg.Button("Exit", size=(12, 1)),
            ],
        ]

        return sg.Window(
            "Transcription Utility",
            layout,
            size=(700, 900),
            finalize=True,
        )

    def _handle_add_urls(self, window: sg.Window, values: dict) -> None:
        """Handle adding URLs."""
        urls_text = values["-URLS-INPUT-"].strip()
        if not urls_text:
            sg.popup_error("Please paste URLs (one per line)")
            return

        valid_urls, errors = InputValidator.validate_urls(urls_text)
        if errors:
            sg.popup_error("\n".join(errors))

        for url in valid_urls:
            base_name = FileUtils.extract_base_name(url)
            options = self._get_options_from_window(window)
            options.source = url
            job = TranscriptionJob(
                id=f"url-{len(self.jobs)}",
                source=url,
                options=options,
            )
            self.jobs.append(job)
            self._log_status(f"Added: {base_name}")

        window["-URLS-INPUT-"].update("")

    def _handle_add_files(self, window: sg.Window, values: dict) -> None:
        """Handle adding files via file picker."""
        files = sg.popup_get_file(
            "Select audio/video files",
            multiple_files=True,
            file_types=(
                ("Audio Files", "*.mp3 *.wav *.m4a *.flac *.ogg"),
                ("Video Files", "*.mp4 *.webm *.mkv *.avi *.mov"),
                ("All Files", "*.*"),
            ),
        )

        if not files:
            return

        file_list = files if isinstance(files, (list, tuple)) else [files]
        paths = [Path(f) for f in file_list]
        valid_files, errors = InputValidator.validate_files(paths)

        if errors:
            sg.popup_error("\n".join(errors))

        for file_path in valid_files:
            base_name = FileUtils.extract_base_name(file_path)
            options = self._get_options_from_window(window)
            options.source = file_path
            job = TranscriptionJob(
                id=f"file-{len(self.jobs)}",
                source=file_path,
                options=options,
            )
            self.jobs.append(job)
            self._log_status(f"Added: {file_path.name}")

    def _handle_select_output_dir(self, window: sg.Window) -> None:
        """Handle output directory selection."""
        folder = sg.popup_get_folder("Select output directory")
        if folder:
            self.output_dir = Path(folder)
            window["-OUTPUT-DIR-"].update(str(self.output_dir))
            self._log_status(f"Output directory: {self.output_dir}")

    def _handle_start(self, window: sg.Window, values: dict) -> None:
        """Handle start transcription."""
        if not self.jobs:
            sg.popup_error("Add some jobs first!")
            return

        self.running = True
        self.cancel_requested = False

        # Run transcription in background thread
        thread = threading.Thread(target=self._run_transcriptions, args=(window,))
        thread.daemon = True
        thread.start()

    def _run_transcriptions(self, window: sg.Window) -> None:
        """Run all pending transcriptions."""
        try:
            for idx, job in enumerate(self.jobs):
                if job.status != JobStatus.PENDING:
                    continue

                if self.cancel_requested:
                    break

                self.current_job_index = idx
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now()
                self._log_status(f"Processing: {job.source_name}")

                try:
                    # Perform transcription
                    result = self.transcriber.transcribe(job.source, job.options)
                    job.result = result

                    # Save outputs
                    base_name = FileUtils.extract_base_name(job.source)
                    for format_name in job.options.output_formats:
                        try:
                            formatter = FormatterFactory.get_formatter(format_name)
                            output = formatter.format(result)
                            output_path = FileUtils.generate_output_path(
                                base_name,
                                result.language,
                                format_name,
                                self.output_dir,
                            )
                            output_path.write_text(output, encoding="utf-8")
                            job.output_paths[format_name] = output_path
                        except Exception as e:
                            self._log_status(f"Error saving {format_name}: {e}")

                    job.status = JobStatus.COMPLETED
                    job.completed_at = datetime.now()
                    self._log_status(f"[DONE] {job.source_name}")

                except TranscriptionError as e:
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    job.completed_at = datetime.now()
                    self._log_status(f"[ERROR] {job.source_name}: {e}")
                except Exception as e:
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    job.completed_at = datetime.now()
                    self._log_status(f"[ERROR] {job.source_name}: {e}")

        finally:
            self.running = False
            self.current_job_index = None

    def _handle_cancel(self) -> None:
        """Handle cancel request."""
        self.cancel_requested = True
        self._log_status("Cancel requested")

    def _handle_clear_finished(self, window: sg.Window) -> None:
        """Remove finished jobs from the list."""
        self.jobs = [
            job
            for job in self.jobs
            if job.status not in (JobStatus.COMPLETED, JobStatus.FAILED)
        ]
        self._log_status("Cleared finished jobs")

    def _get_options_from_window(self, window: sg.Window) -> TranscriptionOptions:
        """Extract options from window values."""
        window.refresh()

        # Collect selected formats
        formats = []
        if window["-FORMAT-TXT-"].get():
            formats.append("txt")
        if window["-FORMAT-MD-"].get():
            formats.append("md")
        if window["-FORMAT-SRT-"].get():
            formats.append("srt")
        if window["-FORMAT-VTT-"].get():
            formats.append("vtt")
        if window["-FORMAT-JSON-"].get():
            formats.append("json")

        if not formats:
            formats = ["txt"]

        return TranscriptionOptions(
            source="temp",
            language=window["-LANGUAGE-"].get(),
            quality=window["-QUALITY-"].get(),
            diarization=window["-DIARIZATION-"].get(),
            smart_format=window["-SMART-FORMAT-"].get(),
            timestamps=window["-TIMESTAMPS-"].get(),
            output_formats=formats,
        )

    def _update_job_table(self, window: sg.Window) -> None:
        """Update the job list table."""
        rows = []
        for job in self.jobs:
            rows.append(
                [
                    job.source_name,
                    job.status.value,
                    job.options.language,
                    job.options.quality.value,
                ]
            )
        window["-JOBS-TABLE-"].update(values=rows)

    def _update_status_display(self, window: sg.Window) -> None:
        """Update status display."""
        pending = sum(1 for j in self.jobs if j.status == JobStatus.PENDING)
        running = sum(1 for j in self.jobs if j.status == JobStatus.RUNNING)
        completed = sum(1 for j in self.jobs if j.status == JobStatus.COMPLETED)
        failed = sum(1 for j in self.jobs if j.status == JobStatus.FAILED)

        summary = f"Jobs: {len(self.jobs)} | Pending: {pending} | Running: {running} | Done: {completed} | Failed: {failed}\n"
        summary += "\n".join(self.status_log[-8:])

        window["-STATUS-"].update(summary, append=False)

    def _log_status(self, message: str) -> None:
        """Log status message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_log.append(f"[{timestamp}] {message}")
        self.status_log = self.status_log[-20:]


def run_gui() -> None:
    """Entry point for GUI."""
    app = TranscriptionGUI()
    app.run()
