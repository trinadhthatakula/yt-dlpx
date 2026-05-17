# YT-DLPx

A modern desktop app for downloading videos and audio from YouTube and 1000+ other sites, and converting media files between formats — powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [ffmpeg](https://ffmpeg.org), with a clean dark UI built on CustomTkinter.

**Current version: 0.2.0**

---

## Features

**Download tab**
- Download video in MP4 (H.264 / H.265), MKV, or WEBM
- Download audio-only in MP3, AAC, FLAC, WAV, OGG, or OPUS
- Choose quality: Best, 4K, 1080p, 720p, 480p, and more
- Paste multiple URLs at once for batch or playlist downloads
- Real-time progress bar, speed, and ETA per item
- Run up to 5 downloads concurrently (adjustable slider)

**Convert tab**
- Convert any local video or audio file to a different format
- Select multiple files at once for batch conversion
- Video targets: MP4 (H.264 / H.265), MKV, WEBM, MOV, AVI, GIF
- Audio targets: MP3 (320 / 192 / 128k), AAC, FLAC, WAV, OGG, OPUS
- Real-time progress from ffmpeg, with per-file cancel support

**General**
- Cancel individual items or stop everything at once
- Dark mode UI — no browser required

---

## Prerequisites

You need two system dependencies before installing. These are not Python packages and cannot be installed via pip.

### 1. ffmpeg

Used for merging video/audio streams and all format conversions.

```bash
brew install ffmpeg
```

### 2. Python with Tcl/Tk support

The UI is built on Tkinter, which requires a Python that was compiled with Tcl/Tk. The standalone Python builds that `uv` and `pyenv` download do **not** include Tcl/Tk. You need Homebrew's Python and its matching `python-tk` formula.

Pick any Python version you like (3.11 or later). Python 3.13 is recommended as the current stable release:

```bash
brew install python@3.13     # or @3.11, @3.12 — your choice
brew install python-tk@3.13  # must match the version above
```

---

## Installation (pipx — recommended)

[pipx](https://pipx.pypa.io) installs the app in an isolated environment and puts the `yt-dlpx` command on your `$PATH`.

### Step 1 — Install pipx (if you don't have it)

```bash
brew install pipx
pipx ensurepath
```

Restart your terminal after running `pipx ensurepath`.

### Step 2 — Install ytdlpx

From the project folder, point pipx at whichever Homebrew Python you installed above:

```bash
pipx install . --python $(brew --prefix python@3.13)/bin/python3.13
```

Swap `python@3.13` for your chosen version if you picked a different one.

### Step 3 — Launch

```bash
yt-dlpx
```

That's it. The window opens immediately. You can run `yt-dlpx` from any directory, at any time.

---

## Updating

Pull the latest changes, then run:

```bash
cd /path/to/yt-dlp
pipx upgrade ytdlpx
```

`pipx upgrade` re-installs the package from the same source it was originally installed from, picking up any code and dependency changes in `pyproject.toml`. No need to specify the Python version again — pipx remembers which interpreter was used at install time.

To confirm the version you're running after an update:

```bash
pipx runpip ytdlpx show ytdlpx
```

> **Only if the environment seems broken** (e.g. after a major Python upgrade on your machine): do a full rebuild with `pipx reinstall ytdlpx`. This wipes and recreates the isolated environment from scratch. Unlike `upgrade`, you do need to pass `--python` again when reinstalling.

---

## Uninstalling

```bash
pipx uninstall ytdlpx
```

---

## Development Setup (uv)

If you want to run or hack on the code locally without installing via pipx:

```bash
# Enter the project
cd yt-dlp

# Create the venv — point at whichever Homebrew Python you installed
uv sync --python $(brew --prefix python@3.13)/bin/python3.13

# Run directly
uv run python src/ytdlpx/app.py
```

The `[tool.uv]` section in `pyproject.toml` is already set to `python-preference = "only-system"`, so `uv` will prefer Homebrew Python automatically if it's found on your PATH.

---

## Project Structure

```
yt-dlp/
├── pyproject.toml          # dependencies, build config, yt-dlpx entry point
├── src/
│   └── ytdlpx/
│       ├── __init__.py     # package version
│       └── app.py          # all app logic — UI, download queue, convert queue
└── README.md
```

---

## Troubleshooting

### `ModuleNotFoundError: No module named '_tkinter'`

Your Python was not compiled with Tcl/Tk. Make sure you installed both:

```bash
brew install python@3.13
brew install python-tk@3.13
```

Then reinstall using the explicit Homebrew Python path (substitute your version):

```bash
pipx install . --python $(brew --prefix python@3.13)/bin/python3.13 --force
```

### `ffmpeg not found` warning on launch

Install ffmpeg via Homebrew:

```bash
brew install ffmpeg
```

The app will still open without ffmpeg, but all format conversion and video/audio merging will fail.

### Downloads fail with `ERROR: Sign in to confirm your age`

Some videos require a logged-in session. This is a yt-dlp limitation for age-restricted content — see the [yt-dlp docs on cookies](https://github.com/yt-dlp/yt-dlp#cookies) for workarounds.

### The window doesn't appear after running `yt-dlpx`

Check that pipx used the right Python:

```bash
pipx runpip ytdlpx show customtkinter
```

If it shows an error, reinstall with the explicit `--python` flag as shown above.

### Conversion finishes instantly with no output file

This usually means ffmpeg exited with an error. Check that the input file isn't corrupted by running it manually:

```bash
ffprobe /path/to/your/file
```

---

## Changelog

### 0.2.0
- Added Convert tab for converting local media files between formats
- Batch file selection (select multiple files at once)
- 15 output formats across video and audio (MP4, MKV, WEBM, MOV, AVI, GIF, MP3, AAC, FLAC, WAV, OGG, OPUS, and more)
- Real-time ffmpeg progress via `-progress pipe:1`
- Per-file cancel terminates the ffmpeg process immediately

### 0.1.0
- Initial release
- Download tab with video and audio format support
- Concurrent downloads with adjustable limit
- Real-time progress, speed, and ETA

---

## Supported Sites

Any site supported by yt-dlp — including YouTube, Vimeo, Twitter/X, Instagram, SoundCloud, Twitch, and [1000+ more](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).
