import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import yt_dlp
import threading
import os
import sys
from PIL import Image, ImageTk
import urllib.request
import io

def get_ffmpeg_path():
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller로 빌드된 경우 임시폴더에서 ffmpeg.exe 사용
        return os.path.join(sys._MEIPASS, "ffmpeg.exe")
    else:
        # 개발 환경에서는 현재 폴더에서 ffmpeg.exe 사용
        return os.path.join(os.path.dirname(sys.argv[0]), "ffmpeg.exe")

class YouTubeDownloaderUI:
    def log_message(self, message):
        if hasattr(self, 'log_text'):
            self.log_text.insert(tk.END, f"{message}\n")
            self.log_text.see(tk.END)
            self.root.update()
    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader by HooniKim")
        self.root.geometry("600x600")
        # 다운로드 상태 변수
        self.is_downloading = False
        self._download_cancelled = False
        self._current_temp_files = []

        self.thumbnail_img = None
        self.thumbnail_label = None

        self.create_widgets()
        
    def create_widgets(self):
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # URL 입력
        ttk.Label(main_frame, text="YouTube URL:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(main_frame, textvariable=self.url_var, width=60)
        self.url_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # URL 입력란 우클릭 컨텍스트 메뉴 추가
        self.url_menu = tk.Menu(self.root, tearoff=0)
        self.url_menu.add_command(label="잘라내기", command=lambda: self.url_entry.event_generate('<<Cut>>'))
        self.url_menu.add_command(label="복사", command=lambda: self.url_entry.event_generate('<<Copy>>'))
        self.url_menu.add_command(label="붙여넣기", command=lambda: self.url_entry.event_generate('<<Paste>>'))
        self.url_entry.bind("<Button-3>", self.show_url_menu)

        # 썸네일 표시 라벨 (초기에는 빈 상태)
        self.thumbnail_label = ttk.Label(main_frame)
        self.thumbnail_label.grid(row=2, column=0, columnspan=2, pady=(0, 10))

        # URL 입력란에 값이 변경될 때마다 썸네일 업데이트
        self.url_var.trace_add('write', self.update_thumbnail)
    def update_thumbnail(self, *args):
        url = self.url_var.get().strip()
        thumb_url = self.extract_thumbnail_url(url)
        if thumb_url:
            try:
                with urllib.request.urlopen(thumb_url) as u:
                    raw_data = u.read()
                im = Image.open(io.BytesIO(raw_data))
                im = im.resize((320, 180))
                self.thumbnail_img = ImageTk.PhotoImage(im)
                self.thumbnail_label.config(image=self.thumbnail_img)
            except Exception:
                self.thumbnail_label.config(image='')
        else:
            self.thumbnail_label.config(image='')

    def extract_thumbnail_url(self, url):
        # YouTube URL에서 영상 ID 추출
        import re
        match = re.search(r'(?:v=|youtu.be/)([\w-]{11})', url)
        if match:
            video_id = match.group(1)
            return f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg'
        return None

    # ...existing code...

    # ...existing code...

    def create_widgets(self):
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        # URL 입력
        ttk.Label(main_frame, text="YouTube URL:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(main_frame, textvariable=self.url_var, width=60)
        self.url_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # URL 입력란 우클릭 컨텍스트 메뉴 추가
        self.url_menu = tk.Menu(self.root, tearoff=0)
        self.url_menu.add_command(label="잘라내기", command=lambda: self.url_entry.event_generate('<<Cut>>'))
        self.url_menu.add_command(label="복사", command=lambda: self.url_entry.event_generate('<<Copy>>'))
        self.url_menu.add_command(label="붙여넣기", command=lambda: self.url_entry.event_generate('<<Paste>>'))
        self.url_entry.bind("<Button-3>", self.show_url_menu)

        # 출력 경로
        ttk.Label(main_frame, text="다운로드 경로:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))

        path_frame = ttk.Frame(main_frame)
        path_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.path_var = tk.StringVar(value="downloads")
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=50)
        self.path_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))

        self.browse_button = ttk.Button(path_frame, text="찾아보기", command=self.browse_folder)
        self.browse_button.grid(row=0, column=1, padx=(5, 0))

        # 품질 설정
        quality_frame = ttk.LabelFrame(main_frame, text="품질 설정", padding="5")
        quality_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.quality_var = tk.StringVar(value="bestvideo+bestaudio")
        quality_options = [
            ("최고 품질 (병합 필요 - ffmpeg 필요)", "bestvideo+bestaudio"),
            ("최고 품질 (단일 파일)", "best"),
            ("720p", "best[height<=720]"),
            ("480p", "best[height<=480]"),
            ("음성만 (mp3)", "bestaudio/best")
        ]

        for i, (text, value) in enumerate(quality_options):
            ttk.Radiobutton(quality_frame, text=text, variable=self.quality_var, 
                           value=value).grid(row=i, column=0, sticky=tk.W, pady=2)

        # 다운로드 버튼
        self.download_button = ttk.Button(main_frame, text="다운로드 시작", 
                                        command=self.start_download)
        self.download_button.grid(row=5, column=0, pady=(0, 10))

        # 정지 버튼
        self.stop_button = ttk.Button(main_frame, text="정지", 
                                    command=self.stop_download, state="disabled")
        self.stop_button.grid(row=5, column=1, pady=(0, 10), padx=(5, 0))

        # 진행률 바
        self.progress_var = tk.StringVar(value="대기 중...")
        ttk.Label(main_frame, textvariable=self.progress_var).grid(row=6, column=0, columnspan=2, sticky=tk.W)

        self.progress_bar = ttk.Progressbar(main_frame, mode='determinate', maximum=100)
        self.progress_bar.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 10))

        # 로그 출력
        ttk.Label(main_frame, text="로그:").grid(row=8, column=0, sticky=tk.W, pady=(0, 5))
        self.log_text = scrolledtext.ScrolledText(main_frame, height=10, width=70)
        self.log_text.grid(row=9, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 그리드 가중치 설정
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(9, weight=1)
        path_frame.columnconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

    def show_url_menu(self, event):
        try:
            self.url_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.url_menu.grab_release()

    def progress_hook(self, d):
        """yt-dlp 진행률 콜백"""
        if self._download_cancelled:
            raise yt_dlp.utils.DownloadCancelled('사용자에 의해 다운로드가 중지되었습니다.')
        if d['status'] == 'downloading':
            # 임시 파일 경로 추적
            tmpfilename = d.get('tmpfilename')
            if tmpfilename and tmpfilename not in self._current_temp_files:
                self._current_temp_files.append(tmpfilename)
            if 'total_bytes' in d:
                percent = d['downloaded_bytes'] / d['total_bytes'] * 100
                self.progress_var.set(f"다운로드 중... {percent:.1f}%")
                self.progress_bar['value'] = percent
            else:
                self.progress_var.set("다운로드 중...")
                self.progress_bar['value'] = 0
        elif d['status'] == 'finished':
            self.progress_var.set("다운로드 완료!")
            self.progress_bar['value'] = 100
            self.log_message(f"완료: {d['filename']}")
    
    def start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("오류", "YouTube URL을 입력해주세요.")
            return

        if self.is_downloading:
            return

        # UI 상태 변경
        self.is_downloading = True
        self._download_cancelled = False
        self._current_temp_files = []
        self.download_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.progress_bar['value'] = 0
        self.progress_var.set("다운로드 준비 중...")

        # 별도 스레드에서 다운로드 실행
        thread = threading.Thread(target=self.download_video, args=(url,))
        thread.daemon = True
        thread.start()
    
    def stop_download(self):
        """다운로드 즉시 중지 및 임시 파일 삭제"""
        self._download_cancelled = True
        self.is_downloading = False
        self.download_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.progress_bar['value'] = 0
        self.progress_var.set("다운로드 정지됨")

        # 임시 파일 삭제
        deleted_files = []
        for f in self._current_temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
                    deleted_files.append(f)
            except Exception:
                pass
        if deleted_files:
            self.log_message(f"중지됨: 임시 파일 삭제 완료 ({', '.join(deleted_files)})")
    
    def download_video(self, url):
        try:
            # 출력 경로 설정
            output_path = self.path_var.get()
            if not output_path:
                output_path = "downloads"

            # ffmpeg.exe 경로 자동 지정 (PyInstaller 임시폴더 또는 프로그램 폴더)
            ffmpeg_path = get_ffmpeg_path()
            ffmpeg_exists = os.path.isfile(ffmpeg_path)

            # yt-dlp 옵션 설정
            quality = self.quality_var.get()
            ydl_opts = {}
            if quality == "bestvideo+bestaudio":
                ydl_opts = {
                    'format': 'bestvideo+bestaudio/best',
                    'outtmpl': os.path.join(output_path, '%(uploader)s/%(title)s.%(ext)s'),
                    'merge_output_format': 'mp4',
                    'progress_hooks': [self.progress_hook]
                }
            elif quality == "bestaudio/best":
                ydl_opts = {
                    'format': quality,
                    'outtmpl': os.path.join(output_path, '%(uploader)s - %(title)s.%(ext)s'),
                    'progress_hooks': [self.progress_hook],
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192'
                    }]
                }
            else:
                ydl_opts = {
                    'format': quality,
                    'outtmpl': os.path.join(output_path, '%(uploader)s - %(title)s.%(ext)s'),
                    'progress_hooks': [self.progress_hook]
                }

            # ffmpeg.exe가 있으면 yt-dlp 옵션에 경로 추가
            if ffmpeg_exists:
                ydl_opts['ffmpeg_location'] = ffmpeg_path

            # 영상 정보 먼저 추출 및 로그 출력
            try:
                with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                title = info.get('title', 'Unknown')
                uploader = info.get('uploader', '')
                duration = info.get('duration', '')
                view_count = info.get('view_count', '')
                self.log_message(f"영상 정보: 제목: {title}, 채널: {uploader}, 길이: {duration}s, 조회수: {view_count}")
            except Exception as e:
                self.log_message(f"영상 정보 추출 실패: {str(e)}")

            # 실제 다운로드 실행
            self.log_message(f"다운로드 시작: {url}")
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = info.get('title', 'Unknown')
                    self.log_message(f"성공적으로 다운로드됨: {title}")
            except yt_dlp.utils.DownloadCancelled:
                self.log_message("다운로드가 중지되었습니다.")
            except Exception as e:
                self.log_message(f"오류 발생: {str(e)}")
                messagebox.showerror("다운로드 오류", f"다운로드 중 오류가 발생했습니다:\n{str(e)}")
        finally:
            # UI 상태 복원
            self.is_downloading = False
            self.download_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.progress_bar['value'] = 0
            if not hasattr(self, '_download_completed'):
                self.progress_var.set("완료")

# 프로그램 실행 진입점 (파일 맨 아래에 추가)
def main():
    root = tk.Tk()
    app = YouTubeDownloaderUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()