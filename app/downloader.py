from __future__ import annotations

import re
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yt_dlp

from app.config import settings
from app.models import DownloadJob, DownloadRequest, JobState

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}

SUPPORTED_AUDIO_FORMATS = {"mp3", "m4a", "wav"}
SUPPORTED_AUDIO_QUALITIES = {"128", "192", "256", "320"}


class DownloadError(Exception):
    """Raised when a download request cannot be processed."""


def validate_youtube_url(url: str) -> str:
    normalized = url.strip()
    if not normalized:
        raise DownloadError("Please provide a YouTube video or playlist URL.")

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"}:
        raise DownloadError("The URL must start with http:// or https://.")

    hostname = (parsed.hostname or "").lower()
    if hostname not in YOUTUBE_HOSTS:
        raise DownloadError("Only YouTube video and playlist URLs are supported.")

    if hostname in {"youtu.be", "www.youtu.be"} and parsed.path.strip("/"):
        return normalized

    query = parse_qs(parsed.query)
    if parsed.path == "/watch" and query.get("v"):
        return normalized

    if parsed.path == "/playlist" and query.get("list"):
        return normalized

    if parsed.path.startswith("/shorts/") and parsed.path.split("/shorts/", 1)[1]:
        return normalized

    if parsed.path.startswith("/live/") and parsed.path.split("/live/", 1)[1]:
        return normalized

    if query.get("list"):
        return normalized

    raise DownloadError("Enter a valid YouTube video, shorts, live, or playlist URL.")


def validate_audio_options(audio_format: str, audio_quality: str) -> tuple[str, str]:
    fmt = audio_format.lower().strip()
    quality = audio_quality.strip()

    if fmt not in SUPPORTED_AUDIO_FORMATS:
        raise DownloadError(
            f"Unsupported audio format '{audio_format}'. Choose from: {', '.join(sorted(SUPPORTED_AUDIO_FORMATS))}."
        )

    if quality not in SUPPORTED_AUDIO_QUALITIES:
        raise DownloadError(
            f"Unsupported audio quality '{audio_quality}'. Choose from: {', '.join(sorted(SUPPORTED_AUDIO_QUALITIES))}."
        )

    return fmt, quality


def _sanitize_segment(value: str) -> str:
    cleaned = re.sub(r"[^\w.-]+", "_", value).strip("._")
    return cleaned or "download"


class DownloadManager:
    def __init__(self) -> None:
        settings.download_root.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, DownloadJob] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max(1, settings.max_workers))

    def list_jobs(self) -> list[dict[str, object]]:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda item: item.created_at, reverse=True)
            return [job.as_dict() for job in jobs]

    def get_job(self, job_id: str) -> DownloadJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def _cleanup_output_dir(self, output_dir: str) -> None:
        if output_dir and Path(output_dir).exists():
            shutil.rmtree(output_dir, ignore_errors=True)

    def delete_job(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            if job.status in {JobState.queued, JobState.downloading, JobState.processing}:
                job.cancel_requested = True
                job.status = JobState.cancelled
                job.message = "Cancellation requested"
                job.touch()
                return True
            self._jobs.pop(job_id, None)
            output_dir = job.output_dir
        self._cleanup_output_dir(output_dir)
        return True

    def clear_completed_jobs(self) -> int:
        """Removes all jobs that are completed, failed, or cancelled."""
        cleared_count = 0
        with self._lock:
            job_ids = list(self._jobs.keys())

        for job_id in job_ids:
            job = self.get_job(job_id)
            if job and job.status in {JobState.completed, JobState.failed, JobState.cancelled}:
                if self.delete_job(job_id):
                    cleared_count += 1
        return cleared_count

    def _remove_job(self, job_id: str) -> DownloadJob | None:
        with self._lock:
            return self._jobs.pop(job_id, None)

    def _is_cancel_requested(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            return bool(job and job.cancel_requested)

    def _finalize_cancelled_job(self, job_id: str) -> None:
        job = self._remove_job(job_id)
        if job is not None:
            self._cleanup_output_dir(job.output_dir)

    def _handle_cancelled_job(self, job_id: str) -> bool:
        if not self._is_cancel_requested(job_id):
            return False
        self._update_job(
            job_id,
            status=JobState.cancelled,
            progress=0.0,
            message="Download cancelled",
            error=None,
        )
        self._finalize_cancelled_job(job_id)
        return True

    @staticmethod
    def _find_ffmpeg() -> str | None:
        """Return the path to ffmpeg, checking PATH then the active venv bin."""
        found = shutil.which("ffmpeg")
        if found:
            return found
        # Fallback: look inside the active Python venv (e.g. venv/bin/ffmpeg)
        venv_bin = Path(sys.executable).parent
        candidates = [venv_bin / "ffmpeg"]
        if sys.platform.startswith("win"):
            candidates.insert(0, venv_bin / "ffmpeg.exe")
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return None

    def submit(self, request: DownloadRequest) -> DownloadJob:
        ffmpeg_path = self._find_ffmpeg()
        if ffmpeg_path is None:
            raise DownloadError("ffmpeg is not installed or not available on PATH.")

        normalized_url = validate_youtube_url(request.url)
        audio_format, audio_quality = validate_audio_options(
            request.audio_format, request.audio_quality
        )

        job = DownloadJob(
            url=normalized_url,
            audio_format=audio_format,
            audio_quality=audio_quality,
        )
        with self._lock:
            self._jobs[job.job_id] = job

        self._executor.submit(self._run_download, job.job_id)
        return job

    def _update_job(self, job_id: str, **changes: object) -> DownloadJob | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            for key, value in changes.items():
                setattr(job, key, value)
            job.touch()
            return job

    def _build_output_template(self, job: DownloadJob) -> dict[str, str]:
        base_dir = settings.download_root / _sanitize_segment(job.job_id)
        base_dir.mkdir(parents=True, exist_ok=True)
        self._update_job(job.job_id, output_dir=str(base_dir))
        return {
            "default": str(base_dir / "%(title)s.%(ext)s"),
            "pl_video": str(base_dir / "%(playlist_title)s" / "%(playlist_index|00)s - %(title)s.%(ext)s"),
        }

    def _run_download(self, job_id: str) -> None:
        job = self.get_job(job_id)
        if job is None:
            return

        outtmpl = self._build_output_template(job)
        files: list[str] = []

        def progress_hook(data: dict[str, object]) -> None:
            if self._is_cancel_requested(job_id):
                raise DownloadError("Download cancelled by user.")
            status = data.get("status")
            if status == "downloading":
                downloaded = float(data.get("downloaded_bytes") or 0)
                total = float(data.get("total_bytes") or data.get("total_bytes_estimate") or 0)
                progress = (downloaded / total * 100.0) if total else 0.0
                self._update_job(
                    job_id,
                    status=JobState.downloading,
                    progress=progress,
                    message="Downloading audio stream",
                )
            elif status == "finished":
                filename = data.get("filename")
                if isinstance(filename, str):
                    files.append(str(Path(filename).with_suffix(f".{job.audio_format}")))
                self._update_job(
                    job_id,
                    status=JobState.processing,
                    progress=98.0,
                    message="Converting audio with ffmpeg",
                    items_downloaded=len(files),
                )

        try:
            # Resolve ffmpeg here (inside the thread) so the variable is always
            # in scope and any lookup failure is caught by the except block below.
            ffmpeg_path = self._find_ffmpeg()
            if ffmpeg_path is None:
                raise DownloadError("ffmpeg binary not found. Check your installation.")

            options = {
                # The android client exposes full audio-only streams (140/251)
                # without requiring a GVS PO Token, unlike ios/mweb/web clients.
                # Format 18 (360p combined mp4) is used as fallback.
                "format": "bestaudio/best",
                "outtmpl": outtmpl,
                "noplaylist": False,
                "ignoreerrors": True,
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False,
                "extractor_args": {
                    "youtube": {
                        "player_client": ["android"],
                    }
                },
                # Explicit ffmpeg path so it works whether or not the venv is
                # activated in the calling shell.
                "ffmpeg_location": ffmpeg_path,
                "progress_hooks": [progress_hook],
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": job.audio_format,
                        "preferredquality": job.audio_quality,
                    }
                ],
            }

            self._update_job(job_id, status=JobState.downloading, message="Fetching metadata")
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(job.url, download=False)
                if self._handle_cancelled_job(job_id):
                    return
                total_items = None
                if isinstance(info, dict):
                    entries = info.get("entries")
                    title = info.get("title")
                    webpage_url = info.get("webpage_url")
                    source_type = info.get("_type") or info.get("extractor_key")
                    is_playlist = bool(entries) or info.get("_type") == "playlist"
                    if isinstance(entries, list):
                        total_items = len([entry for entry in entries if entry])
                    elif entries is not None:
                        total_items = None
                    self._update_job(
                        job_id,
                        title=title if isinstance(title, str) else webpage_url,
                        source_type=str(source_type) if source_type else None,
                        is_playlist=is_playlist,
                        total_items=total_items,
                        message="Starting download",
                    )
                ydl.download([job.url])

            unique_files = sorted({path for path in files if Path(path).exists()})
            if self._handle_cancelled_job(job_id):
                return
            if not unique_files:
                self._update_job(
                    job_id,
                    status=JobState.failed,
                    progress=0.0,
                    message="No audio files were downloaded",
                    error="No downloadable items were produced from the provided URL.",
                )
                return
            skipped_items = 0
            warning = None
            message = "Download completed"
            latest_job = self.get_job(job_id)
            if latest_job and latest_job.total_items:
                skipped_items = max(0, latest_job.total_items - len(unique_files))
                if skipped_items:
                    warning = (
                        f"Skipped {skipped_items} unavailable item"
                        f"{'s' if skipped_items != 1 else ''} while processing the playlist."
                    )
                    message = "Download completed with skipped items"
            self._update_job(
                job_id,
                status=JobState.completed,
                progress=100.0,
                message=message,
                files=unique_files,
                items_downloaded=len(unique_files),
                skipped_items=skipped_items,
                warning=warning,
            )
        except Exception as exc:
            if self._handle_cancelled_job(job_id):
                return
            self._update_job(
                job_id,
                status=JobState.failed,
                error=str(exc),
                message="Download failed",
                warning=None,
            )


download_manager = DownloadManager()
