import argparse
import ctypes
import io
import os
import re
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
import urllib.request
import urllib.error
import webbrowser
from tkinter import filedialog, messagebox

import customtkinter as ctk
import yt_dlp
from PIL import Image


APP_TEXT = {
    "window_title": "유튜브 다운로더",
    "byline": "by HooniKim",
    "subtitle": "링크를 넣고 원하는 품질로 저장하세요.",
    "url_label": "유튜브 링크",
    "url_placeholder": "유튜브 링크를 붙여넣으세요",
    "folder_label": "저장 위치",
    "browse_button": "폴더 선택",
    "quality_label": "화질 선택",
    "download_button": "다운로드 시작",
    "stop_button": "중지",
    "update_button": "업데이트 확인",
    "update_download_button": "업데이트 다운로드",
    "update_install_hint": "릴리즈 페이지에서 새 youtube_downloader.exe를 다운로드한 뒤, 현재 프로그램을 종료하고 기존 파일을 교체하세요.",
    "menu_help": "도움말",
    "menu_check_update": "업데이트 확인",
    "menu_release_page": "릴리즈 페이지 열기",
    "log_label": "진행 상태",
    "ready": "대기 중",
}

APP_VERSION = "1.0.0"
GITHUB_RELEASES_API = "https://api.github.com/repos/HooniKims/YT-Downloader/releases/latest"
GITHUB_RELEASES_PAGE = "https://github.com/HooniKims/YT-Downloader/releases"

THEME = {
    "bg": "#f3f0ea",
    "surface": "#fbfaf7",
    "surface_alt": "#eee8df",
    "text": "#221f1b",
    "muted": "#6f675d",
    "accent": "#2f6f73",
    "accent_hover": "#285f63",
    "danger": "#b45346",
    "danger_hover": "#99463b",
    "success": "#3f7b55",
    "border": "#d8d0c5",
}

QUALITY_OPTIONS = [
    ("최고 화질 (추천, 영상+음성)", "bestvideo+bestaudio"),
    ("최고 단일 파일", "best"),
    ("720p", "720p"),
    ("480p", "480p"),
    ("오디오만 (mp3)", "bestaudio/best"),
]

PAPERLOGY_FAMILY = "Paperlogy"
PAPERLOGY_TK_FAMILY = "Paperlogy 4 Regular"


def app_dir():
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def get_icon_path():
    return os.path.join(app_dir(), "youricon.ico")


def get_ffmpeg_path():
    """Return bundled ffmpeg.exe when present, otherwise fall back to PATH."""
    for base in (app_dir(), os.path.dirname(os.path.abspath(__file__))):
        candidate = os.path.join(base, "ffmpeg.exe")
        if os.path.isfile(candidate):
            return candidate
    return "ffmpeg"


def get_font_path(filename):
    return os.path.join(app_dir(), "fonts", filename)


def get_paperlogy_font_family():
    return PAPERLOGY_TK_FAMILY


def load_paperlogy_font(root):
    regular_font = get_font_path("Paperlogy-4Regular.ttf")
    semibold_font = get_font_path("Paperlogy-6SemiBold.ttf")
    if sys.platform.startswith("win"):
        for font_path in (regular_font, semibold_font):
            if os.path.isfile(font_path):
                ctypes.windll.gdi32.AddFontResourceExW(os.path.abspath(font_path), 0x10, 0)

    families = set(root.tk.call("font", "families"))
    family = PAPERLOGY_FAMILY if PAPERLOGY_FAMILY in families else get_paperlogy_font_family()
    for font_name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkTooltipFont"):
        try:
            tkfont.nametofont(font_name).configure(family=family, size=10)
        except tk.TclError:
            pass
    try:
        tkfont.nametofont("TkHeadingFont").configure(weight="bold")
    except tk.TclError:
        pass
    return family


def apply_window_icon(root):
    icon_path = get_icon_path()
    if os.path.isfile(icon_path):
        try:
            root.iconbitmap(icon_path)
        except tk.TclError:
            pass


def _version_parts(version):
    parts = []
    for part in version.strip().lstrip("vV").split("."):
        match = re.match(r"(\d+)", part)
        parts.append(int(match.group(1)) if match else 0)
    while len(parts) < 3:
        parts.append(0)
    return parts[:3]


def compare_versions(left, right):
    left_parts = _version_parts(left)
    right_parts = _version_parts(right)
    if left_parts > right_parts:
        return 1
    if left_parts < right_parts:
        return -1
    return 0


def parse_latest_release(release):
    tag_name = release.get("tag_name", "")
    return {
        "version": tag_name.lstrip("vV"),
        "url": release.get("html_url", GITHUB_RELEASES_PAGE),
        "available": True,
    }


def fetch_latest_release():
    request = urllib.request.Request(
        GITHUB_RELEASES_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "YT-Downloader"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            import json

            return parse_latest_release(json.loads(response.read().decode("utf-8")))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"version": APP_VERSION, "url": GITHUB_RELEASES_PAGE, "available": False}
        raise


def evaluate_update_status(release, current_version=APP_VERSION):
    url = release.get("url") or GITHUB_RELEASES_PAGE
    if not release.get("available", True):
        return {"state": "no_release", "version": current_version, "url": url}

    latest_version = release.get("version") or current_version
    if compare_versions(latest_version, current_version) > 0:
        return {"state": "available", "version": latest_version, "url": url}
    return {"state": "current", "version": latest_version, "url": url}


def build_download_options(output_path, ffmpeg_path, quality, progress_hook=None):
    opts = {
        "outtmpl": os.path.join(output_path, "%(uploader)s", "%(title)s.%(ext)s"),
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "windowsfilenames": True,
        "noplaylist": True,
    }
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    if ffmpeg_path:
        opts["ffmpeg_location"] = ffmpeg_path

    if quality == "bestvideo+bestaudio":
        opts["format"] = "bv*+ba/b"
        opts["merge_output_format"] = "mp4"
    elif quality == "best":
        opts["format"] = "b[ext=mp4]/b/best"
        opts["merge_output_format"] = "mp4"
    elif quality == "720p":
        opts["format"] = "bv*[height<=720]+ba/b[height<=720]/best[height<=720]/best"
        opts["merge_output_format"] = "mp4"
    elif quality == "480p":
        opts["format"] = "bv*[height<=480]+ba/b[height<=480]/best[height<=480]/best"
        opts["merge_output_format"] = "mp4"
    elif quality == "bestaudio/best":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]
    else:
        opts["format"] = f"{quality}/best"
        opts["merge_output_format"] = "mp4"

    return opts


def download_url(url, output_path, quality="bestvideo+bestaudio", progress_hook=None):
    ffmpeg_path = get_ffmpeg_path()
    ydl_opts = build_download_options(output_path, ffmpeg_path, quality, progress_hook)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="YouTube downloader")
    parser.add_argument("--download-test", help="Download one URL and exit without opening the GUI.")
    parser.add_argument("--output", default="test_downloads_exe", help="Output folder for --download-test.")
    parser.add_argument("--quality", default="bestvideo+bestaudio", help="Quality selector for --download-test.")
    return parser.parse_args(argv)


def run_download_test(url, output_path, quality):
    os.makedirs(output_path, exist_ok=True)
    try:
        download_url(url, output_path, quality)
        return 0
    except Exception:
        return 1


class YouTubeDownloaderUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_TEXT['window_title']} v{APP_VERSION}")
        self.root.geometry("860x720")
        self.root.minsize(760, 640)
        self.root.configure(fg_color=THEME["bg"])
        self.font_family = load_paperlogy_font(root)
        apply_window_icon(root)

        self.is_downloading = False
        self._download_cancelled = False
        self._current_temp_files = []

        self.thumbnail_img = None
        self.url_menu = None
        self.latest_release_url = None
        self.last_update_check = None
        self.update_check_in_progress = False
        self.url_var = tk.StringVar()
        self.path_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Desktop"))
        self.quality_var = tk.StringVar(value="bestvideo+bestaudio")
        self.progress_var = tk.StringVar(value=APP_TEXT["ready"])

        self._build_menu()
        self._build_ui()
        self.root.after(1200, self.check_for_updates_silent)

    def font(self, size=14, weight="normal"):
        return ctk.CTkFont(family=self.font_family, size=size, weight=weight)

    def script_font(self, size=18):
        return ctk.CTkFont(family="Segoe Script", size=size, weight="bold")

    def log_message(self, message):
        if hasattr(self, "log_text"):
            self.log_text.configure(state="normal")
            self.log_text.insert("end", f"{message}\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
            self.root.update_idletasks()

    def _build_menu(self):
        menu_bar = tk.Menu(self.root)
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label=APP_TEXT["menu_check_update"], command=self.check_for_updates)
        help_menu.add_separator()
        help_menu.add_command(label=APP_TEXT["menu_release_page"], command=self.open_release_page)
        menu_bar.add_cascade(label=APP_TEXT["menu_help"], menu=help_menu)
        self.root.configure(menu=menu_bar)

    def open_release_page(self):
        webbrowser.open(self.latest_release_url or GITHUB_RELEASES_PAGE)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)
            self.log_message(f"저장 위치 변경: {folder}")

    def _build_ui(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        shell = ctk.CTkFrame(self.root, fg_color=THEME["bg"], corner_radius=0)
        shell.grid(row=0, column=0, sticky="nsew", padx=28, pady=24)
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(shell, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        header.grid_columnconfigure(0, weight=1)

        brand_row = ctk.CTkFrame(header, fg_color="transparent")
        brand_row.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            brand_row,
            text=APP_TEXT["window_title"],
            text_color=THEME["text"],
            font=self.font(32, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            brand_row,
            text=APP_TEXT["byline"],
            text_color=THEME["accent"],
            font=self.script_font(20),
        ).grid(row=0, column=1, sticky="sw", padx=(12, 0), pady=(0, 4))
        ctk.CTkLabel(
            header,
            text=APP_TEXT["subtitle"],
            text_color=THEME["muted"],
            font=self.font(14),
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        content = ctk.CTkFrame(shell, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=5)
        content.grid_columnconfigure(1, weight=4)
        content.grid_rowconfigure(0, weight=1)

        left = self._card(content)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        left.grid_columnconfigure(0, weight=1)

        right = self._card(content)
        right.grid(row=0, column=1, sticky="nsew", padx=(14, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(4, weight=1)

        self._build_input_area(left)
        self._build_thumbnail_area(left)
        self._build_actions(left)
        self._build_quality_area(right)
        self._build_status_area(right)

    def _card(self, parent):
        return ctk.CTkFrame(
            parent,
            fg_color=THEME["surface"],
            border_color=THEME["border"],
            border_width=1,
            corner_radius=18,
        )

    def _section_label(self, parent, text, row):
        ctk.CTkLabel(parent, text=text, text_color=THEME["text"], font=self.font(15, "bold")).grid(
            row=row, column=0, sticky="w", padx=22, pady=(20, 8)
        )

    def _build_input_area(self, parent):
        self._section_label(parent, APP_TEXT["url_label"], 0)
        self.url_entry = ctk.CTkEntry(
            parent,
            textvariable=self.url_var,
            placeholder_text=APP_TEXT["url_placeholder"],
            height=46,
            corner_radius=12,
            border_color=THEME["border"],
            fg_color="#f7f4ee",
            text_color=THEME["text"],
            placeholder_text_color=THEME["muted"],
            font=self.font(14),
        )
        self.url_entry.grid(row=1, column=0, sticky="ew", padx=22)
        self.url_entry.bind("<Button-3>", self.show_url_menu)
        self.url_var.trace_add("write", self.update_thumbnail)

        self.url_menu = tk.Menu(self.root, tearoff=0)
        self.url_menu.add_command(label="잘라내기", command=self.cut_url)
        self.url_menu.add_command(label="복사", command=self.copy_url)
        self.url_menu.add_command(label="붙여넣기", command=self.paste_url)
        self.url_entry.bind("<Control-v>", self.paste_url_event)
        self.url_entry.bind("<Control-V>", self.paste_url_event)
        self.url_entry.bind("<Control-c>", self.copy_url_event)
        self.url_entry.bind("<Control-C>", self.copy_url_event)
        self.url_entry.bind("<Control-x>", self.cut_url_event)
        self.url_entry.bind("<Control-X>", self.cut_url_event)

        self._section_label(parent, APP_TEXT["folder_label"], 2)
        folder_row = ctk.CTkFrame(parent, fg_color="transparent")
        folder_row.grid(row=3, column=0, sticky="ew", padx=22)
        folder_row.grid_columnconfigure(0, weight=1)

        self.path_entry = ctk.CTkEntry(
            folder_row,
            textvariable=self.path_var,
            height=42,
            corner_radius=12,
            border_color=THEME["border"],
            fg_color="#f7f4ee",
            text_color=THEME["text"],
            font=self.font(13),
        )
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.browse_button = ctk.CTkButton(
            folder_row,
            text=APP_TEXT["browse_button"],
            command=self.browse_folder,
            height=42,
            width=112,
            corner_radius=12,
            fg_color=THEME["surface_alt"],
            hover_color="#e3dbcf",
            text_color=THEME["text"],
            font=self.font(13, "bold"),
        )
        self.browse_button.grid(row=0, column=1)

    def _build_thumbnail_area(self, parent):
        preview = ctk.CTkFrame(parent, fg_color=THEME["surface_alt"], corner_radius=16)
        preview.grid(row=4, column=0, sticky="ew", padx=22, pady=22)
        preview.grid_columnconfigure(0, weight=1)

        self.thumbnail_label = ctk.CTkLabel(
            preview,
            text="썸네일 미리보기",
            text_color=THEME["muted"],
            font=self.font(15, "bold"),
            width=420,
            height=236,
        )
        self.thumbnail_label.grid(row=0, column=0, sticky="ew", padx=14, pady=14)

    def _build_actions(self, parent):
        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.grid(row=5, column=0, sticky="ew", padx=22, pady=(0, 22))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=0)

        self.download_button = ctk.CTkButton(
            actions,
            text=APP_TEXT["download_button"],
            command=self.start_download,
            height=50,
            corner_radius=14,
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            text_color="#f7f4ee",
            font=self.font(15, "bold"),
        )
        self.download_button.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.stop_button = ctk.CTkButton(
            actions,
            text=APP_TEXT["stop_button"],
            command=self.stop_download,
            state="disabled",
            height=50,
            width=92,
            corner_radius=14,
            fg_color=THEME["danger"],
            hover_color=THEME["danger_hover"],
            text_color="#f7f4ee",
            font=self.font(15, "bold"),
        )
        self.stop_button.grid(row=0, column=1)

        self.update_button = ctk.CTkButton(
            actions,
            text=APP_TEXT["update_button"],
            command=self.check_for_updates,
            height=40,
            corner_radius=12,
            fg_color=THEME["surface_alt"],
            hover_color="#e3dbcf",
            text_color=THEME["text"],
            font=self.font(13, "bold"),
        )
        self.update_button.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))

    def _build_quality_area(self, parent):
        ctk.CTkLabel(parent, text=APP_TEXT["quality_label"], text_color=THEME["text"], font=self.font(17, "bold")).grid(
            row=0, column=0, sticky="w", padx=22, pady=(22, 10)
        )

        self.quality_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.quality_frame.grid(row=1, column=0, sticky="ew", padx=22)
        self.quality_frame.grid_columnconfigure(0, weight=1)

        for i, (text, value) in enumerate(QUALITY_OPTIONS):
            radio = ctk.CTkRadioButton(
                self.quality_frame,
                text=text,
                variable=self.quality_var,
                value=value,
                command=self.on_quality_changed,
                radiobutton_width=18,
                radiobutton_height=18,
                border_width_checked=5,
                border_color=THEME["border"],
                fg_color=THEME["accent"],
                hover_color=THEME["accent_hover"],
                text_color=THEME["text"],
                font=self.font(14, "bold" if i == 0 else "normal"),
            )
            radio.grid(row=i, column=0, sticky="w", pady=7)

        self.quality_hint = ctk.CTkLabel(
            parent,
            text="최고 화질은 영상과 음성을 따로 받아 FFmpeg로 병합합니다.",
            text_color=THEME["muted"],
            font=self.font(12),
            wraplength=300,
            justify="left",
        )
        self.quality_hint.grid(row=2, column=0, sticky="w", padx=22, pady=(8, 18))

    def _build_status_area(self, parent):
        status_panel = ctk.CTkFrame(parent, fg_color=THEME["surface_alt"], corner_radius=16)
        status_panel.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 18))
        status_panel.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            status_panel,
            textvariable=self.progress_var,
            text_color=THEME["text"],
            font=self.font(14, "bold"),
        )
        self.status_label.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        self.progress_bar = ctk.CTkProgressBar(
            status_panel,
            height=12,
            corner_radius=8,
            progress_color=THEME["success"],
            fg_color="#ded6ca",
        )
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))
        self.progress_bar.set(0)

        ctk.CTkLabel(parent, text=APP_TEXT["log_label"], text_color=THEME["text"], font=self.font(15, "bold")).grid(
            row=4, column=0, sticky="w", padx=22, pady=(0, 8)
        )
        self.log_text = ctk.CTkTextbox(
            parent,
            height=220,
            corner_radius=16,
            border_color=THEME["border"],
            border_width=1,
            fg_color="#f7f4ee",
            text_color=THEME["text"],
            font=self.font(12),
            wrap="word",
        )
        self.log_text.grid(row=5, column=0, sticky="nsew", padx=22, pady=(0, 22))
        self.log_text.insert("end", "대기 중입니다.\n")
        self.log_text.configure(state="disabled")

    def show_url_menu(self, event):
        try:
            self.url_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.url_menu.grab_release()

    def _entry_widget(self):
        return self.url_entry._entry

    def paste_url(self):
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            return "break"
        entry = self._entry_widget()
        try:
            start = entry.index("sel.first")
            end = entry.index("sel.last")
            entry.delete(start, end)
        except tk.TclError:
            pass
        entry.insert(entry.index("insert"), text)
        self.url_var.set(entry.get())
        return "break"

    def paste_url_event(self, _event=None):
        return self.paste_url()

    def copy_url(self):
        entry = self._entry_widget()
        try:
            text = entry.selection_get()
        except tk.TclError:
            text = entry.get()
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        return "break"

    def copy_url_event(self, _event=None):
        return self.copy_url()

    def cut_url(self):
        entry = self._entry_widget()
        try:
            text = entry.selection_get()
            entry.delete(entry.index("sel.first"), entry.index("sel.last"))
        except tk.TclError:
            text = entry.get()
            entry.delete(0, "end")
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.url_var.set(entry.get())
        return "break"

    def cut_url_event(self, _event=None):
        return self.cut_url()

    def check_for_updates(self):
        self._start_update_check(silent=False)

    def check_for_updates_silent(self):
        self._start_update_check(silent=True)

    def _start_update_check(self, silent):
        if self.update_check_in_progress:
            return
        self.update_check_in_progress = True
        if not silent:
            self.update_button.configure(state="disabled", text="확인 중...")
            self.progress_var.set("업데이트 확인 중...")
        thread = threading.Thread(target=lambda: self._check_for_updates_worker(silent), daemon=True)
        thread.start()

    def _check_for_updates_worker(self, silent=False):
        try:
            release = fetch_latest_release()
            status = evaluate_update_status(release, APP_VERSION)
            self.root.after(0, lambda: self._apply_update_status(status, silent))
        except Exception as exc:
            self.root.after(0, lambda: self._show_update_error(exc, silent))

    def _apply_update_status(self, status, silent=False):
        self.update_check_in_progress = False
        self.last_update_check = status
        self.latest_release_url = status["url"]
        if status["state"] == "available":
            self._show_update_available(status["version"], status["url"])
        elif status["state"] == "no_release":
            self._show_no_release(silent=silent)
        else:
            self._show_no_update(silent=silent)

    def _show_update_available(self, version, url):
        self.update_button.configure(state="normal", text=APP_TEXT["update_download_button"], command=lambda: webbrowser.open(url))
        self.progress_var.set(f"새 버전 v{version} 사용 가능")
        self.log_message(f"새 버전 v{version}이 있습니다.")
        self.log_message(APP_TEXT["update_install_hint"])
        self.log_message(f"다운로드 페이지: {url}")

    def _show_no_update(self, silent=False):
        self.update_button.configure(state="normal", text=APP_TEXT["update_button"], command=self.check_for_updates)
        if silent:
            return
        self.progress_var.set("최신 버전입니다")
        self.log_message("현재 최신 버전을 사용 중입니다.")

    def _show_no_release(self, silent=False):
        self.update_button.configure(state="normal", text="릴리즈 페이지", command=self.open_release_page)
        if silent:
            return
        self.progress_var.set("등록된 릴리즈가 없습니다")
        self.log_message("아직 GitHub 릴리즈가 없습니다. 릴리즈를 만들면 여기서 업데이트를 확인할 수 있습니다.")

    def _show_update_error(self, exc, silent=False):
        self.update_check_in_progress = False
        self.update_button.configure(state="normal", text=APP_TEXT["update_button"], command=self.check_for_updates)
        if silent:
            return
        self.progress_var.set("업데이트 확인 실패")
        self.log_message(f"업데이트 확인 실패: {exc}")

    def on_quality_changed(self):
        selected = next((label for label, value in QUALITY_OPTIONS if value == self.quality_var.get()), "화질")
        self.progress_var.set(f"{selected} 선택됨")

    def update_thumbnail(self, *args):
        url = self.url_var.get().strip()
        thumb_url = self.extract_thumbnail_url(url)
        if not thumb_url:
            self.thumbnail_img = None
            self.thumbnail_label.configure(image=None, text="썸네일 미리보기")
            return

        try:
            with urllib.request.urlopen(thumb_url, timeout=10) as response:
                raw_data = response.read()
            image = Image.open(io.BytesIO(raw_data)).resize((420, 236), Image.LANCZOS)
            self.thumbnail_img = ctk.CTkImage(light_image=image, dark_image=image, size=(420, 236))
            self.thumbnail_label.configure(image=self.thumbnail_img, text="")
        except Exception as exc:
            self.log_message(f"썸네일 불러오기 실패: {exc}")
            self.thumbnail_label.configure(image=None, text="썸네일을 불러오지 못했습니다")

    def extract_thumbnail_url(self, url):
        patterns = [
            r"youtu\.be/([0-9A-Za-z_-]{11})",
            r"(?:v=|/)([0-9A-Za-z_-]{11})(?:[&?/#].*)?$",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return f"https://img.youtube.com/vi/{match.group(1)}/hqdefault.jpg"
        return None

    def progress_hook(self, d):
        if self._download_cancelled:
            raise yt_dlp.utils.DownloadError("사용자가 다운로드를 중지했습니다.")

        if d["status"] == "downloading":
            tmpfilename = d.get("tmpfilename")
            if tmpfilename and tmpfilename not in self._current_temp_files:
                self._current_temp_files.append(tmpfilename)

            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
            if total_bytes:
                percent = d["downloaded_bytes"] / total_bytes * 100
                speed = d.get("speed")
                eta = d.get("eta")
                extra = []
                if speed:
                    extra.append(f"{speed / 1024 / 1024:.2f} MB/s")
                if eta:
                    extra.append(f"남은 시간 {int(eta)}초")
                extra_txt = " | " + " / ".join(extra) if extra else ""
                self.progress_var.set(f"다운로드 중... {percent:.1f}%{extra_txt}")
                self.progress_bar.set(min(max(percent / 100, 0), 1))
            else:
                self.progress_var.set("다운로드 중...")
        elif d["status"] == "finished":
            self.progress_var.set("후처리 중...")
            self.progress_bar.set(1)

    def start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("오류", "유튜브 URL을 입력해 주세요.")
            return
        if self.is_downloading:
            return

        self.is_downloading = True
        self._download_cancelled = False
        self._current_temp_files = []
        self.download_button.configure(state="disabled", text="다운로드 중")
        self.stop_button.configure(state="normal")
        self.progress_bar.set(0)
        self.progress_var.set("다운로드 준비 중...")

        thread = threading.Thread(target=self.download_video, args=(url,), daemon=True)
        thread.start()

    def stop_download(self):
        if not self.is_downloading:
            return
        self._download_cancelled = True
        self.stop_button.configure(state="disabled", text="중지 중")
        self.log_message("다운로드 중지를 요청했습니다...")

    def _build_common_opts(self, output_path, ffmpeg_path):
        return build_download_options(output_path, ffmpeg_path, self.quality_var.get(), self.progress_hook)

    def download_video(self, url):
        try:
            output_path = self.path_var.get() or "downloads"
            ffmpeg_path = get_ffmpeg_path()
            ydl_opts = self._build_common_opts(output_path, ffmpeg_path)

            try:
                info_opts = {
                    "quiet": True,
                    "nocheckcertificate": True,
                    "no_warnings": True,
                    "ignoreerrors": False,
                    "noplaylist": True,
                }
                with yt_dlp.YoutubeDL(info_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                self.log_message(f"영상 정보: {info.get('title', '알 수 없음')} / {info.get('uploader', '알 수 없음')}")
            except Exception as exc:
                self.log_message(f"영상 정보 확인 실패, 다운로드를 계속합니다: {str(exc)[:120]}")

            self.log_message(f"다운로드 시작: {url}")
            self.log_message(f"FFmpeg: {ffmpeg_path}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            if not self._download_cancelled:
                self.log_message("다운로드와 후처리가 완료되었습니다.")
                self.progress_var.set("완료")
                self.progress_bar.set(1)

        except yt_dlp.utils.DownloadError as exc:
            if "cancel" in str(exc).lower() or "중지" in str(exc):
                self.log_message("다운로드가 중지되었습니다.")
                self.progress_var.set("다운로드 중지됨")
            else:
                self.log_message(f"다운로드 오류: {exc}")
                messagebox.showerror("다운로드 오류", f"오류가 발생했습니다:\n{exc}")
        except Exception as exc:
            self.log_message(f"예상치 못한 오류: {exc}")
            messagebox.showerror("예상치 못한 오류", f"예상치 못한 오류가 발생했습니다:\n{exc}")
        finally:
            if self._download_cancelled:
                for file_path in self._current_temp_files:
                    try:
                        if file_path and os.path.exists(file_path):
                            os.remove(file_path)
                            self.log_message(f"임시 파일 삭제: {os.path.basename(file_path)}")
                    except Exception as exc:
                        self.log_message(f"임시 파일 정리 실패: {exc}")

            self.is_downloading = False
            self._download_cancelled = False
            self.download_button.configure(state="normal", text=APP_TEXT["download_button"])
            self.stop_button.configure(state="disabled", text=APP_TEXT["stop_button"])
            if self.progress_var.get() not in ("완료", "다운로드 중지됨"):
                self.progress_var.set(APP_TEXT["ready"])
            if self.progress_var.get() != "완료":
                self.progress_bar.set(0)


def main():
    args = parse_args()
    if args.download_test:
        raise SystemExit(run_download_test(args.download_test, args.output, args.quality))

    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("green")
    root = ctk.CTk()
    YouTubeDownloaderUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
