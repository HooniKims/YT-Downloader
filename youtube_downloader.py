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
import logging
from datetime import datetime
import subprocess
import json
import multiprocessing


def setup_logging():
    """로깅 설정 초기화"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_filename = os.path.join(log_dir, f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return log_filename


def check_and_update_ytdlp():
    """yt-dlp 자동 업데이트 확인 및 실행 (yt-dlp-ejs 플러그인 포함)"""
    # PyInstaller로 빌드된 실행 파일인 경우 업데이트 건너뛰기
    if getattr(sys, 'frozen', False):
        logging.info("실행 파일 모드: yt-dlp 업데이트 건너뜀 (내장 버전 사용)")
        return True

    try:
        logging.info("yt-dlp 업데이트 확인 중... (yt-dlp-ejs 플러그인 포함)")
        # yt-dlp[default]를 설치하면 yt-dlp-ejs 플러그인이 함께 설치됨
        # 이 플러그인은 유튜브의 SABR 제한을 우회하여 고화질 다운로드를 가능하게 함
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp[default]"],
            capture_output=True,
            text=True,
            timeout=60,  # 플러그인 설치에 시간이 더 걸릴 수 있음
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        if "Successfully installed" in result.stdout or "Requirement already satisfied" in result.stdout:
            logging.info("yt-dlp 및 yt-dlp-ejs 플러그인 업데이트 완료")
            return True
        else:
            logging.warning("yt-dlp 업데이트 확인 중 경고 발생")
            return True
    except Exception as e:
        logging.error(f"yt-dlp 업데이트 실패: {e}")
        return False


def get_latest_ytdlp_config():
    """최신 yt-dlp 설정을 반환 (유튜브 고화질 제한 우회 및 404 대응)"""
    # 터미널에서 성공한 설정과 동일하게 최소한의 설정만 적용
    return {
        'nocheckcertificate': True,
        'youtube_include_dash_manifest': True,
        'youtube_include_hls_manifest': True,
    }



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

        # 로깅 초기화
        self.log_filename = setup_logging()
        logging.info("YouTube Downloader 시작")
        logging.info(f"로그 파일: {self.log_filename}")

        # 상태 변수
        self.is_downloading = False
        self._download_cancelled = False
        self._current_temp_files = []
        self.auto_update_on_start = True  # 시작 시 자동 업데이트 활성화
        self.initialization_complete = False

        # UI 변수
        self.thumbnail_img = None
        self.thumbnail_label = None
        self.url_menu = None
        self.url_var = tk.StringVar()
        # 기본 다운로드 경로를 바탕화면으로 설정
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        self.path_var = tk.StringVar(value=desktop_path)
        self.quality_var = tk.StringVar(value="bestvideo+bestaudio")
        self.progress_var = tk.StringVar(value="대기 중...")

        # 시작 시 로딩 화면 표시
        if self.auto_update_on_start:
            self.show_loading_screen()
        else:
            self.create_widgets()

    def show_loading_screen(self):
        """시작 시 로딩 화면 표시"""
        # 로딩 프레임 생성
        self.loading_frame = ttk.Frame(self.root, padding="50")
        self.loading_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 제목
        title_label = ttk.Label(
            self.loading_frame,
            text="YouTube Downloader by HooniKim",
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, pady=(0, 30))

        # 상태 메시지
        self.loading_status = tk.StringVar(value="초기화 중...")
        status_label = ttk.Label(
            self.loading_frame,
            textvariable=self.loading_status,
            font=("Arial", 11)
        )
        status_label.grid(row=1, column=0, pady=(0, 20))

        # 진행 바
        self.loading_progress = ttk.Progressbar(
            self.loading_frame,
            mode='indeterminate',
            length=300
        )
        self.loading_progress.grid(row=2, column=0, pady=(0, 20))
        self.loading_progress.start(10)

        # 상세 정보 텍스트
        self.loading_detail = tk.StringVar(value="프로그램을 준비하고 있습니다...")
        detail_label = ttk.Label(
            self.loading_frame,
            textvariable=self.loading_detail,
            font=("Arial", 9),
            foreground="gray"
        )
        detail_label.grid(row=3, column=0)

        # Grid 설정
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # 백그라운드에서 초기화 시작
        threading.Thread(target=self.initialize_app, daemon=True).start()

    def initialize_app(self):
        """앱 초기화 (업데이트 확인 포함)"""
        try:
            import time

            # 실행 파일 모드인지 확인
            is_frozen = getattr(sys, 'frozen', False)

            if is_frozen:
                # 실행 파일 모드
                self.loading_status.set("프로그램 초기화 중...")
                self.loading_detail.set("YouTube Downloader를 준비하고 있습니다...")
                time.sleep(1)
            else:
                # 개발 모드: 업데이트 확인
                # 1단계: yt-dlp 버전 확인
                self.loading_status.set("yt-dlp 버전 확인 중...")
                self.loading_detail.set("현재 설치된 yt-dlp 버전을 확인하고 있습니다...")
                time.sleep(0.5)

                # 2단계: yt-dlp 업데이트
                self.loading_status.set("yt-dlp 업데이트 확인 중...")
                self.loading_detail.set("최신 버전으로 업데이트하고 있습니다. 잠시만 기다려주세요...")

                if check_and_update_ytdlp():
                    self.loading_detail.set("yt-dlp 최신 버전 확인 완료!")
                    logging.info("yt-dlp 최신 버전 확인 완료")
                else:
                    self.loading_detail.set("업데이트 확인 실패 (기존 버전 사용)")
                    logging.warning("yt-dlp 업데이트 확인 실패")

                time.sleep(1)

            # 3단계: UI 로딩
            self.loading_status.set("UI 준비 중...")
            self.loading_detail.set("사용자 인터페이스를 불러오고 있습니다...")
            time.sleep(0.5)

            # 초기화 완료
            self.initialization_complete = True
            self.loading_status.set("준비 완료!")
            self.loading_detail.set("YouTube Downloader를 시작합니다...")
            time.sleep(0.5)

            # 메인 UI로 전환
            self.root.after(0, self.show_main_ui)

        except Exception as e:
            logging.error(f"초기화 중 오류 발생: {e}")
            self.loading_status.set("초기화 오류")
            self.loading_detail.set(f"오류가 발생했습니다: {str(e)[:50]}")
            # 오류가 발생해도 5초 후 메인 UI 표시
            time.sleep(5)
            self.root.after(0, self.show_main_ui)

    def show_main_ui(self):
        """로딩 화면을 숨기고 메인 UI 표시"""
        # 로딩 화면 제거
        if hasattr(self, 'loading_frame'):
            self.loading_progress.stop()
            self.loading_frame.destroy()

        # 메인 위젯 생성
        self.create_widgets()

        # 로그에 초기화 완료 메시지 추가
        self.log_message("=" * 50)
        self.log_message("YouTube Downloader 준비 완료!")
        self.log_message("초기화가 완료되었습니다. 다운로드를 시작할 수 있습니다.")
        self.log_message("=" * 50)

    def check_updates_background(self):
        """백그라운드에서 yt-dlp 업데이트 확인"""
        self.log_message("yt-dlp 업데이트 확인 중...")
        if check_and_update_ytdlp():
            self.log_message("yt-dlp 최신 버전 확인 완료")
        else:
            self.log_message("yt-dlp 업데이트 확인 실패 (기존 버전 사용)")

    def log_message(self, message):
        """로그 영역에 메시지 추가"""
        logging.info(message)
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
        # 초기화가 완료되지 않았으면 경고
        if not self.initialization_complete:
            messagebox.showwarning("알림", "프로그램 초기화 중입니다. 잠시만 기다려주세요.")
            return

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
        # 최신 yt-dlp 설정 자동 적용
        latest_config = get_latest_ytdlp_config()

        opts = {
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'), # 채널 폴더 제외하고 바로 저장
            'progress_hooks': [self.progress_hook],
            'nocheckcertificate': True,
            'ignoreerrors': False,  # 오류 발생 시 바로 알 수 있도록 변경
            'windowsfilenames': True,
            'retries': 10,
            'fragment_retries': 10,
            'nooverwrites': False, # 강제 덮어쓰기
            'writethumbnail': False,
        }


        # 최신 설정 병합
        opts.update(latest_config)

        if ffmpeg_path:
            opts['ffmpeg_location'] = ffmpeg_path
        return opts

    def download_video(self, url):
        retry_count = 0
        max_retries = 2

        while retry_count <= max_retries:
            try:
                output_path = self.path_var.get() or "downloads"
                ffmpeg_path = get_ffmpeg_path()
                quality = self.quality_var.get()

                if retry_count > 0:
                    self.log_message(f"재시도 중... ({retry_count}/{max_retries})")
                
                self.log_message("다운로드 준비 중...")
                
                # 다운로드 옵션 설정
                ydl_opts = self._build_common_opts(output_path, ffmpeg_path)
                
                # 품질에 따른 포맷 설정
                # 핵심: 수동 분석 대신 yt-dlp의 강력한 포맷 선택 기능 사용
                if quality == "bestvideo+bestaudio":
                    # 1080p MP4 비디오(137) + M4A 오디오(140)를 1차로 시도
                    # 실패하면 자동으로 최고 화질 선택
                    ydl_opts['format'] = "137+140/bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
                    ydl_opts['merge_output_format'] = 'mp4'
                    self.log_message("최고 화질(1080p) 다운로드 시도...")
                    
                elif quality == "best":
                    ydl_opts['format'] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
                    ydl_opts['merge_output_format'] = 'mp4'
                    
                elif quality == "720p":
                    ydl_opts['format'] = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]"
                    ydl_opts['merge_output_format'] = 'mp4'
                    
                elif quality == "480p":
                    ydl_opts['format'] = "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]"
                    ydl_opts['merge_output_format'] = 'mp4'
                    
                elif quality == "bestaudio/best":
                    ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio/best'
                    ydl_opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }]
                else:
                    ydl_opts['format'] = quality

                # 다운로드 실행
                self.log_message(f"다운로드 시작... (포맷: {ydl_opts['format'][:50]}...)")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                if not self._download_cancelled:
                    self.log_message("다운로드 및 후처리 완료!")
                    self.progress_var.set("완료!")
                    break

            except yt_dlp.utils.DownloadError as e:
                if "사용자에 의해" in str(e):
                    self.log_message("다운로드가 중지되었습니다.")
                    self.progress_var.set("다운로드 정지됨")
                    break
                else:
                    error_msg = f"다운로드 오류: {e}"
                    self.log_message(error_msg)
                    logging.error(error_msg)
                    logging.error(f"전체 오류 상세: {str(e)}")

                    # 404 오류인 경우 자동 재시도
                    if "404" in str(e) or "HTTP Error" in str(e):
                        if retry_count < max_retries:
                            retry_count += 1
                            self.log_message(f"HTTP 오류 감지. yt-dlp 업데이트 후 재시도합니다...")
                            check_and_update_ytdlp()
                            continue

                    messagebox.showerror("다운로드 오류", f"오류가 발생했습니다:\n{e}")
                    break

            except Exception as e:
                error_msg = f"알 수 없는 오류: {e}"
                self.log_message(error_msg)
                logging.error(error_msg)
                logging.exception("예외 상세 정보:")

                if retry_count < max_retries:
                    retry_count += 1
                    continue

                messagebox.showerror("알 수 없는 오류", f"예상치 못한 오류가 발생했습니다:\n{e}")
                break

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
    # Windows에서 PyInstaller로 빌드할 때 multiprocessing 무한 루프 방지
    multiprocessing.freeze_support()
    main()
