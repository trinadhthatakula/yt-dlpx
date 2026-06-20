# YT-DLPx

A premium, modern desktop application for downloading media from YouTube and 1000+ other sites, and converting local media files between formats. Powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [ffmpeg](https://ffmpeg.org), with a beautiful, custom Slate/Indigo user interface built on CustomTkinter.

**Current Version: 0.2.0**

---

## Key Features

- **Sleek Sidebar Navigation**: Modern left-hand vertical sidebar for seamless switching between panels (Download, Convert, and Settings).
- **Video & Audio Downloader**:
  - Download video formats (MP4, MKV, WEBM) and audio-only formats (MP3, AAC, FLAC, WAV, OGG) with customizable quality levels.
  - Paste multiple URLs at once for batch/playlist queueing.
  - **Clipboard Helper**: A one-click "📋 Paste" button to instantly retrieve and append links.
  - Card-style queue rows with Tailwind-inspired colored status badges, real-time speed, ETA, and progress bar feedback.
- **Local Media Converter**:
  - Batch select local video/audio files.
  - Convert to 15+ formats (MP4 H.264/H.265, WEBM, MKV, GIF, MP3, AAC, FLAC, and more) with multi-threaded ffmpeg conversion.
  - Real-time conversion progress bar and thread-level cancellation.
- **Centralized Settings Panel**:
  - **Theme Switcher**: Instantly toggle between **System, Dark, and Light** modes.
  - **Custom Destinations**: Configure and browse default save locations for downloads and conversions.
  - **Concurrency Sliders**: Move concurrent download/conversion limits to the settings view to keep the workspace clean.
  - Settings are saved automatically at `~/.config/ytdlpx/settings.json`.

---

## Prerequisites

Before installing `yt-dlpx`, make sure you have the following system dependencies installed on your system path.

### 1. FFmpeg
Used for merging downloaded video/audio streams and performing conversions.
```bash
# macOS
brew install ffmpeg

# Linux (Debian/Ubuntu)
sudo apt install ffmpeg
```

### 2. Python with Tcl/Tk support
The GUI requires Tkinter, which requires a Python interpreter compiled with Tcl/Tk. Standard builds downloaded by some managers (like default `uv` or `pyenv`) may omit Tcl/Tk on macOS. It is recommended to use Homebrew's Python.
```bash
# macOS (Python 3.11 - 3.13)
brew install python@3.13
brew install python-tk@3.13
```

---

## Installation

### Recommended Method (pipx)
[pipx](https://pipx.pypa.io) installs `yt-dlpx` in an isolated environment and exposes the `yt-dlpx` CLI on your system `$PATH`.

1. **Install pipx** (if not already installed):
   ```bash
   brew install pipx
   pipx ensurepath
   ```
   *(Remember to restart your terminal after running `pipx ensurepath`)*

2. **Install yt-dlpx**:
   Specify the Homebrew Python path to ensure Tcl/Tk is enabled:
   ```bash
   pipx install . --python $(brew --prefix python@3.13)/bin/python3.13
   ```

3. **Launch the Application**:
   ```bash
   yt-dlpx
   ```

---

## Development Setup

If you want to run the project locally or contribute to development:

1. Clone or navigate to the repository directory.
2. Initialize and sync the virtual environment using `uv` (pointing to Homebrew's Python):
   ```bash
   uv sync --python $(brew --prefix python@3.13)/bin/python3.13
   ```
3. Run the application:
   ```bash
   uv run python src/ytdlpx/app.py
   ```

---

## Troubleshooting

### `ModuleNotFoundError: No module named '_tkinter'`
Your Python interpreter lacks Tcl/Tk. Ensure you installed `python-tk` from Homebrew and force a reinstall pointing explicitly to that Python version:
```bash
pipx install . --python $(brew --prefix python@3.13)/bin/python3.13 --force
```

### `ffmpeg` not found warning on launch
The application will launch, but video/audio merging and local file conversions will fail. Install `ffmpeg` using Homebrew or your Linux package manager.

---

## License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**. See the [LICENSE](LICENSE) file for the full license text.
