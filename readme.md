ffmpeg를 다운로드 후, 파이썬 파일과 같은 위치에 놓는다.
해당 위치에서 powershell을 관리자 권한으로 실행한 후 아래의 코드를 붙여넣기 한다.

pyinstaller --onefile --noconsole --add-data "ffmpeg.exe;." --icon="youricon.ico" youtube_downloader.py
