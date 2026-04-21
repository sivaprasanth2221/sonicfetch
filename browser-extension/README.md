# SonicFetch Browser Companion

This browser extension sends the current YouTube page or a clicked YouTube link directly into a locally running SonicFetch instance.

## Why this lives in the same repo

This extension is a first-party companion to SonicFetch rather than a separate product. Keeping it in the same repository makes the release process, docs, versioning, and API compatibility easier to maintain.

## Features

- Send the current YouTube tab to SonicFetch from the popup
- Right-click a YouTube page or link and send it directly
- Configure the SonicFetch backend URL
- Save default format and bitrate preferences locally in the browser

## Load it locally

### Chrome / Edge / Brave

1. Open `chrome://extensions/`
2. Enable `Developer mode`
3. Click `Load unpacked`
4. Select the `browser-extension/` folder from this repo

### Firefox

1. Open `about:debugging#/runtime/this-firefox`
2. Click `Load Temporary Add-on`
3. Choose any file inside `browser-extension/`, such as `manifest.json`

## Requirements

- SonicFetch backend running locally
- Default backend API URL: `http://127.0.0.1:8000`
- Default dashboard URL: `http://localhost:5173`

## Usage

1. Start SonicFetch locally
2. Open any YouTube video or playlist page
3. Click the SonicFetch extension icon
4. Confirm the URL and click `Send to SonicFetch`

You can also right-click a YouTube page or a YouTube link and use the SonicFetch context-menu action.
