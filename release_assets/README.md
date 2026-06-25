# 릴리즈 업로드 파일 보관 폴더

GitHub Releases에 올릴 파일을 임시로 모아두는 폴더입니다.

릴리즈를 만들 때 권장 흐름:

1. `APP_VERSION`을 새 버전으로 올립니다.
2. 테스트를 실행합니다.
3. `python -m PyInstaller .\youtube_downloader.spec --noconfirm --clean`로 빌드합니다.
4. `dist\youtube_downloader.exe`를 이 폴더에 복사합니다.
5. GitHub Releases에서 `vX.Y.Z` 태그를 만들고 이 exe를 첨부합니다.

권장 첨부 파일명:

```text
youtube_downloader-vX.Y.Z.exe
```

앱의 업데이트 확인 기능은 GitHub Releases 최신 릴리즈 페이지를 엽니다. 사용자는 그 페이지에서 exe를 다운로드한 뒤, 실행 중인 프로그램을 종료하고 기존 exe를 새 파일로 교체합니다.

