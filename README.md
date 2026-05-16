# YT-DLPx

A modern desktop app for downloading videos and audio from YouTube and 1000+ other sites — powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [ffmpeg](https://ffmpeg.org), with a clean dark UI built on CustomTkinter.

---

## Features

- Download video in MP4 (H.264), MKV, or WEBM
- Download audio-only in MP3, AAC, FLAC, WAV, or OGG
- Choose quality: Best, 4K, 1080p, 720p, 480p, and more
- Paste multiple URLs at once for batch or playlist downloads
- Real-time progress bar, speed, and ETA per item
- Run up to 5 downloads concurrently (adjustable slider)
- Cancel individual downloads or stop everything at once
- Dark mode UI — no browser required

---

## Prerequisites

You need two system dependencies before installing. These are not Python packages and cannot be installed via pip.

### 1. ffmpeg

Used for merging video/audio streams and converting formats.

```bash
brew install ffmpeg
```

### 2. Python with Tcl/Tk support

The UI is built on Tkinter, which requires a Python that was compiled with Tcl/Tk. The standalone Python builds that `uv` and `pyenv` download do **not** include Tcl/Tk. Use Homebrew's Python instead, and install the matching `python-tk` formula.

```bash
brew install python@3.13
brew install python-tk@3.13
```

> **Why 3.13?** Python 3.14 is pre-release and `python-tk@3.14` may not yet be available on Homebrew. Python 3.13 is the current stable release and fully supported.

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

From the project folder, run:

```bash
pipx install . --python /opt/homebrew/opt/python@3.13/bin/python3.13
```

### Step 3 — Launch

```bash
yt-dlpx
```

That's it. The window opens immediately. You can run `yt-dlpx` from any directory, at any time.

---

## Updating

When you pull new changes, re-install in place:

```bash
pipx install . --python /opt/homebrew/opt/python@3.13/bin/python3.13 --force
```

---

## Uninstalling

```bash
pipx uninstall ytdlpx
```

---

## Development Setup (uv)

If you want to hack on the code locally:

```bash
# Clone / enter the project
cd yt-dlp

# Create the venv using Homebrew Python (has Tcl/Tk)
uv sync --python /opt/homebrew/opt/python@3.13/bin/python3.13

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
│       ├── __init__.py
│       └── app.py          # all app logic — UI, download queue, yt-dlp integration
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

Then re-install using the explicit Homebrew Python path:

```bash
pipx install . --python /opt/homebrew/opt/python@3.13/bin/python3.13 --force
```

### `ffmpeg not found` warning on launch

Install ffmpeg via Homebrew:

```bash
brew install ffmpeg
```

The app will still open without ffmpeg, but format conversion (e.g. extracting MP3 from a video stream) will fail.

### Downloads fail with `ERROR: Sign in to confirm your age`

Some videos require a logged-in session. This is a yt-dlp limitation for age-restricted content — see the [yt-dlp docs on cookies](https://github.com/yt-dlp/yt-dlp#cookies) for workarounds.

### The window doesn't appear after running `yt-dlpx`

Check that pipx used the right Python:

```bash
pipx runpip ytdlpx show customtkinter
```

If it shows an error, reinstall with the explicit `--python` flag as shown above.

---

## Supported Sites

Any site supported by yt-dlp — including YouTube, Vimeo, Twitter/X, Instagram, SoundCloud, Twitch, and [1000+ more](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).
