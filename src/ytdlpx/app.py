"""
YT-DLPx — Modern Desktop Downloader & Converter
Requires: customtkinter, yt-dlp, Pillow  |  System: ffmpeg, ffprobe
"""

import customtkinter as ctk
import threading
import queue
import os
import sys
import time
import subprocess
import json
from pathlib import Path
from tkinter import filedialog, messagebox
import yt_dlp

# ──────────────────────────────────────────────
#  Theme / Color Palette
# ──────────────────────────────────────────────
# Custom color tokens for premium dark/light look
COLOR_BG_MAIN      = ("#F8FAFC", "#0B0F19")  # Slate 50 vs deep dark blue-slate
COLOR_BG_SIDEBAR   = ("#F1F5F9", "#151E2E")  # Slate 100 vs slate-dark sidebar
COLOR_BG_CARD      = ("#FFFFFF", "#1E293B")  # White vs slate-800 card
COLOR_BG_PANEL     = ("#E2E8F0", "#111827")  # Slate 200 vs darker panel
COLOR_BORDER       = ("#CBD5E1", "#1F2937")  # Slate 300 vs slate-900 border
COLOR_TEXT_TITLE   = ("#0F172A", "#F8FAFC")  # Slate 900 vs Slate 50 text
COLOR_TEXT_MUTED   = ("#64748B", "#94A3B8")  # Slate 500 vs Slate 400 text

# Interactive colors
COLOR_INDIGO       = "#6366F1"
COLOR_INDIGO_HOVER = "#4F46E5"
COLOR_EMERALD      = "#10B981"
COLOR_EMERALD_HOVER = "#059669"
COLOR_ROSE         = "#F43F5E"
COLOR_ROSE_HOVER   = "#E11D48"
COLOR_MUTED        = ("#94A3B8", "#475569")
COLOR_MUTED_HOVER  = ("#64748B", "#334155")

STATUS_COLORS = {
    "Queued":      "#6B7280",      # Gray
    "Downloading": "#3B82F6",      # Blue
    "Converting":  "#F59E0B",      # Orange
    "Done":        "#10B981",      # Green
    "Error":       "#EF4444",      # Red
    "Cancelled":   "#9CA3AF",      # Muted Gray
}

BADGE_COLORS = {
    "Queued":      {"bg": ("#E2E8F0", "#334155"), "fg": ("#475569", "#94A3B8")},
    "Downloading": {"bg": ("#DBEAFE", "#1E3A8A"), "fg": ("#1D4ED8", "#93C5FD")},
    "Converting":  {"bg": ("#FEF3C7", "#78350F"), "fg": ("#D97706", "#FCD34D")},
    "Done":        {"bg": ("#D1FAE5", "#064E3B"), "fg": ("#047857", "#6EE7B7")},
    "Error":       {"bg": ("#FEE2E2", "#7F1D1D"), "fg": ("#B91C1C", "#FCA5A5")},
    "Cancelled":   {"bg": ("#F3F4F6", "#374151"), "fg": ("#4B5563", "#D1D5DB")},
}

# ──────────────────────────────────────────────
#  Download constants
# ──────────────────────────────────────────────
VIDEO_FORMATS   = ["MP4 (H.264)", "MKV (Best)", "WEBM (VP9)", "MP4 (Best Quality)"]
AUDIO_FORMATS   = ["MP3 (320k)", "MP3 (192k)", "AAC (Best)", "FLAC (Lossless)", "WAV", "OGG"]
VIDEO_QUALITIES = ["Best Available", "4K (2160p)", "1080p", "720p", "480p", "360p", "240p"]

DOWNLOAD_FORMAT_MAP = {
    "MP4 (H.264)":       {"format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", "merge_output_format": "mp4"},
    "MKV (Best)":        {"format": "bestvideo+bestaudio/best",                                  "merge_output_format": "mkv"},
    "WEBM (VP9)":        {"format": "bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]/best","merge_output_format": "webm"},
    "MP4 (Best Quality)":{"format": "bestvideo+bestaudio/best",                                  "merge_output_format": "mp4"},
    "MP3 (320k)":        {"format": "bestaudio/best", "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "320"}]},
    "MP3 (192k)":        {"format": "bestaudio/best", "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]},
    "AAC (Best)":        {"format": "bestaudio/best", "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "aac"}]},
    "FLAC (Lossless)":   {"format": "bestaudio/best", "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "flac"}]},
    "WAV":               {"format": "bestaudio/best", "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}]},
    "OGG":               {"format": "bestaudio/best", "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "vorbis"}]},
}

QUALITY_MAP = {
    "Best Available": "",
    "4K (2160p)":     "[height<=2160]",
    "1080p":          "[height<=1080]",
    "720p":           "[height<=720]",
    "480p":           "[height<=480]",
    "360p":           "[height<=360]",
    "240p":           "[height<=240]",
}

# ──────────────────────────────────────────────
#  Conversion constants
# ──────────────────────────────────────────────
CONVERT_FORMAT_MAP = {
    # ── Video ──
    "MP4 (H.264)":    {"ext": "mp4",  "args": ["-c:v", "libx264",   "-c:a", "aac",       "-preset", "fast", "-movflags", "+faststart"]},
    "MP4 (H.265)":    {"ext": "mp4",  "args": ["-c:v", "libx265",   "-c:a", "aac",       "-preset", "fast", "-movflags", "+faststart"]},
    "MKV (copy)":     {"ext": "mkv",  "args": ["-c:v", "copy",      "-c:a", "copy"]},
    "WEBM (VP9)":     {"ext": "webm", "args": ["-c:v", "libvpx-vp9","-c:a", "libopus",   "-b:v", "0", "-crf", "30"]},
    "MOV":            {"ext": "mov",  "args": ["-c:v", "copy",      "-c:a", "copy"]},
    "AVI":            {"ext": "avi",  "args": ["-c:v", "libxvid",   "-c:a", "libmp3lame"]},
    "GIF":            {"ext": "gif",  "args": ["-vf",  "fps=15,scale=480:-1:flags=lanczos", "-loop", "0"]},
    # ── Audio ──
    "MP3 (320k)":     {"ext": "mp3",  "args": ["-vn", "-c:a", "libmp3lame", "-b:a", "320k"]},
    "MP3 (192k)":     {"ext": "mp3",  "args": ["-vn", "-c:a", "libmp3lame", "-b:a", "192k"]},
    "MP3 (128k)":     {"ext": "mp3",  "args": ["-vn", "-c:a", "libmp3lame", "-b:a", "128k"]},
    "AAC (256k)":     {"ext": "aac",  "args": ["-vn", "-c:a", "aac",        "-b:a", "256k"]},
    "FLAC":           {"ext": "flac", "args": ["-vn", "-c:a", "flac"]},
    "WAV":            {"ext": "wav",  "args": ["-vn", "-c:a", "pcm_s16le"]},
    "OGG":            {"ext": "ogg",  "args": ["-vn", "-c:a", "libvorbis",  "-q:a", "6"]},
    "OPUS":           {"ext": "opus", "args": ["-vn", "-c:a", "libopus",    "-b:a", "128k"]},
}

CONVERT_FORMAT_GROUPS = {
    "Video": ["MP4 (H.264)", "MP4 (H.265)", "MKV (copy)", "WEBM (VP9)", "MOV", "AVI", "GIF"],
    "Audio": ["MP3 (320k)", "MP3 (192k)", "MP3 (128k)", "AAC (256k)", "FLAC", "WAV", "OGG", "OPUS"],
}


# ──────────────────────────────────────────────
#  Data models
# ──────────────────────────────────────────────
class DownloadItem:
    def __init__(self, url: str, fmt: str, quality: str, out_dir: str):
        self.url       = url.strip()
        self.fmt       = fmt
        self.quality   = quality
        self.out_dir   = out_dir
        self.status    = "Queued"
        self.progress  = 0.0
        self.title     = url[:60] + "…" if len(url) > 60 else url
        self.cancelled = False
        self.title_label  = None
        self.status_label = None
        self.progress_bar = None
        self.speed_label  = None
        self.cancel_btn   = None
        self.row_frame    = None


class ConvertItem:
    def __init__(self, input_path: str, fmt: str, out_dir: str):
        self.input_path = input_path
        self.fmt        = fmt
        self.out_dir    = out_dir
        self.status     = "Queued"
        self.progress   = 0.0
        self.cancelled  = False
        self.proc       = None           # subprocess.Popen reference for cancellation
        self.name       = Path(input_path).name
        self.title_label  = None
        self.status_label = None
        self.progress_bar = None
        self.info_label   = None
        self.cancel_btn   = None
        self.row_frame    = None


# ──────────────────────────────────────────────
#  ffprobe helper
# ──────────────────────────────────────────────
def _get_duration(path: str) -> float:
    """Return media duration in seconds (0 on failure)."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error",
             "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1",
             path],
            capture_output=True, text=True, timeout=10,
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


# ──────────────────────────────────────────────
#  Shared queue row builder
# ──────────────────────────────────────────────
def _build_queue_row(parent, title: str, subtitle: str, on_cancel, item):
    """Create a styled queue row and assign widget references onto *item*."""
    # Custom card frame
    row = ctk.CTkFrame(
        parent,
        corner_radius=10,
        fg_color=COLOR_BG_CARD,
        border_color=COLOR_BORDER,
        border_width=1
    )
    row.pack(fill="x", pady=4, padx=4)
    item.row_frame = row

    left = ctk.CTkFrame(row, fg_color="transparent")
    left.pack(side="left", fill="both", expand=True, padx=(16, 6), pady=10)

    # Title with clean font
    item.title_label = ctk.CTkLabel(
        left, text=title,
        font=ctk.CTkFont(size=13, weight="bold"),
        text_color=COLOR_TEXT_TITLE, anchor="w"
    )
    item.title_label.pack(fill="x")

    # Subtitle
    ctk.CTkLabel(
        left, text=subtitle, font=ctk.CTkFont(size=11),
        text_color=COLOR_TEXT_MUTED, anchor="w"
    ).pack(fill="x", pady=(2, 0))

    # Modern Progress Bar
    item.progress_bar = ctk.CTkProgressBar(
        left, height=6, corner_radius=3,
        progress_color=COLOR_INDIGO, fg_color=COLOR_BORDER
    )
    item.progress_bar.set(0)
    item.progress_bar.pack(fill="x", pady=(8, 4))

    # Meta Info Row
    meta = ctk.CTkFrame(left, fg_color="transparent")
    meta.pack(fill="x")
    item.info_label = ctk.CTkLabel(
        meta, text="", font=ctk.CTkFont(size=11),
        text_color=COLOR_TEXT_MUTED, anchor="w"
    )
    item.info_label.pack(side="left")

    right = ctk.CTkFrame(row, fg_color="transparent", width=140)
    right.pack(side="right", padx=(6, 16), pady=10)
    right.pack_propagate(False)

    # Badge Container (to align right)
    badge_container = ctk.CTkFrame(right, fg_color="transparent")
    badge_container.pack(fill="x", anchor="e")

    # Initial Badge Status: QUEUED
    badge_cfg = BADGE_COLORS["Queued"]
    item.status_label = ctk.CTkLabel(
        badge_container,
        text="QUEUED",
        font=ctk.CTkFont(size=10, weight="bold"),
        fg_color=badge_cfg["bg"],
        text_color=badge_cfg["fg"],
        corner_radius=6,
        height=22,
        width=100
    )
    item.status_label.pack(side="right")

    # Custom cancel button with hover states
    item.cancel_btn = ctk.CTkButton(
        right, text="✕ Cancel", width=100, height=26,
        font=ctk.CTkFont(size=11, weight="bold"),
        fg_color=COLOR_MUTED, hover_color=COLOR_ROSE,
        text_color=COLOR_TEXT_TITLE,
        command=on_cancel,
        corner_radius=6
    )
    item.cancel_btn.pack(side="right", pady=(8, 0))

    # alias so download code (which uses .speed_label) still works
    item.speed_label = item.info_label


# ──────────────────────────────────────────────
#  Main Application
# ──────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("YT-DLPx")
        self.geometry("1024x720")
        self.minsize(880, 600)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Load settings
        self._load_app_settings()

        # Download state
        self._dl_queue: "queue.Queue[DownloadItem]" = queue.Queue()
        self._dl_items: list[DownloadItem] = []
        self._dl_threads: list[threading.Thread] = []
        self._dl_max = self._settings["max_downloads"]
        self._dl_running = True

        # Convert state
        self._cv_queue: "queue.Queue[ConvertItem]" = queue.Queue()
        self._cv_items: list[ConvertItem] = []
        self._cv_threads: list[threading.Thread] = []
        self._cv_max = self._settings["max_conversions"]
        self._cv_running = True

        # Pending files added to Convert tab (not yet dispatched)
        self._pending_files: list[str] = []

        # Shared thread-safe UI update queue
        self._ui_queue: "queue.Queue" = queue.Queue()

        self._build_ui()
        self._start_dl_dispatcher()
        self._start_cv_dispatcher()
        self._poll_ui_queue()

    # ══════════════════════════════════════════
    #  SETTINGS PERSISTENCE
    # ══════════════════════════════════════════
    def _load_app_settings(self):
        self._settings = {
            "appearance_mode": "Dark",
            "download_dir": str(Path.home() / "Downloads"),
            "convert_dir": str(Path.home() / "Downloads"),
            "default_quality": "Best Available",
            "max_downloads": 2,
            "max_conversions": 2,
        }
        self._settings_path = Path.home() / ".config" / "ytdlpx" / "settings.json"
        try:
            if self._settings_path.exists():
                with open(self._settings_path, "r") as f:
                    self._settings.update(json.load(f))
        except Exception:
            pass
            
        # Apply appearance mode
        ctk.set_appearance_mode(self._settings["appearance_mode"])
        
    def _save_app_settings(self):
        try:
            self._settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._settings_path, "w") as f:
                json.dump(self._settings, f, indent=4)
        except Exception:
            pass

    def _on_setting_changed(self, *args):
        # Update setting values
        self._settings["appearance_mode"] = self._settings_appearance_var.get()
        self._settings["download_dir"] = self._settings_dl_dir_var.get()
        self._settings["convert_dir"] = self._settings_cv_dir_var.get()
        self._settings["default_quality"] = self._settings_quality_var.get()
        self._settings["max_downloads"] = int(self._settings_max_dl_var.get())
        self._settings["max_conversions"] = int(self._settings_max_cv_var.get())
        
        # Apply changes immediately
        ctk.set_appearance_mode(self._settings["appearance_mode"])
        self._dl_max = self._settings["max_downloads"]
        self._cv_max = self._settings["max_conversions"]
        
        # Sync the directory variables on the main views
        self._dl_out_var.set(self._settings["download_dir"])
        self._cv_out_var.set(self._settings["convert_dir"])
        
        self._save_app_settings()

    def _on_dl_slider_change(self, val):
        self._settings_max_dl_lbl.configure(text=str(int(val)))
        self._on_setting_changed()

    def _on_cv_slider_change(self, val):
        self._settings_max_cv_lbl.configure(text=str(int(val)))
        self._on_setting_changed()

    # ══════════════════════════════════════════
    #  TOP-LEVEL UI & NAVIGATION
    # ══════════════════════════════════════════
    def _build_ui(self):
        # Configure grid layout: 1 row, 2 columns (sidebar and main panel)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Sidebar Frame ──
        self._sidebar_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=COLOR_BG_SIDEBAR, width=200)
        self._sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self._sidebar_frame.grid_rowconfigure(5, weight=1)  # Spacer

        # Sidebar Title
        title_label = ctk.CTkLabel(
            self._sidebar_frame,
            text="YT-DLPx",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLOR_INDIGO,
        )
        title_label.grid(row=0, column=0, padx=20, pady=(24, 6), sticky="w")

        subtitle_label = ctk.CTkLabel(
            self._sidebar_frame,
            text="Media Hub",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
        )
        subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 24), sticky="w")

        # Sidebar navigation buttons
        self._nav_buttons = {}
        navs = [
            ("download", "⬇  Download"),
            ("convert", "🔄  Convert"),
            ("settings", "⚙️  Settings")
        ]
        
        for idx, (view_name, label) in enumerate(navs):
            btn = ctk.CTkButton(
                self._sidebar_frame,
                text=label,
                corner_radius=8,
                height=40,
                border_spacing=10,
                anchor="w",
                font=ctk.CTkFont(size=14, weight="bold"),
                fg_color="transparent",
                text_color=COLOR_TEXT_TITLE,
                hover_color=("#E2E8F0", "#1E293B"),
                command=lambda v=view_name: self._select_view(v)
            )
            btn.grid(row=idx+2, column=0, padx=12, pady=4, sticky="ew")
            self._nav_buttons[view_name] = btn

        # Version label at bottom of sidebar
        version_label = ctk.CTkLabel(
            self._sidebar_frame,
            text="v0.3.0",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED,
        )
        version_label.grid(row=6, column=0, padx=20, pady=16, sticky="w")

        # ── Main Content Area ──
        self._main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=COLOR_BG_MAIN)
        self._main_frame.grid(row=0, column=1, sticky="nsew")
        self._main_frame.grid_columnconfigure(0, weight=1)
        self._main_frame.grid_rowconfigure(0, weight=1)

        # Create the views
        self._views = {}
        self._views["download"] = ctk.CTkFrame(self._main_frame, fg_color="transparent")
        self._views["convert"] = ctk.CTkFrame(self._main_frame, fg_color="transparent")
        self._views["settings"] = ctk.CTkFrame(self._main_frame, fg_color="transparent")

        self._build_download_view(self._views["download"])
        self._build_convert_view(self._views["convert"])
        self._build_settings_view(self._views["settings"])

        # Default view
        self._select_view("download")

    def _select_view(self, name):
        # Update sidebar buttons active state
        for view_name, btn in self._nav_buttons.items():
            if view_name == name:
                btn.configure(fg_color=COLOR_INDIGO, text_color="#FFFFFF", hover_color=COLOR_INDIGO_HOVER)
            else:
                btn.configure(fg_color="transparent", text_color=COLOR_TEXT_TITLE, hover_color=("#E2E8F0", "#1E293B"))

        # Hide all view frames, show selected
        for view_frame in self._views.values():
            view_frame.grid_forget()
        self._views[name].grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

    # ══════════════════════════════════════════
    #  DOWNLOAD VIEW
    # ══════════════════════════════════════════
    def _build_download_view(self, parent):
        # Title of view
        title_row = ctk.CTkFrame(parent, fg_color="transparent")
        title_row.pack(fill="x", padx=12, pady=(4, 12))
        
        ctk.CTkLabel(
            title_row,
            text="Video & Audio Downloader",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLOR_TEXT_TITLE,
        ).pack(side="left")

        # ── Input panel ──
        panel = ctk.CTkFrame(parent, corner_radius=12, fg_color=COLOR_BG_PANEL, border_color=COLOR_BORDER, border_width=1)
        panel.pack(fill="x", padx=4, pady=(0, 12))

        # URL Box Row
        url_row = ctk.CTkFrame(panel, fg_color="transparent")
        url_row.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            url_row, text="URLs", width=54,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
            anchor="w"
        ).pack(side="left")

        # Container for Entry & Paste button
        entry_container = ctk.CTkFrame(url_row, fg_color="transparent")
        entry_container.pack(side="left", fill="x", expand=True, padx=(8, 0))

        self._url_entry = ctk.CTkTextbox(
            entry_container, height=64, font=ctk.CTkFont(size=13),
            fg_color=COLOR_BG_MAIN, border_color=COLOR_BORDER, border_width=1, corner_radius=8,
        )
        self._url_entry.pack(side="left", fill="x", expand=True)
        self._url_entry.insert("0.0", "Paste one or more URLs here, one per line…")
        self._url_entry.bind("<FocusIn>",  self._clear_url_placeholder)
        self._url_entry.bind("<FocusOut>", self._restore_url_placeholder)

        # Paste Clipboard Button
        paste_btn = ctk.CTkButton(
            entry_container,
            text="📋 Paste",
            width=76,
            height=64,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLOR_INDIGO,
            hover_color=COLOR_INDIGO_HOVER,
            text_color="#FFFFFF",
            command=self._dl_paste_clipboard,
            corner_radius=8,
        )
        paste_btn.pack(side="right", padx=(8, 0))

        # Format / Quality Options Row
        opts_row = ctk.CTkFrame(panel, fg_color="transparent")
        opts_row.pack(fill="x", padx=16, pady=(0, 8))

        self._dl_type = ctk.StringVar(value="Video")
        type_frame = ctk.CTkFrame(opts_row, fg_color="transparent")
        type_frame.pack(side="left", padx=(62, 12))
        for t in ("Video", "Audio"):
            ctk.CTkRadioButton(
                type_frame, text=t, value=t,
                variable=self._dl_type, command=self._on_dl_type_change,
                font=ctk.CTkFont(size=13), radiobutton_width=16, radiobutton_height=16,
                fg_color=COLOR_INDIGO, hover_color=COLOR_INDIGO_HOVER,
                text_color=COLOR_TEXT_TITLE
            ).pack(side="left", padx=(0, 16))

        ctk.CTkLabel(
            opts_row, text="Format:", font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_MUTED
        ).pack(side="left")
        
        self._dl_fmt_var = ctk.StringVar(value=VIDEO_FORMATS[0])
        self._dl_fmt_menu = ctk.CTkOptionMenu(
            opts_row, variable=self._dl_fmt_var, values=VIDEO_FORMATS, width=178,
            font=ctk.CTkFont(size=13),
            fg_color=COLOR_BG_MAIN, button_color=COLOR_MUTED, button_hover_color=COLOR_MUTED_HOVER,
            text_color=COLOR_TEXT_TITLE,
            dropdown_fg_color=COLOR_BG_MAIN, dropdown_text_color=COLOR_TEXT_TITLE,
            dropdown_hover_color=COLOR_MUTED
        )
        self._dl_fmt_menu.pack(side="left", padx=(8, 20))

        self._quality_label = ctk.CTkLabel(
            opts_row, text="Quality:", font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_MUTED
        )
        self._quality_label.pack(side="left")
        
        self._quality_var = ctk.StringVar(value=self._settings["default_quality"])
        self._quality_menu = ctk.CTkOptionMenu(
            opts_row, variable=self._quality_var, values=VIDEO_QUALITIES, width=148,
            font=ctk.CTkFont(size=13),
            fg_color=COLOR_BG_MAIN, button_color=COLOR_MUTED, button_hover_color=COLOR_MUTED_HOVER,
            text_color=COLOR_TEXT_TITLE,
            dropdown_fg_color=COLOR_BG_MAIN, dropdown_text_color=COLOR_TEXT_TITLE,
            dropdown_hover_color=COLOR_MUTED
        )
        self._quality_menu.pack(side="left", padx=(8, 0))

        # Save to Location Row
        dir_row = ctk.CTkFrame(panel, fg_color="transparent")
        dir_row.pack(fill="x", padx=16, pady=(4, 16))

        ctk.CTkLabel(
            dir_row, text="Save to", width=54,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
            anchor="w"
        ).pack(side="left")

        self._dl_out_var = ctk.StringVar(value=self._settings["download_dir"])
        
        dl_out_entry = ctk.CTkEntry(
            dir_row, textvariable=self._dl_out_var, font=ctk.CTkFont(size=13),
            fg_color=COLOR_BG_MAIN, border_color=COLOR_BORDER,
            text_color=COLOR_TEXT_TITLE, corner_radius=8
        )
        dl_out_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        
        ctk.CTkButton(
            dir_row, text="Browse", width=80,
            command=lambda: self._browse_dir(self._dl_out_var),
            fg_color=COLOR_MUTED, hover_color=COLOR_MUTED_HOVER,
            text_color=COLOR_TEXT_TITLE, font=ctk.CTkFont(size=13),
            corner_radius=8
        ).pack(side="left")

        # ── Buttons ──
        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill="x", padx=4, pady=(0, 8))

        actions = [
            ("＋ Add to Queue", COLOR_INDIGO, COLOR_INDIGO_HOVER, "#FFFFFF", self._dl_add_to_queue),
            ("▶ Start All",    COLOR_EMERALD, COLOR_EMERALD_HOVER, "#FFFFFF", self._dl_start_all),
            ("⏹ Stop All",     COLOR_ROSE, COLOR_ROSE_HOVER, "#FFFFFF", self._dl_stop_all),
            ("🗑 Clear Done",   COLOR_MUTED, COLOR_MUTED_HOVER, COLOR_TEXT_TITLE, self._dl_clear_done),
        ]
        
        for label, color, hover, t_color, cmd in actions:
            ctk.CTkButton(
                btn_row, text=label, width=130, height=36,
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color=color, hover_color=hover, text_color=t_color,
                command=cmd, corner_radius=8
            ).pack(side="left", padx=(0, 8))

        # ── Stats ──
        stats_frame = ctk.CTkFrame(parent, fg_color="transparent")
        stats_frame.pack(fill="x", padx=6, pady=(0, 6))
        
        self._dl_stats_label = ctk.CTkLabel(
            stats_frame, text="Queue: 0  |  Downloading: 0  |  Done: 0  |  Error: 0",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_MUTED,
        )
        self._dl_stats_label.pack(side="left")

        # ── Queue scroll ──
        self._dl_scroll = ctk.CTkScrollableFrame(
            parent, corner_radius=12, fg_color=COLOR_BG_PANEL, border_color=COLOR_BORDER, border_width=1,
            scrollbar_button_color=COLOR_MUTED, scrollbar_button_hover_color=COLOR_MUTED_HOVER,
        )
        self._dl_scroll.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        self._dl_empty_label = ctk.CTkLabel(
            self._dl_scroll,
            text="No active downloads.\n\nEnter video or playlist URLs above to build your queue.",
            font=ctk.CTkFont(size=14), text_color=COLOR_TEXT_MUTED,
            justify="center"
        )
        self._dl_empty_label.pack(pady=80)

    # ══════════════════════════════════════════
    #  CONVERT VIEW
    # ══════════════════════════════════════════
    def _build_convert_view(self, parent):
        # Title of view
        title_row = ctk.CTkFrame(parent, fg_color="transparent")
        title_row.pack(fill="x", padx=12, pady=(4, 12))
        
        ctk.CTkLabel(
            title_row,
            text="Local Media Converter",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLOR_TEXT_TITLE,
        ).pack(side="left")

        # ── File picker panel ──
        panel = ctk.CTkFrame(parent, corner_radius=12, fg_color=COLOR_BG_PANEL, border_color=COLOR_BORDER, border_width=1)
        panel.pack(fill="x", padx=4, pady=(0, 12))

        # File list header
        file_header = ctk.CTkFrame(panel, fg_color="transparent")
        file_header.pack(fill="x", padx=16, pady=(16, 6))

        ctk.CTkLabel(
            file_header, text="Selected Files",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        ).pack(side="left")

        for label, color, hover, cmd in [
            ("＋ Add Files",  COLOR_INDIGO, COLOR_INDIGO_HOVER, self._cv_pick_files),
            ("✕ Clear All",  COLOR_MUTED, COLOR_MUTED_HOVER, self._cv_clear_pending),
        ]:
            ctk.CTkButton(
                file_header, text=label, width=100, height=28,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color=color, hover_color=hover, text_color="#FFFFFF" if color == COLOR_INDIGO else COLOR_TEXT_TITLE,
                command=cmd, corner_radius=6
            ).pack(side="right", padx=(6, 0))

        # Scrollable pending file list
        self._cv_file_scroll = ctk.CTkScrollableFrame(
            panel, height=100, corner_radius=8, fg_color=COLOR_BG_MAIN, border_color=COLOR_BORDER, border_width=1,
            scrollbar_button_color=COLOR_MUTED, scrollbar_button_hover_color=COLOR_MUTED_HOVER,
        )
        self._cv_file_scroll.pack(fill="x", padx=16, pady=(0, 10))

        self._cv_file_empty = ctk.CTkLabel(
            self._cv_file_scroll,
            text="No files added yet. Click '＋ Add Files' to select media files.",
            font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MUTED,
        )
        self._cv_file_empty.pack(pady=24)

        # Format selection row
        fmt_row = ctk.CTkFrame(panel, fg_color="transparent")
        fmt_row.pack(fill="x", padx=16, pady=(0, 8))

        # Format group toggle
        self._cv_fmt_group = ctk.StringVar(value="Audio")
        grp_frame = ctk.CTkFrame(fmt_row, fg_color="transparent")
        grp_frame.pack(side="left", padx=(0, 20))
        for g in ("Video", "Audio"):
            ctk.CTkRadioButton(
                grp_frame, text=g, value=g,
                variable=self._cv_fmt_group, command=self._on_cv_group_change,
                font=ctk.CTkFont(size=13), radiobutton_width=16, radiobutton_height=16,
                fg_color=COLOR_INDIGO, hover_color=COLOR_INDIGO_HOVER,
                text_color=COLOR_TEXT_TITLE
            ).pack(side="left", padx=(0, 12))

        ctk.CTkLabel(
            fmt_row, text="Convert to:", font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_MUTED
        ).pack(side="left")
        
        self._cv_fmt_var = ctk.StringVar(value="MP3 (320k)")
        self._cv_fmt_menu = ctk.CTkOptionMenu(
            fmt_row, variable=self._cv_fmt_var,
            values=CONVERT_FORMAT_GROUPS["Audio"], width=160,
            font=ctk.CTkFont(size=13),
            fg_color=COLOR_BG_MAIN, button_color=COLOR_MUTED, button_hover_color=COLOR_MUTED_HOVER,
            text_color=COLOR_TEXT_TITLE,
            dropdown_fg_color=COLOR_BG_MAIN, dropdown_text_color=COLOR_TEXT_TITLE,
            dropdown_hover_color=COLOR_MUTED
        )
        self._cv_fmt_menu.pack(side="left", padx=(8, 0))

        # Output dir
        out_row = ctk.CTkFrame(panel, fg_color="transparent")
        out_row.pack(fill="x", padx=16, pady=(4, 16))

        ctk.CTkLabel(
            out_row, text="Save to", width=54,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
            anchor="w"
        ).pack(side="left")

        self._cv_out_var = ctk.StringVar(value=self._settings["convert_dir"])
        
        cv_out_entry = ctk.CTkEntry(
            out_row, textvariable=self._cv_out_var, font=ctk.CTkFont(size=13),
            fg_color=COLOR_BG_MAIN, border_color=COLOR_BORDER,
            text_color=COLOR_TEXT_TITLE, corner_radius=8
        )
        cv_out_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        
        ctk.CTkButton(
            out_row, text="Browse", width=80,
            command=lambda: self._browse_dir(self._cv_out_var),
            fg_color=COLOR_MUTED, hover_color=COLOR_MUTED_HOVER,
            text_color=COLOR_TEXT_TITLE, font=ctk.CTkFont(size=13),
            corner_radius=8
        ).pack(side="left")

        # ── Action buttons ──
        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill="x", padx=4, pady=(0, 8))

        actions = [
            ("▶ Convert All", COLOR_EMERALD, COLOR_EMERALD_HOVER, "#FFFFFF", self._cv_start_all),
            ("⏹ Stop All",    COLOR_ROSE, COLOR_ROSE_HOVER, "#FFFFFF", self._cv_stop_all),
            ("🗑 Clear Done",  COLOR_MUTED, COLOR_MUTED_HOVER, COLOR_TEXT_TITLE, self._cv_clear_done),
        ]
        
        for label, color, hover, t_color, cmd in actions:
            ctk.CTkButton(
                btn_row, text=label, width=130, height=36,
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color=color, hover_color=hover, text_color=t_color,
                command=cmd, corner_radius=8
            ).pack(side="left", padx=(0, 8))

        # ── Stats ──
        stats_frame = ctk.CTkFrame(parent, fg_color="transparent")
        stats_frame.pack(fill="x", padx=6, pady=(0, 6))
        
        self._cv_stats_label = ctk.CTkLabel(
            stats_frame, text="Queue: 0  |  Converting: 0  |  Done: 0  |  Error: 0",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_MUTED,
        )
        self._cv_stats_label.pack(side="left")

        # ── Progress scroll ──
        self._cv_scroll = ctk.CTkScrollableFrame(
            parent, corner_radius=12, fg_color=COLOR_BG_PANEL, border_color=COLOR_BORDER, border_width=1,
            scrollbar_button_color=COLOR_MUTED, scrollbar_button_hover_color=COLOR_MUTED_HOVER,
        )
        self._cv_scroll.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        self._cv_empty_label = ctk.CTkLabel(
            self._cv_scroll,
            text="No active conversions.\n\nAdd media files above and click '▶ Convert All' to begin.",
            font=ctk.CTkFont(size=14), text_color=COLOR_TEXT_MUTED,
            justify="center"
        )
        self._cv_empty_label.pack(pady=80)

    # ══════════════════════════════════════════
    #  SETTINGS VIEW
    # ══════════════════════════════════════════
    def _build_settings_view(self, parent):
        # Title of view
        title_row = ctk.CTkFrame(parent, fg_color="transparent")
        title_row.pack(fill="x", padx=12, pady=(4, 16))
        
        ctk.CTkLabel(
            title_row,
            text="Application Settings",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLOR_TEXT_TITLE,
        ).pack(side="left")

        # ── Scrollable Container for Settings ──
        scroll = ctk.CTkScrollableFrame(
            parent, corner_radius=12, fg_color=COLOR_BG_PANEL, border_color=COLOR_BORDER, border_width=1,
            scrollbar_button_color=COLOR_MUTED, scrollbar_button_hover_color=COLOR_MUTED_HOVER,
        )
        scroll.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        # --- SECTION: Appearance ---
        sec_appearance = ctk.CTkFrame(scroll, fg_color="transparent")
        sec_appearance.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(
            sec_appearance, text="Appearance & Visuals",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_INDIGO
        ).pack(anchor="w", pady=(0, 8))

        row_theme = ctk.CTkFrame(sec_appearance, fg_color="transparent")
        row_theme.pack(fill="x", pady=4)
        ctk.CTkLabel(
            row_theme, text="UI Theme Mode:", font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_TITLE
        ).pack(side="left")

        self._settings_appearance_var = ctk.StringVar(value=self._settings["appearance_mode"])
        theme_menu = ctk.CTkOptionMenu(
            row_theme, variable=self._settings_appearance_var,
            values=["System", "Dark", "Light"], width=140,
            command=self._on_setting_changed,
            font=ctk.CTkFont(size=13),
            fg_color=COLOR_BG_MAIN, button_color=COLOR_MUTED, button_hover_color=COLOR_MUTED_HOVER,
            text_color=COLOR_TEXT_TITLE,
            dropdown_fg_color=COLOR_BG_MAIN, dropdown_text_color=COLOR_TEXT_TITLE,
            dropdown_hover_color=COLOR_MUTED
        )
        theme_menu.pack(side="right")

        # Divider
        ctk.CTkFrame(scroll, height=1, fg_color=COLOR_BORDER).pack(fill="x", padx=16, pady=12)

        # --- SECTION: Default Paths ---
        sec_paths = ctk.CTkFrame(scroll, fg_color="transparent")
        sec_paths.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(
            sec_paths, text="Default File Destinations",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_INDIGO
        ).pack(anchor="w", pady=(0, 8))

        # Download path row
        row_dl_path = ctk.CTkFrame(sec_paths, fg_color="transparent")
        row_dl_path.pack(fill="x", pady=6)
        ctk.CTkLabel(
            row_dl_path, text="Downloads Directory:", font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_TITLE
        ).pack(side="left")

        self._settings_dl_dir_var = ctk.StringVar(value=self._settings["download_dir"])
        
        dl_dir_entry = ctk.CTkEntry(
            row_dl_path, textvariable=self._settings_dl_dir_var, font=ctk.CTkFont(size=13),
            fg_color=COLOR_BG_MAIN, border_color=COLOR_BORDER,
            text_color=COLOR_TEXT_TITLE, corner_radius=8, width=280
        )
        dl_dir_entry.pack(side="left", fill="x", expand=True, padx=(20, 8))
        dl_dir_entry.bind("<FocusOut>", lambda e: self._on_setting_changed())
        dl_dir_entry.bind("<Return>", lambda e: self._on_setting_changed())

        ctk.CTkButton(
            row_dl_path, text="Browse", width=76,
            command=lambda: self._browse_settings_dir(self._settings_dl_dir_var),
            fg_color=COLOR_MUTED, hover_color=COLOR_MUTED_HOVER,
            text_color=COLOR_TEXT_TITLE, font=ctk.CTkFont(size=13),
            corner_radius=8
        ).pack(side="right")

        # Convert path row
        row_cv_path = ctk.CTkFrame(sec_paths, fg_color="transparent")
        row_cv_path.pack(fill="x", pady=6)
        ctk.CTkLabel(
            row_cv_path, text="Conversions Directory:", font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_TITLE
        ).pack(side="left")

        self._settings_cv_dir_var = ctk.StringVar(value=self._settings["convert_dir"])
        
        cv_dir_entry = ctk.CTkEntry(
            row_cv_path, textvariable=self._settings_cv_dir_var, font=ctk.CTkFont(size=13),
            fg_color=COLOR_BG_MAIN, border_color=COLOR_BORDER,
            text_color=COLOR_TEXT_TITLE, corner_radius=8, width=280
        )
        cv_dir_entry.pack(side="left", fill="x", expand=True, padx=(20, 8))
        cv_dir_entry.bind("<FocusOut>", lambda e: self._on_setting_changed())
        cv_dir_entry.bind("<Return>", lambda e: self._on_setting_changed())

        ctk.CTkButton(
            row_cv_path, text="Browse", width=76,
            command=lambda: self._browse_settings_dir(self._settings_cv_dir_var),
            fg_color=COLOR_MUTED, hover_color=COLOR_MUTED_HOVER,
            text_color=COLOR_TEXT_TITLE, font=ctk.CTkFont(size=13),
            corner_radius=8
        ).pack(side="right")

        # Divider
        ctk.CTkFrame(scroll, height=1, fg_color=COLOR_BORDER).pack(fill="x", padx=16, pady=12)

        # --- SECTION: Performance & Limits ---
        sec_perf = ctk.CTkFrame(scroll, fg_color="transparent")
        sec_perf.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(
            sec_perf, text="Task Limits & Quality Defaults",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_INDIGO
        ).pack(anchor="w", pady=(0, 8))

        # Default Quality row
        row_quality = ctk.CTkFrame(sec_perf, fg_color="transparent")
        row_quality.pack(fill="x", pady=6)
        ctk.CTkLabel(
            row_quality, text="Default Download Quality:", font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_TITLE
        ).pack(side="left")

        self._settings_quality_var = ctk.StringVar(value=self._settings["default_quality"])
        quality_menu = ctk.CTkOptionMenu(
            row_quality, variable=self._settings_quality_var,
            values=VIDEO_QUALITIES, width=160,
            command=self._on_setting_changed,
            font=ctk.CTkFont(size=13),
            fg_color=COLOR_BG_MAIN, button_color=COLOR_MUTED, button_hover_color=COLOR_MUTED_HOVER,
            text_color=COLOR_TEXT_TITLE,
            dropdown_fg_color=COLOR_BG_MAIN, dropdown_text_color=COLOR_TEXT_TITLE,
            dropdown_hover_color=COLOR_MUTED
        )
        quality_menu.pack(side="right")

        # Max concurrent downloads
        row_max_dl = ctk.CTkFrame(sec_perf, fg_color="transparent")
        row_max_dl.pack(fill="x", pady=8)
        ctk.CTkLabel(
            row_max_dl, text="Max Concurrent Downloads:", font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_TITLE
        ).pack(side="left")

        self._settings_max_dl_var = ctk.IntVar(value=self._settings["max_downloads"])
        
        self._settings_max_dl_lbl = ctk.CTkLabel(
            row_max_dl, text=str(self._settings["max_downloads"]),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_INDIGO, width=24
        )
        self._settings_max_dl_lbl.pack(side="right", padx=(10, 0))

        dl_slider = ctk.CTkSlider(
            row_max_dl, from_=1, to=5, number_of_steps=4,
            variable=self._settings_max_dl_var, width=150,
            command=self._on_dl_slider_change,
            fg_color=COLOR_BORDER, progress_color=COLOR_INDIGO, button_color=COLOR_INDIGO, button_hover_color=COLOR_INDIGO_HOVER
        )
        dl_slider.pack(side="right")

        # Max concurrent conversions
        row_max_cv = ctk.CTkFrame(sec_perf, fg_color="transparent")
        row_max_cv.pack(fill="x", pady=8)
        ctk.CTkLabel(
            row_max_cv, text="Max Concurrent Conversions:", font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_TITLE
        ).pack(side="left")

        self._settings_max_cv_var = ctk.IntVar(value=self._settings["max_conversions"])
        
        self._settings_max_cv_lbl = ctk.CTkLabel(
            row_max_cv, text=str(self._settings["max_conversions"]),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_INDIGO, width=24
        )
        self._settings_max_cv_lbl.pack(side="right", padx=(10, 0))

        cv_slider = ctk.CTkSlider(
            row_max_cv, from_=1, to=4, number_of_steps=3,
            variable=self._settings_max_cv_var, width=150,
            command=self._on_cv_slider_change,
            fg_color=COLOR_BORDER, progress_color=COLOR_INDIGO, button_color=COLOR_INDIGO, button_hover_color=COLOR_INDIGO_HOVER
        )
        cv_slider.pack(side="right")
        
        # Info note
        note_row = ctk.CTkFrame(scroll, fg_color="transparent")
        note_row.pack(fill="x", padx=16, pady=(20, 10))
        ctk.CTkLabel(
            note_row,
            text="Settings are saved automatically in standard config location.",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color=COLOR_TEXT_MUTED,
        ).pack(anchor="w")

    def _browse_settings_dir(self, var: ctk.StringVar):
        d = filedialog.askdirectory(initialdir=var.get())
        if d:
            var.set(d)
            self._on_setting_changed()

    # ══════════════════════════════════════════
    #  SHARED HELPERS
    # ══════════════════════════════════════════
    def _browse_dir(self, var: ctk.StringVar):
        d = filedialog.askdirectory(initialdir=var.get())
        if d:
            var.set(d)

    # ══════════════════════════════════════════
    #  DOWNLOAD — UI handlers
    # ══════════════════════════════════════════
    def _clear_url_placeholder(self, _=None):
        if self._url_entry.get("0.0", "end").strip() == "Paste one or more URLs here, one per line…":
            self._url_entry.delete("0.0", "end")

    def _restore_url_placeholder(self, _=None):
        if not self._url_entry.get("0.0", "end").strip():
            self._url_entry.insert("0.0", "Paste one or more URLs here, one per line…")

    def _on_dl_type_change(self):
        if self._dl_type.get() == "Video":
            self._dl_fmt_var.set(VIDEO_FORMATS[0])
            self._dl_fmt_menu.configure(values=VIDEO_FORMATS)
            self._quality_label.pack(side="left")
            self._quality_menu.pack(side="left", padx=(8, 0))
        else:
            self._dl_fmt_var.set(AUDIO_FORMATS[0])
            self._dl_fmt_menu.configure(values=AUDIO_FORMATS)
            self._quality_label.pack_forget()
            self._quality_menu.pack_forget()

    def _dl_paste_clipboard(self):
        try:
            text = self.clipboard_get()
            if text:
                self._clear_url_placeholder()
                self._url_entry.insert("insert", text)
        except Exception:
            messagebox.showwarning("Clipboard Error", "Could not read clipboard.")

    def _dl_add_to_queue(self):
        raw = self._url_entry.get("0.0", "end").strip()
        if not raw or raw == "Paste one or more URLs here, one per line…":
            messagebox.showwarning("No URL", "Please enter at least one URL.")
            return

        urls = [u.strip() for u in raw.splitlines() if u.strip()]
        fmt  = self._dl_fmt_var.get()
        qual = self._quality_var.get() if self._dl_type.get() == "Video" else ""
        out  = self._dl_out_var.get()

        if not os.path.isdir(out):
            messagebox.showerror("Bad Directory", f"Output folder not found:\n{out}")
            return

        for url in urls:
            item = DownloadItem(url, fmt, qual, out)
            self._dl_items.append(item)
            self._dl_queue.put(item)
            if self._dl_empty_label.winfo_ismapped():
                self._dl_empty_label.pack_forget()
            _build_queue_row(self._dl_scroll, item.title, fmt,
                             lambda i=item: self._dl_cancel(i), item)

        self._url_entry.delete("0.0", "end")
        self._dl_update_stats()

    def _dl_cancel(self, item: DownloadItem):
        item.cancelled = True
        self._ui_queue.put(("dl_status", item, "Cancelled"))

    def _dl_start_all(self):
        self._start_dl_dispatcher()

    def _dl_stop_all(self):
        for item in self._dl_items:
            if item.status in ("Queued", "Downloading"):
                self._dl_cancel(item)

    def _dl_clear_done(self):
        to_rm = [i for i in self._dl_items if i.status in ("Done", "Cancelled", "Error")]
        for item in to_rm:
            self._dl_items.remove(item)
            if item.row_frame:
                item.row_frame.destroy()
        if not self._dl_items:
            self._dl_empty_label.pack(pady=80)
        self._dl_update_stats()

    def _dl_update_stats(self):
        q  = sum(1 for i in self._dl_items if i.status == "Queued")
        dl = sum(1 for i in self._dl_items if i.status in ("Downloading", "Converting"))
        dn = sum(1 for i in self._dl_items if i.status == "Done")
        er = sum(1 for i in self._dl_items if i.status == "Error")
        self._dl_stats_label.configure(
            text=f"Queue: {q}  |  Downloading: {dl}  |  Done: {dn}  |  Error: {er}")

    # ══════════════════════════════════════════
    #  DOWNLOAD — backend
    # ══════════════════════════════════════════
    def _start_dl_dispatcher(self):
        t = threading.Thread(target=self._dl_dispatcher_loop, daemon=True)
        t.start()

    def _dl_dispatcher_loop(self):
        while self._dl_running:
            active = sum(1 for t in self._dl_threads if t.is_alive())
            if active < self._dl_max:
                try:
                    item = self._dl_queue.get_nowait()
                    if item.cancelled:
                        continue
                    t = threading.Thread(target=self._dl_worker, args=(item,), daemon=True)
                    self._dl_threads.append(t)
                    t.start()
                except queue.Empty:
                    pass
            time.sleep(0.4)

    def _dl_worker(self, item: DownloadItem):
        if item.cancelled:
            return
        self._ui_queue.put(("dl_status", item, "Downloading"))

        cfg = DOWNLOAD_FORMAT_MAP.get(item.fmt, {}).copy()
        fmt_str = cfg.get("format", "best")
        if item.quality and item.quality != "Best Available":
            q = QUALITY_MAP.get(item.quality, "")
            if q and "bestvideo" in fmt_str:
                fmt_str = fmt_str.replace("bestvideo", f"bestvideo{q}")

        ydl_opts = {
            "format":         fmt_str,
            "outtmpl":        os.path.join(item.out_dir, "%(title)s.%(ext)s"),
            "progress_hooks": [lambda d, i=item: self._dl_progress_hook(d, i)],
            "quiet":          True,
            "no_warnings":    True,
            "noplaylist":     False,
        }
        if "merge_output_format" in cfg:
            ydl_opts["merge_output_format"] = cfg["merge_output_format"]
        if "postprocessors" in cfg:
            ydl_opts["postprocessors"] = cfg["postprocessors"]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(item.url, download=False)
                title = info.get("title") or info.get("playlist_title") or item.url
                self._ui_queue.put(("dl_title", item, title[:80]))
                if item.cancelled:
                    return
                ydl.download([item.url])
            if not item.cancelled:
                self._ui_queue.put(("dl_status", item, "Done"))
                self._ui_queue.put(("dl_progress", item, 1.0, "", ""))
        except Exception as e:
            if not item.cancelled:
                self._ui_queue.put(("dl_status", item, "Error"))
                self._ui_queue.put(("dl_info", item, f"Error: {str(e)[:70]}"))
        finally:
            self._ui_queue.put(("dl_stats",))

    def _dl_progress_hook(self, d: dict, item: DownloadItem):
        if item.cancelled:
            raise yt_dlp.utils.DownloadCancelled()
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            pct   = d.get("downloaded_bytes", 0) / total if total else 0
            speed = d.get("_speed_str", "").strip()
            eta   = d.get("_eta_str", "").strip()
            self._ui_queue.put(("dl_progress", item, pct, speed, eta))
        elif d["status"] == "finished":
            self._ui_queue.put(("dl_progress", item, 1.0, "Converting…", ""))
            self._ui_queue.put(("dl_status", item, "Converting"))

    # ══════════════════════════════════════════
    #  CONVERT — UI handlers
    # ══════════════════════════════════════════
    def _on_cv_group_change(self):
        grp = self._cv_fmt_group.get()
        formats = CONVERT_FORMAT_GROUPS[grp]
        self._cv_fmt_var.set(formats[0])
        self._cv_fmt_menu.configure(values=formats)

    def _cv_pick_files(self):
        paths = filedialog.askopenfilenames(
            title="Select media files",
            filetypes=[
                ("All media", "*.mp4 *.mkv *.webm *.mov *.avi *.flv *.wmv "
                              "*.m4v *.ts *.mp3 *.aac *.flac *.wav *.ogg *.opus *.m4a"),
                ("Video files", "*.mp4 *.mkv *.webm *.mov *.avi *.flv *.wmv *.m4v *.ts"),
                ("Audio files", "*.mp3 *.aac *.flac *.wav *.ogg *.opus *.m4a"),
                ("All files",   "*.*"),
            ],
        )
        for p in paths:
            if p not in self._pending_files:
                self._pending_files.append(p)
                self._cv_add_pending_row(p)

        if self._pending_files and self._cv_file_empty.winfo_ismapped():
            self._cv_file_empty.pack_forget()

    def _cv_add_pending_row(self, path: str):
        name = Path(path).name
        row = ctk.CTkFrame(
            self._cv_file_scroll,
            fg_color="transparent",
        )
        row.pack(fill="x", pady=2, padx=4)

        # File bullet representer
        ctk.CTkLabel(
            row, text="📄", font=ctk.CTkFont(size=12),
            text_color=COLOR_INDIGO
        ).pack(side="left", padx=(4, 6))

        ctk.CTkLabel(
            row, text=name, font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT_TITLE, anchor="w"
        ).pack(side="left", fill="x")

        # Parent directory path
        ctk.CTkLabel(
            row, text=str(Path(path).parent), font=ctk.CTkFont(size=10),
            text_color=COLOR_TEXT_MUTED, anchor="e"
        ).pack(side="left", fill="x", expand=True, padx=(8, 12))

        # Close/remove button
        ctk.CTkButton(
            row, text="✕", width=24, height=22,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COLOR_MUTED, hover_color=COLOR_ROSE,
            text_color=COLOR_TEXT_TITLE,
            command=lambda p=path, r=row: self._cv_remove_pending(p, r),
            corner_radius=4
        ).pack(side="right", padx=(0, 4))

    def _cv_remove_pending(self, path: str, row_frame):
        if path in self._pending_files:
            self._pending_files.remove(path)
        row_frame.destroy()
        if not self._pending_files:
            self._cv_file_empty.pack(pady=24)

    def _cv_clear_pending(self):
        for widget in self._cv_file_scroll.winfo_children():
            if widget != self._cv_file_empty:
                widget.destroy()
        self._pending_files.clear()
        self._cv_file_empty.pack(pady=24)

    def _cv_start_all(self):
        if not self._pending_files:
            messagebox.showwarning("No files", "Add at least one file to convert.")
            return

        fmt = self._cv_fmt_var.get()
        out = self._cv_out_var.get()

        if not os.path.isdir(out):
            messagebox.showerror("Bad Directory", f"Output folder not found:\n{out}")
            return

        for path in list(self._pending_files):
            item = ConvertItem(path, fmt, out)
            self._cv_items.append(item)
            self._cv_queue.put(item)
            if self._cv_empty_label.winfo_ismapped():
                self._cv_empty_label.pack_forget()
            cfg = CONVERT_FORMAT_MAP[fmt]
            subtitle = f"{Path(path).suffix.lstrip('.').upper()}  →  {cfg['ext'].upper()}"
            _build_queue_row(self._cv_scroll, item.name, subtitle,
                             lambda i=item: self._cv_cancel(i), item)

        self._cv_clear_pending()
        self._cv_update_stats()
        self._start_cv_dispatcher()

    def _cv_cancel(self, item: ConvertItem):
        item.cancelled = True
        if item.proc and item.proc.poll() is None:
            item.proc.terminate()
        self._ui_queue.put(("cv_status", item, "Cancelled"))

    def _cv_stop_all(self):
        for item in self._cv_items:
            if item.status in ("Queued", "Converting"):
                self._cv_cancel(item)

    def _cv_clear_done(self):
        to_rm = [i for i in self._cv_items if i.status in ("Done", "Cancelled", "Error")]
        for item in to_rm:
            self._cv_items.remove(item)
            if item.row_frame:
                item.row_frame.destroy()
        if not self._cv_items:
            self._cv_empty_label.pack(pady=80)
        self._cv_update_stats()

    def _cv_update_stats(self):
        q  = sum(1 for i in self._cv_items if i.status == "Queued")
        cv = sum(1 for i in self._cv_items if i.status == "Converting")
        dn = sum(1 for i in self._cv_items if i.status == "Done")
        er = sum(1 for i in self._cv_items if i.status == "Error")
        self._cv_stats_label.configure(
            text=f"Queue: {q}  |  Converting: {cv}  |  Done: {dn}  |  Error: {er}")

    # ══════════════════════════════════════════
    #  CONVERT — backend
    # ══════════════════════════════════════════
    def _start_cv_dispatcher(self):
        t = threading.Thread(target=self._cv_dispatcher_loop, daemon=True)
        t.start()

    def _cv_dispatcher_loop(self):
        while self._cv_running:
            active = sum(1 for t in self._cv_threads if t.is_alive())
            if active < self._cv_max:
                try:
                    item = self._cv_queue.get_nowait()
                    if item.cancelled:
                        continue
                    t = threading.Thread(target=self._cv_worker, args=(item,), daemon=True)
                    self._cv_threads.append(t)
                    t.start()
                except queue.Empty:
                    pass
            time.sleep(0.4)

    def _cv_worker(self, item: ConvertItem):
        if item.cancelled:
            return

        self._ui_queue.put(("cv_status", item, "Converting"))

        cfg      = CONVERT_FORMAT_MAP[item.fmt]
        out_name = Path(item.input_path).stem + "." + cfg["ext"]
        out_path = os.path.join(item.out_dir, out_name)

        # Avoid overwriting the source if same path
        if os.path.abspath(out_path) == os.path.abspath(item.input_path):
            out_path = os.path.join(
                item.out_dir,
                Path(item.input_path).stem + "_converted." + cfg["ext"],
            )

        duration = _get_duration(item.input_path)

        cmd = (
            ["ffmpeg", "-y", "-i", item.input_path]
            + cfg["args"]
            + ["-progress", "pipe:1", "-nostats", out_path]
        )

        try:
            item.proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1,
            )

            for line in item.proc.stdout:
                if item.cancelled:
                    break
                line = line.strip()
                if line.startswith("out_time_ms="):
                    try:
                        ms  = int(line.split("=", 1)[1])
                        pct = min(ms / 1_000_000 / duration, 1.0) if duration > 0 else 0
                        self._ui_queue.put(("cv_progress", item, pct))
                    except ValueError:
                        pass

            item.proc.wait()
            rc = item.proc.returncode

            if item.cancelled:
                # Clean up partial output
                if os.path.exists(out_path):
                    os.remove(out_path)
                return

            if rc == 0:
                self._ui_queue.put(("cv_status", item, "Done"))
                self._ui_queue.put(("cv_progress", item, 1.0))
                self._ui_queue.put(("cv_info", item, f"→ {out_name}"))
            else:
                stderr = item.proc.stderr.read()
                self._ui_queue.put(("cv_status", item, "Error"))
                self._ui_queue.put(("cv_info", item, f"ffmpeg error (code {rc})"))

        except Exception as e:
            if not item.cancelled:
                self._ui_queue.put(("cv_status", item, "Error"))
                self._ui_queue.put(("cv_info", item, str(e)[:70]))
        finally:
            self._ui_queue.put(("cv_stats",))

    # ══════════════════════════════════════════
    #  SHARED UI POLL (runs on main thread)
    # ══════════════════════════════════════════
    def _poll_ui_queue(self):
        try:
            while True:
                msg  = self._ui_queue.get_nowait()
                kind = msg[0]

                # ── Download messages ──
                if kind == "dl_status":
                    _, item, status = msg
                    self._apply_status(item, status)
                    self._dl_update_stats()

                elif kind == "dl_progress":
                    _, item, pct, speed, eta = msg
                    if item.progress_bar:
                        item.progress_bar.set(pct)
                    if item.info_label:
                        parts = [p for p in [speed, f"ETA {eta}" if eta else "", f"{pct*100:.1f}%" if 0 < pct < 1 else ""] if p]
                        item.info_label.configure(text="  ".join(parts))

                elif kind == "dl_title":
                    _, item, title = msg
                    if item.title_label:
                        item.title_label.configure(text=title)

                elif kind == "dl_info":
                    _, item, text = msg
                    if item.info_label:
                        item.info_label.configure(text=text)

                elif kind == "dl_stats":
                    self._dl_update_stats()

                # ── Convert messages ──
                elif kind == "cv_status":
                    _, item, status = msg
                    self._apply_status(item, status)
                    self._cv_update_stats()

                elif kind == "cv_progress":
                    _, item, pct = msg
                    if item.progress_bar:
                        item.progress_bar.set(pct)
                    if item.info_label and 0 < pct < 1:
                        item.info_label.configure(text=f"{pct*100:.1f}%")

                elif kind == "cv_info":
                    _, item, text = msg
                    if item.info_label:
                        item.info_label.configure(text=text)

                elif kind == "cv_stats":
                    self._cv_update_stats()

        except queue.Empty:
            pass
        self.after(100, self._poll_ui_queue)

    def _apply_status(self, item, status: str):
        item.status = status
        # Get badge color configuration
        badge_cfg = BADGE_COLORS.get(status, BADGE_COLORS["Queued"])
        
        if item.status_label:
            item.status_label.configure(
                text=status.upper(),
                fg_color=badge_cfg["bg"],
                text_color=badge_cfg["fg"]
            )
        if status in ("Done", "Error", "Cancelled") and item.cancel_btn:
            item.cancel_btn.configure(state="disabled")
            
        if item.progress_bar:
            if status == "Done":
                item.progress_bar.configure(progress_color=COLOR_EMERALD)
                item.progress_bar.set(1.0)
            elif status == "Error":
                item.progress_bar.configure(progress_color=COLOR_ROSE)
            elif status == "Cancelled":
                item.progress_bar.configure(progress_color=STATUS_COLORS["Cancelled"])

    # ══════════════════════════════════════════
    #  CLOSE
    # ══════════════════════════════════════════
    def _on_close(self):
        self._dl_running = False
        self._cv_running = False
        for item in self._dl_items:
            item.cancelled = True
        for item in self._cv_items:
            item.cancelled = True
            if item.proc and item.proc.poll() is None:
                item.proc.terminate()
        self.destroy()


# ──────────────────────────────────────────────
#  Entry point
# ──────────────────────────────────────────────
def main():
    missing = []
    for tool in ("ffmpeg", "ffprobe"):
        try:
            subprocess.run([tool, "-version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            missing.append(tool)

    if missing:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            "Missing system tools",
            f"{' and '.join(missing)} not found on your PATH.\n\n"
            "Install via:\n"
            "  macOS:   brew install ffmpeg\n"
            "  Ubuntu:  sudo apt install ffmpeg\n"
            "  Windows: https://ffmpeg.org/download.html\n\n"
            "The app will still open but conversion/merging will fail.",
        )
        root.destroy()

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
