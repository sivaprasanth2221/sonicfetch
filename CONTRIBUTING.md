# Contributing to SonicFetch

Thanks for contributing.

## Local workflow

1. Create and activate a virtual environment.
2. Install Python dependencies with `pip install -r requirements.txt`.
3. Install frontend dependencies with `cd frontend && npm install`.
4. Run the backend with `python download_mp3.py --reload`.
5. Run the frontend with `cd frontend && npm run dev`.

## Before opening a pull request

1. Run `PYTHONPATH=. ./.venv/bin/python -m unittest discover -s tests` or the equivalent command for your environment.
2. Build the frontend with `cd frontend && npm run build`.
3. Confirm the app can fetch one single video and one playlist.
4. Update the README if behavior or setup changed.

## Scope

- Keep changes focused and well-tested.
- Avoid committing virtual environments, downloads, or `node_modules`.
- Prefer improving tests when fixing lifecycle or API behavior.
