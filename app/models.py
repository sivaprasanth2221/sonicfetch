from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JobState(str, Enum):
    queued = "queued"
    downloading = "downloading"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


@dataclass
class DownloadRequest:
    url: str
    audio_format: str = "mp3"
    audio_quality: str = "192"


@dataclass
class DownloadJob:
    url: str
    audio_format: str
    audio_quality: str
    job_id: str = field(default_factory=lambda: str(uuid4()))
    status: JobState = JobState.queued
    progress: float = 0.0
    message: str = "Queued"
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    output_dir: str = ""
    title: str | None = None
    source_type: str | None = None
    is_playlist: bool = False
    items_downloaded: int = 0
    total_items: int | None = None
    files: list[str] = field(default_factory=list)
    error: str | None = None
    cancel_requested: bool = False
    skipped_items: int = 0
    warning: str | None = None

    def touch(self) -> None:
        self.updated_at = utc_now()

    def as_dict(self) -> dict[str, Any]:
        return {
            "jobId": self.job_id,
            "url": self.url,
            "audioFormat": self.audio_format,
            "audioQuality": self.audio_quality,
            "status": self.status.value,
            "progress": round(self.progress, 2),
            "message": self.message,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
            "outputDir": self.output_dir,
            "title": self.title,
            "sourceType": self.source_type,
            "isPlaylist": self.is_playlist,
            "itemsDownloaded": self.items_downloaded,
            "totalItems": self.total_items,
            "files": self.files,
            "error": self.error,
            "skippedItems": self.skipped_items,
            "warning": self.warning,
        }
