import os
import queue

import customtkinter as ctk

from youtube_downloader import (
    APP_TEXT,
    APP_VERSION,
    GITHUB_RELEASES_API,
    GITHUB_RELEASES_PAGE,
    QUALITY_OPTIONS,
    THEME,
    YouTubeDownloaderUI,
    build_download_options,
    compare_versions,
    evaluate_update_status,
    format_progress_label,
    get_font_path,
    get_ffmpeg_path,
    get_icon_path,
    get_paperlogy_font_family,
    parse_args,
    parse_latest_release,
    run_download_test,
)


class FakeProgressVar:
    def __init__(self):
        self.values = []

    def set(self, value):
        self.values.append(value)

    def get(self):
        return self.values[-1] if self.values else ""


class FakeProgressBar:
    def __init__(self):
        self.values = []

    def set(self, value):
        self.values.append(value)


def test_extracts_thumbnail_url_from_short_youtube_link():
    app = YouTubeDownloaderUI.__new__(YouTubeDownloaderUI)

    assert (
        app.extract_thumbnail_url("https://youtu.be/87PfcSLZsaE")
        == "https://img.youtube.com/vi/87PfcSLZsaE/hqdefault.jpg"
    )


def test_default_quality_prefers_best_video_plus_audio_mp4_merge(tmp_path):
    opts = build_download_options(str(tmp_path), get_ffmpeg_path(), "bestvideo+bestaudio")

    assert opts["format"] == "bv*+ba/b"
    assert opts["merge_output_format"] == "mp4"
    assert opts["outtmpl"] == os.path.join(str(tmp_path), "%(uploader)s", "%(title)s.%(ext)s")
    assert opts["ffmpeg_location"].endswith("ffmpeg.exe")
    assert opts["quiet"] is True
    assert opts["no_warnings"] is True
    assert opts["noprogress"] is True


def test_ffmpeg_is_loaded_from_project_folder():
    ffmpeg_path = get_ffmpeg_path()

    assert os.path.basename(ffmpeg_path).lower() == "ffmpeg.exe"
    assert os.path.isfile(ffmpeg_path)


def test_download_test_args_use_headless_mode():
    args = parse_args(
        [
            "--download-test",
            "https://youtu.be/87PfcSLZsaE",
            "--output",
            "tmp-output",
            "--quality",
            "bestvideo+bestaudio",
        ]
    )

    assert args.download_test == "https://youtu.be/87PfcSLZsaE"
    assert args.output == "tmp-output"
    assert args.quality == "bestvideo+bestaudio"


def test_quality_labels_are_korean_and_recommend_best_quality():
    labels = [label for label, _value in QUALITY_OPTIONS]

    assert labels[0] == "\ucd5c\uace0 \ud654\uc9c8 (\ucd94\ucc9c, \uc601\uc0c1+\uc74c\uc131)"
    assert "Best quality" not in labels[0]
    assert "\ucd5c\uace0 \ub2e8\uc77c \ud30c\uc77c" in labels
    assert "\uc624\ub514\uc624\ub9cc (mp3)" in labels


def test_paperlogy_font_file_is_available():
    font_path = get_font_path("Paperlogy-4Regular.ttf")

    assert os.path.basename(font_path) == "Paperlogy-4Regular.ttf"
    assert os.path.isfile(font_path)


def test_paperlogy_font_family_is_used_for_tk():
    assert get_paperlogy_font_family().startswith("Paperlogy")


def test_download_test_does_not_write_log_file(tmp_path, monkeypatch):
    def fake_download_url(url, output_path, quality):
        os.makedirs(output_path, exist_ok=True)
        with open(os.path.join(output_path, "sample.mp4"), "wb") as video_file:
            video_file.write(b"ok")

    monkeypatch.setattr("youtube_downloader.download_url", fake_download_url)

    assert run_download_test("https://youtu.be/87PfcSLZsaE", str(tmp_path), "bestvideo+bestaudio") == 0
    assert not (tmp_path / "download_test_result.txt").exists()
    assert (tmp_path / "sample.mp4").exists()


def test_spec_bundles_runtime_assets():
    with open("youtube_downloader.spec", encoding="utf-8") as spec_file:
        spec = spec_file.read()

    assert "ffmpeg.exe" in spec
    assert "ffprobe.exe" in spec
    assert "youricon.ico" in spec
    assert "customtkinter" in spec
    assert "fonts/Paperlogy-4Regular.ttf" in spec
    assert "fonts/Paperlogy-6SemiBold.ttf" in spec


def test_modern_korean_ui_copy_and_theme_tokens_are_defined():
    assert APP_TEXT["window_title"] == "\uc720\ud29c\ube0c \ub2e4\uc6b4\ub85c\ub354"
    assert APP_TEXT["byline"] == "by HooniKim"
    assert APP_TEXT["url_placeholder"] == "\uc720\ud29c\ube0c \ub9c1\ud06c\ub97c \ubd99\uc5ec\ub123\uc73c\uc138\uc694"
    assert APP_TEXT["download_button"] == "\ub2e4\uc6b4\ub85c\ub4dc \uc2dc\uc791"
    assert APP_TEXT["stop_button"] == "\uc911\uc9c0"
    assert THEME["accent"].startswith("#")
    assert THEME["surface"].startswith("#")
    assert THEME["success"].startswith("#")


def test_update_menu_copy_is_defined():
    assert APP_TEXT["menu_help"] == "\ub3c4\uc6c0\ub9d0"
    assert APP_TEXT["menu_check_update"] == "\uc5c5\ub370\uc774\ud2b8 \ud655\uc778"
    assert APP_TEXT["menu_release_page"] == "\ub9b4\ub9ac\uc988 \ud398\uc774\uc9c0 \uc5f4\uae30"
    assert APP_TEXT["update_download_button"] == "\uc5c5\ub370\uc774\ud2b8 \ub2e4\uc6b4\ub85c\ub4dc"
    assert "\uc885\ub8cc" in APP_TEXT["update_install_hint"]


def test_custom_window_icon_is_available():
    icon_path = get_icon_path()

    assert os.path.basename(icon_path) == "youricon.ico"
    assert os.path.isfile(icon_path)


def test_version_and_github_release_endpoint_are_defined():
    assert APP_VERSION
    assert GITHUB_RELEASES_API == "https://api.github.com/repos/HooniKims/YT-Downloader/releases/latest"
    assert GITHUB_RELEASES_PAGE == "https://github.com/HooniKims/YT-Downloader/releases"


def test_release_version_parsing_and_comparison():
    release = parse_latest_release(
        {
            "tag_name": "v1.2.0",
            "html_url": "https://github.com/HooniKims/YT-Downloader/releases/tag/v1.2.0",
        }
    )

    assert release["version"] == "1.2.0"
    assert release["url"].endswith("/v1.2.0")
    assert compare_versions("1.2.0", "1.1.9") == 1
    assert compare_versions("1.2.0", "1.2.0") == 0
    assert compare_versions("1.2.0", "1.3.0") == -1


def test_update_status_distinguishes_new_current_and_missing_release():
    assert evaluate_update_status({"available": True, "version": "1.0.1", "url": "https://example.com"}, "1.0.0")[
        "state"
    ] == "available"
    assert evaluate_update_status({"available": True, "version": "1.0.0", "url": "https://example.com"}, "1.0.0")[
        "state"
    ] == "current"
    assert evaluate_update_status({"available": False, "version": "1.0.0", "url": GITHUB_RELEASES_PAGE}, "1.0.0")[
        "state"
    ] == "no_release"


def test_release_upload_folder_exists_for_future_update_assets():
    assert os.path.isdir("release_assets")
    assert os.path.isfile(os.path.join("release_assets", "README.md"))


def test_progress_hook_queues_ui_updates_instead_of_touching_widgets_directly():
    app = YouTubeDownloaderUI.__new__(YouTubeDownloaderUI)
    app._download_cancelled = False
    app._current_temp_files = []
    app._last_progress_update = 0
    app._ui_thread_id = -1
    app.ui_queue = queue.Queue()
    app.progress_var = FakeProgressVar()
    app.progress_bar = FakeProgressBar()

    app.progress_hook(
        {
            "status": "downloading",
            "tmpfilename": "video.part",
            "downloaded_bytes": 50,
            "total_bytes": 100,
            "speed": 1024 * 1024,
            "eta": 2,
        }
    )

    assert app.progress_var.values == []
    assert app.progress_bar.values == []
    assert app.ui_queue.qsize() == 1
    assert app._current_temp_files == ["video.part"]


def test_progress_label_includes_percent_and_remaining_time():
    assert format_progress_label(50, 100, 2) == "\ub2e4\uc6b4\ub85c\ub4dc  50.0% | \ub0a8\uc740 00:02"
    assert format_progress_label(100, 100, 125) == "\ub2e4\uc6b4\ub85c\ub4dc 100.0% | \ub0a8\uc740 02:05"
    assert format_progress_label(50, 100, None) == "\ub2e4\uc6b4\ub85c\ub4dc  50.0% | \ub0a8\uc740 --:--"


def test_update_worker_queues_result_instead_of_calling_tk_from_thread(monkeypatch):
    app = YouTubeDownloaderUI.__new__(YouTubeDownloaderUI)
    app.ui_queue = queue.Queue()

    monkeypatch.setattr(
        "youtube_downloader.fetch_latest_release",
        lambda: {"available": True, "version": "1.0.0", "url": GITHUB_RELEASES_PAGE},
    )

    app._check_for_updates_worker(silent=True)

    callback, args = app.ui_queue.get_nowait()
    assert callback.__name__ == "_apply_update_status"
    assert args[0]["state"] == "current"
    assert args[1] is True


def test_common_download_options_use_explicit_quality_without_reading_tk_var(tmp_path):
    app = YouTubeDownloaderUI.__new__(YouTubeDownloaderUI)
    app.quality_var = type("ExplodingVar", (), {"get": lambda _self: (_ for _ in ()).throw(RuntimeError("tk access"))})()

    opts = app._build_common_opts(str(tmp_path), "ffmpeg.exe", "720p")

    assert opts["format"] == "bv*[height<=720]+ba/b[height<=720]/best[height<=720]/best"


def test_status_label_has_fixed_width_for_stable_progress_layout():
    root = ctk.CTk()
    root.withdraw()
    try:
        app = YouTubeDownloaderUI(root)
        root.update()

        assert app.status_label.cget("width") == 300
    finally:
        root.destroy()
