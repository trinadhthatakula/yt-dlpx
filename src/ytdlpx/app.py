"""
YT-DLP Downloader — Modern Desktop App
Requires: customtkinter, yt-dlp, Pillow, ffmpeg (system)
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
#  Constants
# ──────────────────────────────────────────────
VIDEO_FORMATS   = ["MP4 (H.264)", "MKV (Best)", "WEBM (VP9)", "MP4 (Best Quality)"]
AUDIO_FORMATS   = ["MP3 (320k)", "MP3 (192k)", "AAC (Best)", "FLAC (Lossless)", "WAV", "OGG"]
VIDEO_QUALITIES = ["Best Available", "4K (2160p)", "1080p", "720p", "480p", "360p", "240p"]

FORMAT_MAP = {
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

STATUS_COLORS = {
    "Queued":      "#6B7280",
    "Downloading": "#3B82F6",
    "Converting":  "#F59E0B",
    "Done":        "#10B981",
    "Error":       "#EF4444",
    "Cancelled":   "#9CA3AF",
}


# ──────────────────────────────────────────────
#  Download Item (data model)
# ──────────────────────────────────────────────
class DownloadItem:
    def __init__(self, url: str, fmt: str, quality: str, out_dir: str):
        self.url       = url.strip()
        self.fmt       = fmt
        self.quality   = quality
        self.out_dir   = out_dir
        self.status    = "Queued"
        self.progress  = 0.0
        self.speed     = ""
        self.eta       = ""
        self.title     = url[:60] + "…" if len(url) > 60 else url
        self.cancelled = False
        # UI widgets assigned after row creation
        self.title_label  = None
        self.status_label = None
        self.progress_bar = None
        self.speed_label  = None
        self.cancel_btn   = None
        self.row_frame    = None


# ──────────────────────────────────────────────
#  Main Application
# ──────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("YT-DLP Downloader")
        self.geometry("960x700")
        self.minsize(800, 580)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._dl_queue: "queue.Queue[DownloadItem]" = queue.Queue()
        self._items: list[DownloadItem] = []
        self._active_threads: list[threading.Thread] = []
        self._max_concurrent = 2
        self._running = True
        self._ui_queue: "queue.Queue" = queue.Queue()

        self._build_ui()
        self._start_dispatcher()
        self._poll_ui_queue()

    # ──────────────────────────────────────────
    #  UI Construction
    # ──────────────────────────────────────────
    def _build_ui(self):
        # ── Header ──
        header = ctk.CTkFrame(self, fg_color=("#1A1A2E", "#0F0F1A"), corner_radius=0, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="  ⬇  YT-DLP Downloader",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#60A5FA",
        ).pack(side="left", padx=20, pady=12)

        self._concurrent_var = ctk.IntVar(value=2)
        ctk.CTkLabel(header, text="Concurrent:", font=ctk.CTkFont(size=12), text_color="#9CA3AF").pack(side="right", padx=(0, 4))
        ctk.CTkSlider(
            header, from_=1, to=5, number_of_steps=4,
            variable=self._concurrent_var, width=100,
            command=lambda v: setattr(self, "_max_concurrent", int(v)),
        ).pack(side="right", padx=(0, 16))

        # ── Input Panel ──
        panel = ctk.CTkFrame(self, corner_radius=12, fg_color=("#1E1E2E", "#1E1E2E"))
        panel.pack(fill="x", padx=16, pady=(12, 6))

        # Row 1 — URL
        url_row = ctk.CTkFrame(panel, fg_color="transparent")
        url_row.pack(fill="x", padx=12, pady=(12, 6))

        ctk.CTkLabel(url_row, text="URL(s)", width=70,
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#9CA3AF").pack(side="left")

        self._url_entry = ctk.CTkTextbox(
            url_row, height=60, font=ctk.CTkFont(size=13),
            fg_color="#111827", border_color="#374151", border_width=1, corner_radius=8,
        )
        self._url_entry.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self._url_entry.insert("0.0", "Paste one or more URLs here, one per line…")
        self._url_entry.bind("<FocusIn>",  self._clear_placeholder)
        self._url_entry.bind("<FocusOut>", self._restore_placeholder)

        # Row 2 — Format / Quality
        opts_row = ctk.CTkFrame(panel, fg_color="transparent")
        opts_row.pack(fill="x", padx=12, pady=(0, 4))

        self._dl_type = ctk.StringVar(value="Video")
        type_frame = ctk.CTkFrame(opts_row, fg_color="transparent")
        type_frame.pack(side="left", padx=(70, 12))
        for t in ("Video", "Audio"):
            ctk.CTkRadioButton(
                type_frame, text=t, value=t,
                variable=self._dl_type,
                command=self._on_type_change,
                font=ctk.CTkFont(size=13),
                radiobutton_width=16, radiobutton_height=16,
            ).pack(side="left", padx=(0, 12))

        ctk.CTkLabel(opts_row, text="Format:", font=ctk.CTkFont(size=13), text_color="#9CA3AF").pack(side="left")
        self._fmt_var = ctk.StringVar(value=VIDEO_FORMATS[0])
        self._fmt_menu = ctk.CTkOptionMenu(
            opts_row, variable=self._fmt_var,
            values=VIDEO_FORMATS, width=180,
            font=ctk.CTkFont(size=13),
            fg_color="#1F2937", button_color="#374151", button_hover_color="#4B5563",
        )
        self._fmt_menu.pack(side="left", padx=(6, 16))

        self._quality_label = ctk.CTkLabel(opts_row, text="Quality:", font=ctk.CTkFont(size=13), text_color="#9CA3AF")
        self._quality_label.pack(side="left")
        self._quality_var = ctk.StringVar(value=VIDEO_QUALITIES[0])
        self._quality_menu = ctk.CTkOptionMenu(
            opts_row, variable=self._quality_var,
            values=VIDEO_QUALITIES, width=150,
            font=ctk.CTkFont(size=13),
            fg_color="#1F2937", button_color="#374151", button_hover_color="#4B5563",
        )
        self._quality_menu.pack(side="left", padx=(6, 0))

        # Row 3 — Output dir
        dir_row = ctk.CTkFrame(panel, fg_color="transparent")
        dir_row.pack(fill="x", padx=12, pady=(4, 12))

        ctk.CTkLabel(dir_row, text="Save to", width=70,
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#9CA3AF").pack(side="left")

        default_dir = str(Path.home() / "Downloads")
        self._out_var = ctk.StringVar(value=default_dir)
        ctk.CTkEntry(
            dir_row, textvariable=self._out_var,
            font=ctk.CTkFont(size=13),
            fg_color="#111827", border_color="#374151", corner_radius=8,
        ).pack(side="left", fill="x", expand=True, padx=(8, 8))
        ctk.CTkButton(dir_row, text="Browse", width=80,
                      command=self._browse_dir,
                      fg_color="#374151", hover_color="#4B5563",
                      font=ctk.CTkFont(size=13)).pack(side="left")

        # ── Action Buttons ──
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkButton(
            btn_row, text="＋  Add to Queue", width=160, height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2563EB", hover_color="#1D4ED8",
            command=self._add_to_queue,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_row, text="▶  Start All", width=130, height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#059669", hover_color="#047857",
            command=self._start_all,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_row, text="⏹  Stop All", width=130, height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#DC2626", hover_color="#B91C1C",
            command=self._stop_all,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_row, text="🗑  Clear Done", width=130, height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#4B5563", hover_color="#374151",
            command=self._clear_done,
        ).pack(side="left")

        # ── Stats bar ──
        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.pack(fill="x", padx=16, pady=(0, 4))
        self._stats_label = ctk.CTkLabel(
            stats, text="Queue: 0  |  Downloading: 0  |  Done: 0  |  Error: 0",
            font=ctk.CTkFont(size=12), text_color="#6B7280",
        )
        self._stats_label.pack(side="left")

        # ── Queue Scroll Area ──
        queue_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=("#1E1E2E", "#1E1E2E"))
        queue_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self._scroll = ctk.CTkScrollableFrame(
            queue_frame, corner_radius=8, fg_color="transparent",
            scrollbar_button_color="#374151", scrollbar_button_hover_color="#4B5563",
        )
        self._scroll.pack(fill="both", expand=True, padx=4, pady=4)

        self._empty_label = ctk.CTkLabel(
            self._scroll,
            text="No downloads yet.\nPaste a URL above and click  ＋ Add to Queue.",
            font=ctk.CTkFont(size=14), text_color="#4B5563",
        )
        self._empty_label.pack(pady=60)

    # ──────────────────────────────────────────
    #  Helpers
    # ──────────────────────────────────────────
    def _clear_placeholder(self, _event=None):
        if self._url_entry.get("0.0", "end").strip() == "Paste one or more URLs here, one per line…":
            self._url_entry.delete("0.0", "end")

    def _restore_placeholder(self, _event=None):
        if not self._url_entry.get("0.0", "end").strip():
            self._url_entry.insert("0.0", "Paste one or more URLs here, one per line…")

    def _on_type_change(self):
        if self._dl_type.get() == "Video":
            self._fmt_var.set(VIDEO_FORMATS[0])
            self._fmt_menu.configure(values=VIDEO_FORMATS)
            self._quality_label.pack(side="left")
            self._quality_menu.pack(side="left", padx=(6, 0))
        else:
            self._fmt_var.set(AUDIO_FORMATS[0])
            self._fmt_menu.configure(values=AUDIO_FORMATS)
            self._quality_label.pack_forget()
            self._quality_menu.pack_forget()

    def _browse_dir(self):
        d = filedialog.askdirectory(initialdir=self._out_var.get())
        if d:
            self._out_var.set(d)

    # ──────────────────────────────────────────
    #  Queue Management
    # ──────────────────────────────────────────
    def _add_to_queue(self):
        raw = self._url_entry.get("0.0", "end").strip()
        if not raw or raw == "Paste one or more URLs here, one per line…":
            messagebox.showwarning("No URL", "Please enter at least one URL.")
            return

        urls = [u.strip() for u in raw.splitlines() if u.strip()]
        fmt  = self._fmt_var.get()
        qual = self._quality_var.get() if self._dl_type.get() == "Video" else ""
        out  = self._out_var.get()

        if not os.path.isdir(out):
            messagebox.showerror("Bad Directory", f"Output directory not found:\n{out}")
            return

        for url in urls:
            item = DownloadItem(url, fmt, qual, out)
            self._items.append(item)
            self._dl_queue.put(item)
            self._add_item_row(item)

        self._url_entry.delete("0.0", "end")
        self._update_stats()

    def _add_item_row(self, item: DownloadItem):
        if self._empty_label.winfo_ismapped():
            self._empty_label.pack_forget()

        row = ctk.CTkFrame(self._scroll, corner_radius=8,
                            fg_color="#111827", border_color="#1F2937", border_width=1)
        row.pack(fill="x", pady=3, padx=2)
        item.row_frame = row

        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(12, 6), pady=8)

        item.title_label = ctk.CTkLabel(left, text=item.title,
                                         font=ctk.CTkFont(size=13, weight="bold"),
                                         text_color="#E5E7EB", anchor="w")
        item.title_label.pack(fill="x")

        fmt_txt = f"{item.fmt}  •  {item.quality}" if item.quality else item.fmt
        ctk.CTkLabel(left, text=fmt_txt, font=ctk.CTkFont(size=11),
                     text_color="#6B7280", anchor="w").pack(fill="x")

        item.progress_bar = ctk.CTkProgressBar(left, height=6, corner_radius=3,
                                                 progress_color="#2563EB", fg_color="#1F2937")
        item.progress_bar.set(0)
        item.progress_bar.pack(fill="x", pady=(6, 2))

        meta = ctk.CTkFrame(left, fg_color="transparent")
        meta.pack(fill="x")
        item.speed_label = ctk.CTkLabel(meta, text="", font=ctk.CTkFont(size=11),
                                          text_color="#6B7280", anchor="w")
        item.speed_label.pack(side="left")

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
                                          command=lambda i=item: self._cancel_item(i))
        item.cancel_btn.pack(anchor="e", pady=(4, 0))

    def _cancel_item(self, item: DownloadItem):
        item.cancelled = True
        self._set_status(item, "Cancelled")

    def _start_all(self):
        self._start_dispatcher()

    def _stop_all(self):
        for item in self._items:
            if item.status in ("Queued", "Downloading"):
                item.cancelled = True
                self._set_status(item, "Cancelled")

    def _clear_done(self):
        to_remove = [i for i in self._items if i.status in ("Done", "Cancelled", "Error")]
        for item in to_remove:
            self._items.remove(item)
            if item.row_frame:
                item.row_frame.destroy()
        if not self._items:
            self._empty_label.pack(pady=60)
        self._update_stats()

    # ──────────────────────────────────────────
    #  Download Dispatcher
    # ──────────────────────────────────────────
    def _start_dispatcher(self):
        t = threading.Thread(target=self._dispatcher_loop, daemon=True)
        t.start()

    def _dispatcher_loop(self):
        while self._running:
            active = sum(1 for t in self._active_threads if t.is_alive())
            if active < self._max_concurrent:
                try:
                    item = self._dl_queue.get_nowait()
                    if item.cancelled:
                        continue
                    t = threading.Thread(target=self._download, args=(item,), daemon=True)
                    self._active_threads.append(t)
                    t.start()
                except queue.Empty:
                    pass
            time.sleep(0.4)

    # ──────────────────────────────────────────
    #  Download Logic
    # ──────────────────────────────────────────
    def _download(self, item: DownloadItem):
        if item.cancelled:
            return

        self._set_status(item, "Downloading")

        cfg = FORMAT_MAP.get(item.fmt, {}).copy()
        fmt_str = cfg.get("format", "best")

        if item.quality and item.quality != "Best Available":
            q = QUALITY_MAP.get(item.quality, "")
            if q and "bestvideo" in fmt_str:
                fmt_str = fmt_str.replace("bestvideo", f"bestvideo{q}")

        ydl_opts = {
            "format":         fmt_str,
            "outtmpl":        os.path.join(item.out_dir, "%(title)s.%(ext)s"),
            "progress_hooks": [lambda d, i=item: self._progress_hook(d, i)],
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
                self._ui_queue.put(("title", item, title[:80]))
                if item.cancelled:
                    return
                ydl.download([item.url])

            if not item.cancelled:
                self._set_status(item, "Done")
                self._ui_queue.put(("progress", item, 1.0, "", ""))
        except yt_dlp.utils.DownloadError as e:
            if not item.cancelled:
                self._set_status(item, "Error")
                self._ui_queue.put(("speed", item, f"Error: {str(e)[:60]}"))
        except Exception as e:
            if not item.cancelled:
                self._set_status(item, "Error")
                self._ui_queue.put(("speed", item, f"Error: {str(e)[:60]}"))
        finally:
            self._ui_queue.put(("stats",))

    def _progress_hook(self, d: dict, item: DownloadItem):
        if item.cancelled:
            raise yt_dlp.utils.DownloadCancelled()

        if d["status"] == "downloading":
            total      = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            pct   = downloaded / total if total > 0 else 0
            speed = d.get("_speed_str", "").strip()
            eta   = d.get("_eta_str", "").strip()
            self._ui_queue.put(("progress", item, pct, speed, eta))
        elif d["status"] == "finished":
            self._ui_queue.put(("progress", item, 1.0, "Converting…", ""))
            self._set_status(item, "Converting")

    # ──────────────────────────────────────────
    #  UI Updates (thread-safe via queue)
    # ──────────────────────────────────────────
    def _set_status(self, item: DownloadItem, status: str):
        self._ui_queue.put(("status", item, status))

    def _poll_ui_queue(self):
        try:
            while True:
                msg  = self._ui_queue.get_nowait()
                kind = msg[0]

                if kind == "status":
                    _, item, status = msg
                    item.status = status
                    color = STATUS_COLORS.get(status, "#9CA3AF")
                    if item.status_label:
                        item.status_label.configure(text=status, text_color=color)
                    if status in ("Done", "Error", "Cancelled") and item.cancel_btn:
                        item.cancel_btn.configure(state="disabled")
                    if status == "Done" and item.progress_bar:
                        item.progress_bar.configure(progress_color="#10B981")
                    if status == "Error" and item.progress_bar:
                        item.progress_bar.configure(progress_color="#EF4444")
                    self._update_stats()

                elif kind == "progress":
                    _, item, pct, speed, eta = msg
                    if item.progress_bar:
                        item.progress_bar.set(pct)
                    if item.speed_label:
                        parts = []
                        if speed: parts.append(speed)
                        if eta:   parts.append(f"ETA {eta}")
                        if 0 < pct < 1: parts.append(f"{pct * 100:.1f}%")
                        item.speed_label.configure(text="  ".join(parts))

                elif kind == "title":
                    _, item, title = msg
                    item.title = title
                    if item.title_label:
                        item.title_label.configure(text=title)

                elif kind == "speed":
                    _, item, text = msg
                    if item.speed_label:
                        item.speed_label.configure(text=text)

                elif kind == "stats":
                    self._update_stats()

        except queue.Empty:
            pass
        self.after(120, self._poll_ui_queue)

    def _update_stats(self):
        q  = sum(1 for i in self._items if i.status == "Queued")
        dl = sum(1 for i in self._items if i.status in ("Downloading", "Converting"))
        dn = sum(1 for i in self._items if i.status == "Done")
        er = sum(1 for i in self._items if i.status == "Error")
        self._stats_label.configure(
            text=f"Queue: {q}  |  Downloading: {dl}  |  Done: {dn}  |  Error: {er}"
        )

    # ──────────────────────────────────────────
    #  Close
    # ──────────────────────────────────────────
    def _on_close(self):
        self._running = False
        for item in self._items:
            item.cancelled = True
        self.destroy()


# ──────────────────────────────────────────────
#  Entry point (called by pipx / the console script)
# ──────────────────────────────────────────────
def main():
    # Warn if ffmpeg is missing — non-fatal, app still opens
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            "ffmpeg not found",
            "ffmpeg was not found on your PATH.\n\n"
            "Install it via:\n"
            "  macOS:   brew install ffmpeg\n"
            "  Ubuntu:  sudo apt install ffmpeg\n"
            "  Windows: https://ffmpeg.org/download.html\n\n"
            "The app will still open but format conversion may fail.",
        )
        root.destroy()

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
