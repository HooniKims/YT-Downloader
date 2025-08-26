ffmpeg를 다운로드 후, 파이썬 파일과 같은 위치에 놓는다.

pyinstaller --onefile --noconsole --add-data "ffmpeg.exe;." --add-data "avcodec-62.dll;." --add-data "avdevice-62.dll;." --add-data "avfilter-11.dll;." --add-data "avformat-62.dll;." --add-data "avutil-60.dll;." --add-data "swresample-6.dll;." --add-data "swscale-9.dll;." --add-data "ffprobe.exe;." --icon="youricon.ico" youtube_downloader.py
