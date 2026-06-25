# AGENTS.md

## Project Overview

This is a Windows YouTube downloader built with Python, CustomTkinter, yt-dlp, and PyInstaller.

The app is distributed as a single Windows exe. `ffmpeg.exe`, `ffprobe.exe`, the app icon, CustomTkinter assets, and Paperlogy fonts are bundled through `youtube_downloader.spec`.

## Important Files

- `youtube_downloader.py`: main app source
- `youtube_downloader.spec`: PyInstaller one-file build spec
- `tests/test_downloader_core.py`: regression tests for download options, update checks, UI copy, and progress UI stability
- `dist/youtube_downloader.exe`: local build output, ignored by git
- `release_assets/`: local staging folder for files that will be attached to GitHub Releases
- `release_assets/README.md`: release asset preparation notes

## Versioning

The app version is defined in `youtube_downloader.py`:

```python
APP_VERSION = "1.0.0"
```

For a new public update, increment `APP_VERSION` before building.

Examples:

- Patch update: `1.0.0` to `1.0.1`
- Next patch: `1.0.1` to `1.0.2`

Do not change the version unless the user explicitly asks for a release/update version bump.

## Testing

Run tests before every commit and before every release build:

```powershell
python -m pytest -q
```

For cache-free verification:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest -q -p no:cacheprovider
```

## Build

Build the single exe with:

```powershell
python -m PyInstaller .\youtube_downloader.spec --noconfirm --clean
```

The output is:

```text
dist\youtube_downloader.exe
```

`dist/` and `build/` are generated folders and should not be committed.

## Update Release Flow

The app checks GitHub Releases:

```text
https://api.github.com/repos/HooniKims/YT-Downloader/releases/latest
```

If the latest release tag is newer than `APP_VERSION`, the app shows an update download button that opens:

```text
https://github.com/HooniKims/YT-Downloader/releases
```

The app does not auto-replace itself. Users manually download the new exe from GitHub Releases, close the running app, and replace the old exe.

## Preparing a Release Asset

After tests pass and the exe is built, copy the exe into `release_assets/` with a versioned filename:

```powershell
copy dist\youtube_downloader.exe release_assets\youtube_downloader-v1.0.1.exe
```

Then create a GitHub Release:

1. Go to `https://github.com/HooniKims/YT-Downloader/releases`.
2. Click `Draft a new release`.
3. Use a tag matching the app version, for example `v1.0.1`.
4. Attach `release_assets\youtube_downloader-v1.0.1.exe`.
5. Publish the release.

Do not delete old release files unless the user explicitly asks. Keeping old releases lets users roll back.

## GitHub Upload Rules

- Commit source, tests, build spec, fonts, ffmpeg/ffprobe, and release instructions.
- Do not commit `dist/`, `build/`, cache folders, or temporary download outputs.
- The built exe should be distributed through GitHub Releases, not normal git commits.
- `ffmpeg.exe` and `ffprobe.exe` are currently committed because the project expects bundled local binaries.

## UI Stability Notes

Tk widgets must only be touched from the main UI thread.

Download progress callbacks run from yt-dlp's download thread. They must queue UI work through `queue_ui()` and `process_ui_queue()` instead of directly changing Tk widgets or `StringVar`s.

Progress text should remain fixed-width enough to avoid layout jitter. Current format:

```text
다운로드  50.0% | 남은 00:02
```

When testing UI stability, verify the app window width and height do not change during download.

