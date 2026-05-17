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
from pathlib import Path
from tkinter import filedialog, messagebox
import yt_dlp

# ──────────────────────────────────────────────
#  Theme
# ──────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

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

STATUS_COLORS = {
    "Queued":      "#6B7280",
    "Downloading": "#3B82F6",
    "Converting":  "#F59E0B",
    "Done":        "#10B981",
    "Error":       "#EF4444",
    "Cancelled":   "#9CA3AF",
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
    row = ctk.CTkFrame(parent, corner_radius=8,
                        fg_color="#111827", border_color="#1F2937", border_width=1)
    row.pack(fill="x", pady=3, padx=2)
    item.row_frame = row

    left = ctk.CTkFrame(row, fg_color="transparent")
    left.pack(side="left", fill="both", expand=True, padx=(12, 6), pady=8)

    item.title_label = ctk.CTkLabel(left, text=title,
                                     font=ctk.CTkFont(size=13, weight="bold"),
                                     text_color="#E5E7EB", anchor="w")
    item.title_label.pack(fill="x")

    ctk.CTkLabel(left, text=subtitle, font=ctk.CTkFont(size=11),
                 text_color="#6B7280", anchor="w").pack(fill="x")

    item.progress_bar = ctk.CTkProgressBar(left, height=6, corner_radius=3,
                                             progress_color="#2563EB", fg_color="#1F2937")
    item.progress_bar.set(0)
    item.progress_bar.pack(fill="x", pady=(6, 2))

    meta = ctk.CTkFrame(left, fg_color="transparent")
    meta.pack(fill="x")
    item.info_label = ctk.CTkLabel(meta, text="", font=ctk.CTkFont(size=11),
                                    text_color="#6B7280", anchor="w")
    item.info_label.pack(side="left")

    right = ctk.CTkFrame(row, fg_color="transparent", width=120)
    right.pack(side="right", padx=(6, 12), pady=8)
    right.pack_propagate(False)

    item.status_label = ctk.CTkLabel(right, text="Queued",
                                      font=ctk.CTkFont(size=12, weight="bold"),
                                      text_color=STATUS_COLORS["Queued"],
                                      width=80, anchor="e")
    item.status_label.pack(anchor="e")

    item.cancel_btn = ctk.CTkButton(right, text="✕ Cancel", width=80, height=26,
                                      font=ctk.CTkFont(size=11),
                                      fg_color="#374151", hover_color="#DC2626",
                                      command=on_cancel)
    item.cancel_btn.pack(anchor="e", pady=(4, 0))

    # alias so download code (which uses .speed_label) still works
    item.speed_label = item.info_label


# ──────────────────────────────────────────────
#  Main Application
# ──────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("YT-DLPx")
        self.geometry("980x740")
        self.minsize(820, 600)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Download state
        self._dl_queue: "queue.Queue[DownloadItem]" = queue.Queue()
        self._dl_items: list[DownloadItem] = []
        self._dl_threads: list[threading.Thread] = []
        self._dl_max = 2
        self._dl_running = True

        # Convert state
        self._cv_queue: "queue.Queue[ConvertItem]" = queue.Queue()
        self._cv_items: list[ConvertItem] = []
        self._cv_threads: list[threading.Thread] = []
        self._cv_max = 2
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
    #  TOP-LEVEL UI
    # ══════════════════════════════════════════
    def _build_ui(self):
        # ── App header ──
        header = ctk.CTkFrame(self, fg_color=("#0F0F1A", "#0F0F1A"), corner_radius=0, height=58)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="  YT-DLPx",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#60A5FA",
        ).pack(side="left", padx=20, pady=10)

        ctk.CTkLabel(
            header,
            text="Downloader & Converter",
            font=ctk.CTkFont(size=13),
            text_color="#4B5563",
        ).pack(side="left", pady=10)

        # ── Tabs ──
        self._tabs = ctk.CTkTabview(
            self,
            fg_color=("#1E1E2E", "#1E1E2E"),
            segmented_button_fg_color=("#111827", "#111827"),
            segmented_button_selected_color="#2563EB",
            segmented_button_selected_hover_color="#1D4ED8",
            segmented_button_unselected_color=("#111827", "#111827"),
            segmented_button_unselected_hover_color="#1F2937",
            text_color="#E5E7EB",
            text_color_disabled="#4B5563",
        )
        self._tabs.pack(fill="both", expand=True, padx=12, pady=(8, 12))

        self._tabs.add("⬇  Download")
        self._tabs.add("🔄  Convert")

        self._build_download_tab(self._tabs.tab("⬇  Download"))
        self._build_convert_tab(self._tabs.tab("🔄  Convert"))

    # ══════════════════════════════════════════
    #  DOWNLOAD TAB
    # ══════════════════════════════════════════
    def _build_download_tab(self, parent):
        # ── Input panel ──
        panel = ctk.CTkFrame(parent, corner_radius=10, fg_color="#111827")
        panel.pack(fill="x", padx=4, pady=(8, 6))

        # URL
        url_row = ctk.CTkFrame(panel, fg_color="transparent")
        url_row.pack(fill="x", padx=12, pady=(12, 6))

        ctk.CTkLabel(url_row, text="URL(s)", width=64,
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#9CA3AF").pack(side="left")

        self._url_entry = ctk.CTkTextbox(
            url_row, height=58, font=ctk.CTkFont(size=13),
            fg_color="#1F2937", border_color="#374151", border_width=1, corner_radius=8,
        )
        self._url_entry.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self._url_entry.insert("0.0", "Paste one or more URLs here, one per line…")
        self._url_entry.bind("<FocusIn>",  self._clear_url_placeholder)
        self._url_entry.bind("<FocusOut>", self._restore_url_placeholder)

        # Format / Quality
        opts_row = ctk.CTkFrame(panel, fg_color="transparent")
        opts_row.pack(fill="x", padx=12, pady=(0, 4))

        self._dl_type = ctk.StringVar(value="Video")
        type_frame = ctk.CTkFrame(opts_row, fg_color="transparent")
        type_frame.pack(side="left", padx=(64, 12))
        for t in ("Video", "Audio"):
            ctk.CTkRadioButton(
                type_frame, text=t, value=t,
                variable=self._dl_type, command=self._on_dl_type_change,
                font=ctk.CTkFont(size=13), radiobutton_width=16, radiobutton_height=16,
            ).pack(side="left", padx=(0, 12))

        ctk.CTkLabel(opts_row, text="Format:", font=ctk.CTkFont(size=13),
                     text_color="#9CA3AF").pack(side="left")
        self._dl_fmt_var = ctk.StringVar(value=VIDEO_FORMATS[0])
        self._dl_fmt_menu = ctk.CTkOptionMenu(
            opts_row, variable=self._dl_fmt_var, values=VIDEO_FORMATS, width=178,
            font=ctk.CTkFont(size=13),
            fg_color="#1F2937", button_color="#374151", button_hover_color="#4B5563",
        )
        self._dl_fmt_menu.pack(side="left", padx=(6, 16))

        self._quality_label = ctk.CTkLabel(opts_row, text="Quality:", font=ctk.CTkFont(size=13),
                                            text_color="#9CA3AF")
        self._quality_label.pack(side="left")
        self._quality_var = ctk.StringVar(value=VIDEO_QUALITIES[0])
        self._quality_menu = ctk.CTkOptionMenu(
            opts_row, variable=self._quality_var, values=VIDEO_QUALITIES, width=148,
            font=ctk.CTkFont(size=13),
            fg_color="#1F2937", button_color="#374151", button_hover_color="#4B5563",
        )
        self._quality_menu.pack(side="left", padx=(6, 0))

        # Concurrent slider
        ctk.CTkLabel(opts_row, text="Concurrent:", font=ctk.CTkFont(size=12),
                     text_color="#9CA3AF").pack(side="right", padx=(0, 4))
        self._dl_concurrent_var = ctk.IntVar(value=2)
        ctk.CTkSlider(
            opts_row, from_=1, to=5, number_of_steps=4,
            variable=self._dl_concurrent_var, width=90,
            command=lambda v: setattr(self, "_dl_max", int(v)),
        ).pack(side="right", padx=(0, 12))

        # Output dir
        dir_row = ctk.CTkFrame(panel, fg_color="transparent")
        dir_row.pack(fill="x", padx=12, pady=(4, 12))

        ctk.CTkLabel(dir_row, text="Save to", width=64,
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#9CA3AF").pack(side="left")

        self._dl_out_var = ctk.StringVar(value=str(Path.home() / "Downloads"))
        ctk.CTkEntry(dir_row, textvariable=self._dl_out_var, font=ctk.CTkFont(size=13),
                     fg_color="#1F2937", border_color="#374151",
                     corner_radius=8).pack(side="left", fill="x", expand=True, padx=(8, 8))
        ctk.CTkButton(dir_row, text="Browse", width=76,
                      command=lambda: self._browse_dir(self._dl_out_var),
                      fg_color="#374151", hover_color="#4B5563",
                      font=ctk.CTkFont(size=13)).pack(side="left")

        # ── Buttons ──
        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill="x", padx=4, pady=(0, 6))

        for label, color, hover, cmd in [
            ("＋  Add to Queue", "#2563EB", "#1D4ED8", self._dl_add_to_queue),
            ("▶  Start All",    "#059669", "#047857", self._dl_start_all),
            ("⏹  Stop All",     "#DC2626", "#B91C1C", self._dl_stop_all),
            ("🗑  Clear Done",   "#4B5563", "#374151", self._dl_clear_done),
        ]:
            ctk.CTkButton(btn_row, text=label, width=148, height=38,
                          font=ctk.CTkFont(size=13, weight="bold"),
                          fg_color=color, hover_color=hover,
                          command=cmd).pack(side="left", padx=(0, 8))

        # ── Stats ──
        self._dl_stats_label = ctk.CTkLabel(
            parent, text="Queue: 0  |  Downloading: 0  |  Done: 0  |  Error: 0",
            font=ctk.CTkFont(size=11), text_color="#6B7280",
        )
        self._dl_stats_label.pack(anchor="w", padx=6, pady=(0, 4))

        # ── Queue scroll ──
        self._dl_scroll = ctk.CTkScrollableFrame(
            parent, corner_radius=8, fg_color="transparent",
            scrollbar_button_color="#374151", scrollbar_button_hover_color="#4B5563",
        )
        self._dl_scroll.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        self._dl_empty_label = ctk.CTkLabel(
            self._dl_scroll,
            text="No downloads yet.\nPaste a URL above and click  ＋ Add to Queue.",
            font=ctk.CTkFont(size=14), text_color="#374151",
        )
        self._dl_empty_label.pack(pady=60)

    # ══════════════════════════════════════════
    #  CONVERT TAB
    # ══════════════════════════════════════════
    def _build_convert_tab(self, parent):
        # ── File picker panel ──
        panel = ctk.CTkFrame(parent, corner_radius=10, fg_color="#111827")
        panel.pack(fill="x", padx=4, pady=(8, 6))

        # Pending file list
        file_header = ctk.CTkFrame(panel, fg_color="transparent")
        file_header.pack(fill="x", padx=12, pady=(12, 4))

        ctk.CTkLabel(file_header, text="Files to convert",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#9CA3AF").pack(side="left")

        for label, color, hover, cmd in [
            ("＋ Add Files",  "#2563EB", "#1D4ED8", self._cv_pick_files),
            ("✕ Clear All",  "#4B5563", "#374151", self._cv_clear_pending),
        ]:
            ctk.CTkButton(file_header, text=label, width=110, height=28,
                          font=ctk.CTkFont(size=12),
                          fg_color=color, hover_color=hover,
                          command=cmd).pack(side="right", padx=(6, 0))

        # Scrollable pending file list
        self._cv_file_scroll = ctk.CTkScrollableFrame(
            panel, height=110, corner_radius=6, fg_color="#1F2937",
            scrollbar_button_color="#374151", scrollbar_button_hover_color="#4B5563",
        )
        self._cv_file_scroll.pack(fill="x", padx=12, pady=(0, 8))

        self._cv_file_empty = ctk.CTkLabel(
            self._cv_file_scroll,
            text="No files added yet. Click  ＋ Add Files  to select one or more files.",
            font=ctk.CTkFont(size=12), text_color="#4B5563",
        )
        self._cv_file_empty.pack(pady=20)

        # Format / output row
        fmt_row = ctk.CTkFrame(panel, fg_color="transparent")
        fmt_row.pack(fill="x", padx=12, pady=(0, 4))

        # Format group toggle
        self._cv_fmt_group = ctk.StringVar(value="Audio")
        grp_frame = ctk.CTkFrame(fmt_row, fg_color="transparent")
        grp_frame.pack(side="left", padx=(0, 12))
        for g in ("Video", "Audio"):
            ctk.CTkRadioButton(
                grp_frame, text=g, value=g,
                variable=self._cv_fmt_group, command=self._on_cv_group_change,
                font=ctk.CTkFont(size=13), radiobutton_width=16, radiobutton_height=16,
            ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(fmt_row, text="Output format:", font=ctk.CTkFont(size=13),
                     text_color="#9CA3AF").pack(side="left")
        self._cv_fmt_var = ctk.StringVar(value="MP3 (320k)")
        self._cv_fmt_menu = ctk.CTkOptionMenu(
            fmt_row, variable=self._cv_fmt_var,
            values=CONVERT_FORMAT_GROUPS["Audio"], width=160,
            font=ctk.CTkFont(size=13),
            fg_color="#1F2937", button_color="#374151", button_hover_color="#4B5563",
        )
        self._cv_fmt_menu.pack(side="left", padx=(6, 0))

        # Concurrent slider
        ctk.CTkLabel(fmt_row, text="Concurrent:", font=ctk.CTkFont(size=12),
                     text_color="#9CA3AF").pack(side="right", padx=(0, 4))
        self._cv_concurrent_var = ctk.IntVar(value=2)
        ctk.CTkSlider(
            fmt_row, from_=1, to=4, number_of_steps=3,
            variable=self._cv_concurrent_var, width=90,
            command=lambda v: setattr(self, "_cv_max", int(v)),
        ).pack(side="right", padx=(0, 12))

        # Output dir
        out_row = ctk.CTkFrame(panel, fg_color="transparent")
        out_row.pack(fill="x", padx=12, pady=(4, 12))

        ctk.CTkLabel(out_row, text="Save to", width=64,
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#9CA3AF").pack(side="left")

        self._cv_out_var = ctk.StringVar(value=str(Path.home() / "Downloads"))
        ctk.CTkEntry(out_row, textvariable=self._cv_out_var, font=ctk.CTkFont(size=13),
                     fg_color="#1F2937", border_color="#374151",
                     corner_radius=8).pack(side="left", fill="x", expand=True, padx=(8, 8))
        ctk.CTkButton(out_row, text="Browse", width=76,
                      command=lambda: self._browse_dir(self._cv_out_var),
                      fg_color="#374151", hover_color="#4B5563",
                      font=ctk.CTkFont(size=13)).pack(side="left")

        # ── Action buttons ──
        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill="x", padx=4, pady=(0, 6))

        for label, color, hover, cmd in [
            ("▶  Convert All",  "#059669", "#047857", self._cv_start_all),
            ("⏹  Stop All",     "#DC2626", "#B91C1C", self._cv_stop_all),
            ("🗑  Clear Done",   "#4B5563", "#374151", self._cv_clear_done),
        ]:
            ctk.CTkButton(btn_row, text=label, width=148, height=38,
                          font=ctk.CTkFont(size=13, weight="bold"),
                          fg_color=color, hover_color=hover,
                          command=cmd).pack(side="left", padx=(0, 8))

        # ── Stats ──
        self._cv_stats_label = ctk.CTkLabel(
            parent, text="Queue: 0  |  Converting: 0  |  Done: 0  |  Error: 0",
            font=ctk.CTkFont(size=11), text_color="#6B7280",
        )
        self._cv_stats_label.pack(anchor="w", padx=6, pady=(0, 4))

        # ── Progress scroll ──
        self._cv_scroll = ctk.CTkScrollableFrame(
            parent, corner_radius=8, fg_color="transparent",
            scrollbar_button_color="#374151", scrollbar_button_hover_color="#4B5563",
        )
        self._cv_scroll.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        self._cv_empty_label = ctk.CTkLabel(
            self._cv_scroll,
            text="No conversions yet.\nAdd files above, choose a format, then click  ▶ Convert All.",
            font=ctk.CTkFont(size=14), text_color="#374151",
        )
        self._cv_empty_label.pack(pady=60)

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
            self._quality_menu.pack(side="left", padx=(6, 0))
        else:
            self._dl_fmt_var.set(AUDIO_FORMATS[0])
            self._dl_fmt_menu.configure(values=AUDIO_FORMATS)
            self._quality_label.pack_forget()
            self._quality_menu.pack_forget()

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
            self._dl_empty_label.pack(pady=60)
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
        row = ctk.CTkFrame(self._cv_file_scroll, fg_color="transparent")
        row.pack(fill="x", pady=1)

        ctk.CTkLabel(row, text=f"  {name}", font=ctk.CTkFont(size=12),
                     text_color="#D1D5DB", anchor="w").pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(row, text=str(Path(path).parent), font=ctk.CTkFont(size=10),
                     text_color="#6B7280", anchor="e").pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            row, text="✕", width=28, height=22,
            font=ctk.CTkFont(size=11), fg_color="#374151", hover_color="#DC2626",
            command=lambda p=path, r=row: self._cv_remove_pending(p, r),
        ).pack(side="right", padx=(0, 4))

    def _cv_remove_pending(self, path: str, row_frame):
        if path in self._pending_files:
            self._pending_files.remove(path)
        row_frame.destroy()
        if not self._pending_files:
            self._cv_file_empty.pack(pady=20)

    def _cv_clear_pending(self):
        for widget in self._cv_file_scroll.winfo_children():
            if widget != self._cv_file_empty:
                widget.destroy()
        self._pending_files.clear()
        self._cv_file_empty.pack(pady=20)

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
            self._cv_empty_label.pack(pady=60)
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
        color = STATUS_COLORS.get(status, "#9CA3AF")
        if item.status_label:
            item.status_label.configure(text=status, text_color=color)
        if status in ("Done", "Error", "Cancelled") and item.cancel_btn:
            item.cancel_btn.configure(state="disabled")
        if item.progress_bar:
            if status == "Done":
                item.progress_bar.configure(progress_color="#10B981")
                item.progress_bar.set(1.0)
            elif status == "Error":
                item.progress_bar.configure(progress_color="#EF4444")
            elif status == "Cancelled":
                item.progress_bar.configure(progress_color="#9CA3AF")

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
