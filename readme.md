# 유튜브 다운로더

Windows용 유튜브 다운로더입니다. 링크를 넣으면 썸네일을 미리 보여주고, 기본값은 `최고 화질 (추천, 영상+음성)`입니다. `ffmpeg.exe`와 `ffprobe.exe`를 포함해 단일 exe로 빌드합니다.

## 사용자 안내

1. `youtube_downloader.exe`를 실행합니다.
2. 유튜브 링크를 붙여넣습니다.
3. 저장 위치와 화질을 선택합니다.
4. `다운로드 시작`을 누릅니다.

업데이트가 있는 경우 앱에 `새 버전 vX.Y.Z 사용 가능`이 표시됩니다. `업데이트 다운로드` 버튼이나 `도움말 > 릴리즈 페이지 열기`를 눌러 GitHub 릴리즈 페이지로 이동한 뒤, 새 `youtube_downloader.exe`를 다운로드하세요. 다운로드 후 현재 프로그램을 종료하고 기존 exe를 새 파일로 교체하면 됩니다.

## 개발 실행

```powershell
python youtube_downloader.py
```

## 테스트

```powershell
python -m pytest -q
```

## 단일 exe 빌드

```powershell
python -m PyInstaller .\youtube_downloader.spec --noconfirm --clean
```

빌드 결과는 다음 경로에 생성됩니다.

```text
dist\youtube_downloader.exe
```

## GitHub 업로드 전 릴리즈 준비

릴리즈에 첨부할 파일은 `release_assets` 폴더에 모아둡니다. 이 폴더는 GitHub Releases에 올릴 exe를 준비하기 위한 작업 폴더입니다.

권장 절차:

1. `youtube_downloader.py`의 `APP_VERSION`을 올립니다.
2. 테스트를 실행합니다.
3. PyInstaller로 exe를 다시 빌드합니다.
4. `dist\youtube_downloader.exe`를 `release_assets\youtube_downloader-vX.Y.Z.exe`로 복사합니다.
5. GitHub Releases에 `vX.Y.Z` 태그로 릴리즈를 만듭니다.
6. `release_assets`에 준비한 exe를 릴리즈 파일로 첨부합니다.

앱은 실행 직후 백그라운드에서 `https://api.github.com/repos/HooniKims/YT-Downloader/releases/latest`를 확인합니다. 최신 릴리즈 버전이 앱의 `APP_VERSION`보다 높으면 GitHub 릴리즈 페이지로 이동할 수 있는 버튼을 보여줍니다.

## 업데이트 방식

현재 업데이트는 자동 교체가 아니라 `업데이트 확인 + 릴리즈 페이지 안내` 방식입니다. Windows에서는 실행 중인 단일 exe가 자기 자신을 바로 덮어쓰기 어렵기 때문에, 초기 배포 방식으로는 수동 교체가 가장 안정적입니다.

나중에 완전 자동 업데이트가 필요하면 별도 updater exe 또는 임시 배치 파일 방식으로 확장할 수 있습니다.

