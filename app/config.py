from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _split_origins(value: str) -> list[str]:
    origins = []
    for origin in value.split(","):
        item = origin.strip()
        if item:
            origins.append(item)
    return origins


@dataclass
class Settings:
    app_name: str = "SonicFetch"
    host: str = field(default_factory=lambda: os.getenv("APP_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("APP_PORT", "8000")))
    download_root: Path = field(
        default_factory=lambda: Path(os.getenv("DOWNLOAD_DIR", "downloads")).resolve()
    )
    allowed_origins: list[str] = field(
        default_factory=lambda: _split_origins(
            os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
        )
    )
    extension_origin_regex: str = field(
        default_factory=lambda: os.getenv(
            "EXTENSION_ORIGIN_REGEX",
            r"^(chrome-extension|moz-extension)://.*$",
        )
    )
    max_workers: int = field(default_factory=lambda: int(os.getenv("MAX_DOWNLOAD_WORKERS", "2")))


settings = Settings()
