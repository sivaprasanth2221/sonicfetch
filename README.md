# SonicFetch

SonicFetch is a cross-platform YouTube-to-audio downloader with a FastAPI backend and a React + Vite frontend. It supports single videos, playlists, shorts, and live URLs, converts them to audio, tracks job progress, and lets you clean up completed downloads from both history and disk.

## Highlights

- Fetch audio from YouTube videos, playlists, shorts, and live links
- Convert to `mp3`, `m4a`, or `wav` at `128`, `192`, `256`, or `320` kbps
- Cancel running jobs safely without crashing background workers
- Skip unavailable playlist items while keeping the rest of the batch moving
- Clear finished jobs in bulk and free disk space automatically
- Browser extension for sending YouTube links directly into SonicFetch
- Run locally on Windows, macOS, and Linux, or package with Docker

## Tech Stack

- Backend: FastAPI, `yt-dlp`, `ffmpeg`
- Frontend: React, Vite
- Testing: `unittest`, FastAPI `TestClient`
- CI: GitHub Actions

## Repository Layout

```text
.
|-- app/
|   |-- cli.py
|   |-- config.py
|   |-- downloader.py
|   |-- models.py
|   `-- server.py
|-- browser-extension/
|   |-- manifest.json
|   |-- background.js
|   |-- popup.html
|   `-- README.md
|-- frontend/
|   |-- public/
|   |-- src/
|   |-- package.json
|   `-- vite.config.js
|-- tests/
|   `-- test_downloader.py
|-- .env.example
|-- .github/workflows/ci.yml
|-- CONTRIBUTING.md
|-- Dockerfile
|-- docker-compose.yml
|-- LICENSE
|-- download_mp3.py
`-- requirements.txt
```

## Requirements

| Tool | Recommended |
|------|-------------|
| Python | 3.10+ |
| Node.js | 20+ |
| npm | 9+ |
| ffmpeg | Any recent version on PATH |

Python 3.9 may still work in some environments, but newer Python versions are recommended because `yt-dlp` support moves quickly.

## Local Setup

### 1. Install `ffmpeg`

macOS:

```bash
brew install ffmpeg
```

Ubuntu / Debian:

```bash
sudo apt update
sudo apt install ffmpeg
```

Fedora:

```bash
sudo dnf install ffmpeg
```

Arch:

```bash
sudo pacman -S ffmpeg
```

Windows:

Download a build from [ffmpeg.org](https://ffmpeg.org/download.html) and add its `bin` directory to your `PATH`.

### 2. Backend setup

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Frontend setup

```bash
cd frontend
npm install
cd ..
```

### 4. Run the app

Backend:

```bash
python download_mp3.py --reload
```

Frontend:

```bash
cd frontend
npm run dev
```

The backend runs at [http://127.0.0.1:8000](http://127.0.0.1:8000) and the frontend runs at [http://localhost:5173](http://localhost:5173).

## Environment Variables

Copy `.env.example` to `.env` if you want local overrides.

| Variable | Default | Purpose |
|----------|---------|---------|
| `APP_HOST` | `127.0.0.1` | Backend bind host |
| `APP_PORT` | `8000` | Backend bind port |
| `DOWNLOAD_DIR` | `downloads` | Output directory |
| `FRONTEND_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed browser origins |
| `EXTENSION_ORIGIN_REGEX` | `^(chrome-extension|moz-extension)://.*$` | Allowed browser-extension origins |
| `MAX_DOWNLOAD_WORKERS` | `2` | Background download concurrency |

## Docker

Build and run SonicFetch with Docker:

```bash
docker build -t sonicfetch .
docker run --rm -p 8000:8000 -v "$(pwd)/downloads:/app/downloads" sonicfetch
```

Or with Docker Compose:

```bash
cp .env.example .env
docker compose up --build
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/downloads` | List jobs |
| `GET` | `/api/downloads/{job_id}` | Get one job |
| `POST` | `/api/downloads` | Start a new job |
| `DELETE` | `/api/downloads/{job_id}` | Cancel or remove one job |
| `POST` | `/api/downloads/clear` | Clear finished jobs |
| `GET` | `/api/downloads/{job_id}/files/{file_index}` | Download one output file |

Example request:

```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "audioFormat": "mp3",
  "audioQuality": "192"
}
```

## Browser Extension

SonicFetch now includes a first-party browser extension in [browser-extension/](./browser-extension/) for sending YouTube links directly into the local app.

Features:

- Send the current YouTube tab to SonicFetch from the extension popup
- Right-click a YouTube page or link and send it through a context-menu action
- Store default format, quality, backend API URL, and dashboard URL preferences in browser storage

Load it locally:

### Chrome / Edge / Brave

1. Open `chrome://extensions/`
2. Enable `Developer mode`
3. Click `Load unpacked`
4. Select the `browser-extension/` folder

### Firefox

1. Open `about:debugging#/runtime/this-firefox`
2. Click `Load Temporary Add-on`
3. Choose `browser-extension/manifest.json`

The extension-specific usage notes are documented in [browser-extension/README.md](./browser-extension/README.md).

## Testing

Run backend tests:

```bash
PYTHONPATH=. python -m unittest discover -s tests
```

The test suite covers:

- URL and audio option validation
- Windows `ffmpeg.exe` fallback resolution
- Safe deletion and cancellation handling
- Finished-job bulk clearing
- FastAPI clear endpoint behavior

## Production Build

To serve the built frontend from FastAPI:

```bash
cd frontend
npm run build
cd ..
python download_mp3.py
```

If `frontend/dist` exists, the backend serves the built app at the root path.

## GitHub Push Checklist

Before your first push:

1. Make sure `.venv`, `venv`, `downloads`, and `frontend/node_modules` are not staged.
2. Run the backend tests.
3. Run `npm run build` inside `frontend`.
4. Confirm one single-video download and one playlist download work locally.
5. Add repository screenshots or a short demo GIF if you want a stronger project landing page.

## Contributing and License

- Contribution guide: [CONTRIBUTING.md](./CONTRIBUTING.md)
- License: [MIT](./LICENSE)
