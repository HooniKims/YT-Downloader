import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import yt_dlp
import threading
import os
import sys
from PIL import Image, ImageTk
import urllib.request
import io
import re


def get_ffmpeg_path():
    """PyInstaller 번들/개발 환경 모두에서 ffmpeg.exe 경로 추정"""
    # 1) PyInstaller 번들 임시 폴더
    if hasattr(sys, '_MEIPASS'):
        cand = os.path.join(sys._MEIPASS, "ffmpeg.exe")
        if os.path.isfile(cand):
            return cand
    # 2) 스크립트와 같은 폴더
    cand = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe")
    if os.path.isfile(cand):
        return cand
    # 3) PATH 상의 ffmpeg
    return "ffmpeg"  # 존재 여부는 실행 시 검증


class YouTubeDownloaderUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader by HooniKim")
        self.root.geometry("600x650")

        # 상태 변수
        self.is_downloading = False
        self._download_cancelled = False
        self._current_temp_files = []

        # UI 변수
        self.thumbnail_img = None
        self.thumbnail_label = None
        self.url_menu = None
        self.url_var = tk.StringVar()
        self.path_var = tk.StringVar(value="downloads")
        self.quality_var = tk.StringVar(value="bestvideo+bestaudio")
        self.progress_var = tk.StringVar(value="대기 중...")

        self.create_widgets()

    def log_message(self, message):
        """로그 영역에 메시지 추가"""
        if hasattr(self, 'log_text'):
            self.log_text.insert(tk.END, f"{message}\n")
            self.log_text.see(tk.END)
            self.root.update_idletasks()

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # URL 입력
        ttk.Label(main_frame, text="YouTube URL:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.url_entry = ttk.Entry(main_frame, textvariable=self.url_var, width=60)
        self.url_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # 우클릭 메뉴
        self.url_menu = tk.Menu(self.root, tearoff=0)
        self.url_menu.add_command(label="잘라내기", command=lambda: self.url_entry.event_generate('<<Cut>>'))
        self.url_menu.add_command(label="복사", command=lambda: self.url_entry.event_generate('<<Copy>>'))
        self.url_menu.add_command(label="붙여넣기", command=lambda: self.url_entry.event_generate('<<Paste>>'))
        self.url_entry.bind("<Button-3>", self.show_url_menu)

        # 썸네일
        self.thumbnail_label = ttk.Label(main_frame)
        self.thumbnail_label.grid(row=2, column=0, columnspan=2, pady=(0, 10))
        self.url_var.trace_add('write', self.update_thumbnail)

        # 다운로드 경로
        ttk.Label(main_frame, text="다운로드 경로:").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        path_frame = ttk.Frame(main_frame)
        path_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=50)
        self.path_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.browse_button = ttk.Button(path_frame, text="찾아보기", command=self.browse_folder)
        self.browse_button.grid(row=0, column=1, padx=(5, 0))

        # 품질 설정
        quality_frame = ttk.LabelFrame(main_frame, text="품질 설정", padding="5")
        quality_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        quality_options = [
            ("최고 품질 (병합 필요 - ffmpeg 필요)", "bestvideo+bestaudio"),
            ("최고 품질 (단일 파일)", "best"),
            ("720p (호환 우선)", "720p"),
            ("480p (호환 우선)", "480p"),
            ("음성만 (mp3)", "bestaudio/best")
        ]
        for i, (text, value) in enumerate(quality_options):
            ttk.Radiobutton(quality_frame, text=text, variable=self.quality_var, value=value).grid(row=i, column=0, sticky=tk.W, pady=2)

        # 버튼들
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        self.download_button = ttk.Button(button_frame, text="다운로드 시작", command=self.start_download)
        self.download_button.grid(row=0, column=0)
        self.stop_button = ttk.Button(button_frame, text="정지", command=self.stop_download, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=(5, 0))

        # 진행 표시
        ttk.Label(main_frame, textvariable=self.progress_var).grid(row=7, column=0, columnspan=2, sticky=tk.W)
        self.progress_bar = ttk.Progressbar(main_frame, mode='determinate', maximum=100)
        self.progress_bar.grid(row=8, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 10))

        # 로그
        ttk.Label(main_frame, text="로그:").grid(row=9, column=0, sticky=tk.W, pady=(0, 5))
        self.log_text = scrolledtext.ScrolledText(main_frame, height=10, width=70)
        self.log_text.grid(row=10, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Grid weight
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(10, weight=1)
        path_frame.columnconfigure(0, weight=1)

    def show_url_menu(self, event):
        try:
            self.url_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.url_menu.grab_release()

    def update_thumbnail(self, *args):
        url = self.url_var.get().strip()
        thumb_url = self.extract_thumbnail_url(url)
        if thumb_url:
            try:
                with urllib.request.urlopen(thumb_url) as u:
                    raw_data = u.read()
                im = Image.open(io.BytesIO(raw_data))
                im = im.resize((320, 180), Image.LANCZOS)
                self.thumbnail_img = ImageTk.PhotoImage(im)
                self.thumbnail_label.config(image=self.thumbnail_img)
            except Exception:
                self.thumbnail_label.config(image='')
        else:
            self.thumbnail_label.config(image='')

    def extract_thumbnail_url(self, url):
        video_id = None
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'youtu\.be\/([0-9A-Za-z_-]{11})'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                break
        if video_id:
            return f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg'
        return None

    def progress_hook(self, d):
        if self._download_cancelled:
            raise yt_dlp.utils.DownloadError('사용자에 의해 다운로드가 중지되었습니다.')

        if d['status'] == 'downloading':
            tmpfilename = d.get('tmpfilename')
            if tmpfilename and tmpfilename not in self._current_temp_files:
                self._current_temp_files.append(tmpfilename)

            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes:
                percent = d['downloaded_bytes'] / total_bytes * 100
                speed = d.get('speed')
                eta = d.get('eta')
                extra = []
                if speed:
                    extra.append(f"{speed/1024/1024:.2f} MB/s")
                if eta:
                    extra.append(f"남은 시간 ~{int(eta)}s")
                extra_txt = " | " + " / ".join(extra) if extra else ""
                self.progress_var.set(f"다운로드 중... {percent:.1f}%{extra_txt}")
                self.progress_bar['value'] = percent
            else:
                self.progress_var.set("다운로드 중...")
        elif d['status'] == 'finished':
            self.progress_var.set("후처리 중...")
            self.progress_bar['value'] = 100

    def start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("오류", "YouTube URL을 입력해주세요.")
            return
        if self.is_downloading:
            return

        self.is_downloading = True
        self._download_cancelled = False
        self._current_temp_files = []
        self.download_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.progress_bar['value'] = 0
        self.progress_var.set("다운로드 준비 중...")

        thread = threading.Thread(target=self.download_video, args=(url,))
        thread.daemon = True
        thread.start()

    def stop_download(self):
        if not self.is_downloading:
            return
        self._download_cancelled = True
        self.log_message("다운로드 중지 요청...")

    def _build_common_opts(self, output_path, ffmpeg_path):
        opts = {
            'outtmpl': os.path.join(output_path, '%(uploader)s/%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'windowsfilenames': True,
        }
        if ffmpeg_path:
            opts['ffmpeg_location'] = ffmpeg_path
        return opts

    def download_video(self, url):
        try:
            output_path = self.path_var.get() or "downloads"
            ffmpeg_path = get_ffmpeg_path()
            quality = self.quality_var.get()

            ydl_opts = self._build_common_opts(output_path, ffmpeg_path)

            # 형식/호환 프리셋 (메신저 호환을 위해 최종 mp4로 재인코딩)
            if quality == "bestvideo+bestaudio":
                ydl_opts['format'] = (
                    "(bv*[vcodec^=avc1]+ba[acodec^=mp4a])/"
                    "b[ext=mp4]/"
                    "bv*+ba/b"
                )
                ydl_opts['recodevideo'] = 'mp4'

            elif quality == "best":
                ydl_opts['format'] = "b[ext=mp4]/b"
                ydl_opts['recodevideo'] = 'mp4'

            elif quality == "720p":
                ydl_opts['format'] = (
                    "(bv[height<=720][vcodec^=avc1]+ba[acodec^=mp4a])/"
                    "b[height<=720][ext=mp4]/"
                    "b[height<=720]"
                )
                ydl_opts['recodevideo'] = 'mp4'

            elif quality == "480p":
                ydl_opts['format'] = (
                    "(bv[height<=480][vcodec^=avc1]+ba[acodec^=mp4a])/"
                    "b[height<=480][ext=mp4]/"
                    "b[height<=480]"
                )
                ydl_opts['recodevideo'] = 'mp4'

            elif quality == "bestaudio/best":
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]

            else:
                ydl_opts['format'] = quality
                ydl_opts['recodevideo'] = 'mp4'

            # 정보 로깅
            try:
                with yt_dlp.YoutubeDL({'quiet': True, 'nocheckcertificate': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                title = info.get('title', 'Unknown')
                uploader = info.get('uploader', 'Unknown')
                self.log_message(f"영상 정보: {title} / {uploader}")
            except Exception as e:
                self.log_message(f"영상 정보 추출 실패: {e}")

            # 다운로드 실행
            self.log_message(f"다운로드 시작: {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            if not self._download_cancelled:
                self.log_message("다운로드 및 후처리 완료!")
                self.progress_var.set("완료!")

        except yt_dlp.utils.DownloadError as e:
            if "사용자에 의해" in str(e):
                self.log_message("다운로드가 중지되었습니다.")
                self.progress_var.set("다운로드 정지됨")
            else:
                self.log_message(f"다운로드 오류: {e}")
                messagebox.showerror("다운로드 오류", f"오류가 발생했습니다:\n{e}")
        except Exception as e:
            self.log_message(f"알 수 없는 오류: {e}")
            messagebox.showerror("알 수 없는 오류", f"예상치 못한 오류가 발생했습니다:\n{e}")
        finally:
            # 임시 파일 정리
            for f in self._current_temp_files:
                try:
                    if f and os.path.exists(f):
                        os.remove(f)
                        self.log_message(f"임시 파일 삭제: {os.path.basename(f)}")
                except Exception as e:
                    self.log_message(f"임시 파일 삭제 실패: {e}")

            self.is_downloading = False
            self._download_cancelled = False
            self.download_button.config(state="normal")
            self.stop_button.config(state="disabled")
            if self.progress_var.get() not in ["완료!", "다운로드 정지됨"]:
                self.progress_var.set("대기 중...")
            self.progress_bar['value'] = 0


def main():
    root = tk.Tk()
    app = YouTubeDownloaderUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
