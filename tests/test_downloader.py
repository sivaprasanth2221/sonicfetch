import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.downloader import DownloadError, DownloadManager, validate_audio_options, validate_youtube_url
from app.models import DownloadJob, DownloadRequest, JobState
from app.server import app, download_manager


class ValidateYouTubeUrlTests(unittest.TestCase):
    def test_accepts_watch_url(self) -> None:
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertEqual(validate_youtube_url(url), url)

    def test_accepts_playlist_url(self) -> None:
        url = "https://www.youtube.com/playlist?list=PL12345"
        self.assertEqual(validate_youtube_url(url), url)

    def test_accepts_short_url(self) -> None:
        url = "https://youtu.be/dQw4w9WgXcQ"
        self.assertEqual(validate_youtube_url(url), url)

    def test_rejects_non_youtube_url(self) -> None:
        with self.assertRaises(DownloadError):
            validate_youtube_url("https://example.com/watch?v=dQw4w9WgXcQ")


class ValidateAudioOptionsTests(unittest.TestCase):
    def test_accepts_supported_values(self) -> None:
        self.assertEqual(validate_audio_options("mp3", "192"), ("mp3", "192"))

    def test_rejects_unsupported_format(self) -> None:
        with self.assertRaises(DownloadError):
            validate_audio_options("flac", "192")

    def test_rejects_unsupported_quality(self) -> None:
        with self.assertRaises(DownloadError):
            validate_audio_options("mp3", "999")


class DownloadManagerTests(unittest.TestCase):
    def test_find_ffmpeg_checks_windows_executable_name(self) -> None:
        manager = DownloadManager()

        def fake_exists(path_obj: Path) -> bool:
            return str(path_obj).endswith("ffmpeg.exe")

        with patch("app.downloader.shutil.which", return_value=None), patch(
            "app.downloader.sys.platform", "win32"
        ), patch("app.downloader.sys.executable", r"C:\project\.venv\Scripts\python.exe"), patch(
            "pathlib.Path.exists", fake_exists
        ):
            resolved = manager._find_ffmpeg()

        self.assertIsNotNone(resolved)
        self.assertTrue(str(resolved).endswith("ffmpeg.exe"))

    def test_delete_in_flight_job_marks_cancelled_without_removing_record(self) -> None:
        manager = DownloadManager()
        job = DownloadJob(url="https://youtu.be/example", audio_format="mp3", audio_quality="192")
        job.status = JobState.downloading
        with manager._lock:
            manager._jobs[job.job_id] = job

        deleted = manager.delete_job(job.job_id)

        self.assertTrue(deleted)
        current = manager.get_job(job.job_id)
        self.assertIsNotNone(current)
        self.assertEqual(current.status, JobState.cancelled)
        self.assertTrue(current.cancel_requested)

    def test_delete_completed_job_removes_output_dir_and_job(self) -> None:
        manager = DownloadManager()
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "job-dir"
            output_dir.mkdir()
            (output_dir / "track.mp3").write_text("audio", encoding="utf-8")
            job = DownloadJob(url="https://youtu.be/example", audio_format="mp3", audio_quality="192")
            job.status = JobState.completed
            job.output_dir = str(output_dir)
            with manager._lock:
                manager._jobs[job.job_id] = job

            deleted = manager.delete_job(job.job_id)

            self.assertTrue(deleted)
            self.assertIsNone(manager.get_job(job.job_id))
            self.assertFalse(output_dir.exists())

    def test_submit_rejects_missing_ffmpeg(self) -> None:
        manager = DownloadManager()
        with patch.object(manager, "_find_ffmpeg", return_value=None):
            with self.assertRaises(DownloadError):
                manager.submit(
                    DownloadRequest(
                        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        audio_format="mp3",
                        audio_quality="192",
                    )
                )

    def test_clear_completed_jobs_only_removes_finished_states(self) -> None:
        manager = DownloadManager()
        active = DownloadJob(url="https://youtu.be/active", audio_format="mp3", audio_quality="192")
        active.status = JobState.downloading
        finished = DownloadJob(url="https://youtu.be/finished", audio_format="mp3", audio_quality="192")
        finished.status = JobState.completed
        failed = DownloadJob(url="https://youtu.be/failed", audio_format="mp3", audio_quality="192")
        failed.status = JobState.failed
        with manager._lock:
            manager._jobs = {
                active.job_id: active,
                finished.job_id: finished,
                failed.job_id: failed,
            }

        cleared = manager.clear_completed_jobs()

        self.assertEqual(cleared, 2)
        self.assertIsNotNone(manager.get_job(active.job_id))
        self.assertIsNone(manager.get_job(finished.job_id))
        self.assertIsNone(manager.get_job(failed.job_id))


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_clear_endpoint_returns_deleted_count(self) -> None:
        active = DownloadJob(url="https://youtu.be/active", audio_format="mp3", audio_quality="192")
        active.status = JobState.downloading
        finished = DownloadJob(url="https://youtu.be/finished", audio_format="mp3", audio_quality="192")
        finished.status = JobState.completed
        original_jobs = None

        with download_manager._lock:
            original_jobs = download_manager._jobs.copy()
            download_manager._jobs = {
                active.job_id: active,
                finished.job_id: finished,
            }

        try:
            response = self.client.post("/api/downloads/clear")
        finally:
            with download_manager._lock:
                download_manager._jobs = original_jobs

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cleared"], 1)


if __name__ == "__main__":
    unittest.main()
