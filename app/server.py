from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import settings
from app.downloader import DownloadError, download_manager
from app.models import DownloadRequest


class DownloadRequestBody(BaseModel):
    url: str = Field(..., min_length=1)
    audioFormat: str = "mp3"
    audioQuality: str = "192"


app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "downloadRoot": str(settings.download_root),
    }


@app.get("/api/downloads")
def list_downloads() -> dict[str, object]:
    return {"jobs": download_manager.list_jobs()}


@app.get("/api/downloads/{job_id}")
def get_download(job_id: str) -> dict[str, object]:
    job = download_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Download job not found.")
    return job.as_dict()


@app.delete("/api/downloads/{job_id}", status_code=204)
def delete_download(job_id: str) -> None:
    if not download_manager.delete_job(job_id):
        raise HTTPException(status_code=404, detail="Download job not found.")


@app.post("/api/downloads/clear")
def clear_downloads() -> dict[str, object]:
    count = download_manager.clear_completed_jobs()
    return {"cleared": count}


@app.post("/api/downloads", status_code=202)
def create_download(payload: DownloadRequestBody) -> dict[str, object]:
    try:
        job = download_manager.submit(
            DownloadRequest(
                url=payload.url,
                audio_format=payload.audioFormat,
                audio_quality=payload.audioQuality,
            )
        )
    except DownloadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return job.as_dict()


@app.get("/api/downloads/{job_id}/files/{file_index}")
def download_file(job_id: str, file_index: int) -> FileResponse:
    job = download_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Download job not found.")
    if not job.files or file_index < 0 or file_index >= len(job.files):
        raise HTTPException(status_code=404, detail="File not found.")
    file_path = Path(job.files[file_index])
    if not file_path.exists():
        raise HTTPException(status_code=410, detail="File no longer exists on disk.")
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )


frontend_dist = Path("frontend/dist")
frontend_assets = frontend_dist / "assets"
if frontend_dist.exists():
    if frontend_assets.exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_assets)), name="assets")

    @app.get("/")
    def read_index() -> FileResponse:
        return FileResponse(frontend_dist / "index.html")
