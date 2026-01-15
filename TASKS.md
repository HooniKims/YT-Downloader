# YouTube Downloader 개발 기록

## 프로젝트 개요
YouTube 동영상을 고화질로 다운로드할 수 있는 GUI 기반 다운로더 프로그램

## 개발 환경
- Python 3.12
- yt-dlp (yt-dlp-ejs 플러그인 포함)
- ffmpeg (영상/음성 병합용)
- tkinter (GUI)

---

## Phase 1: 초기 복구 (2026-01-16)

### 문제 상황
- 깃허브의 구버전 코드로 로컬 파일이 덮어씌워짐
- 로컬에 있던 최신 코드(617라인)가 구버전(355라인)으로 대체됨

### 해결
- [x] 메모리에 남아있던 최신 코드를 기반으로 `youtube_downloader.py` 파일 복구
- [x] 로깅, 자동 업데이트, 로딩 화면 기능 포함된 버전으로 복원

---

## Phase 2: yt-dlp 라이브러리 오류 해결 (2026-01-16)

### 문제 상황
- `ImportError: cannot import name 'yt_dlp_ejs' from 'yt_dlp.dependencies'` 오류 발생
- 다운로드 기능이 완전히 작동하지 않음

### 해결
- [x] `pip install --upgrade --force-reinstall yt-dlp` 명령으로 라이브러리 재설치
- [x] 라이브러리 파일 손상 문제 해결

---

## Phase 3: 고화질 다운로드 문제 해결 (2026-01-16)

### 문제 상황
- 최고 화질을 선택해도 360p(가로 640px)로만 다운로드됨
- 유튜브의 SABR(Streaming ABR) 제한으로 고화질 스트림 URL이 차단됨

### 원인 분석
1. **SABR 제한**: 유튜브가 고화질 스트림의 URL을 숨기거나 차단
2. **오디오 포맷 부재**: 비디오만 다운로드되고 오디오가 없어서 병합 실패
3. **폴백 동작**: 비디오+오디오 병합 실패 시 단일 파일인 360p(ID 18)로 폴백

### 해결
- [x] `yt-dlp[default]` 패키지 설치 (yt-dlp-ejs 플러그인 포함)
- [x] 프로그램 시작 시 자동으로 `yt-dlp[default]` 업데이트하도록 코드 수정
- [x] 터미널에서 성공한 설정과 동일하게 최소한의 설정만 적용
- [x] `check_formats` 옵션 제거 (포맷 사전 검증 오류 방지)

---

## Phase 4: 실행 파일(exe) 자동 업데이트 기능 추가 (2026-01-16)

### 문제 상황
- PyInstaller로 빌드된 exe 파일은 내장된 yt-dlp 버전을 사용
- 유튜브 정책 변경 시 다시 빌드해야 하는 불편함

### 해결
- [x] 실행 파일 모드에서 외부 `yt-dlp.exe` 사용하도록 수정
- [x] 시작 시 GitHub에서 최신 `yt-dlp.exe` 자동 다운로드
- [x] 기존 `yt-dlp.exe`가 있으면 `-U` 옵션으로 자체 업데이트
- [x] 다운로드 시 subprocess로 외부 `yt-dlp.exe` 호출

### 핵심 함수
```python
def get_ytdlp_exe_path():
    """yt-dlp.exe 경로 반환 (외부 다운로드된 버전 우선)"""
    
def download_latest_ytdlp_exe():
    """GitHub에서 최신 yt-dlp.exe 다운로드"""
```

### 작동 흐름
```
exe 실행
   ↓
yt-dlp.exe 있음? → 있음 → yt-dlp.exe -U (자체 업데이트)
   ↓ 없음
GitHub에서 다운로드
   ↓
다운로드 시 외부 yt-dlp.exe subprocess 호출
```

---

## Phase 5: 로그 폴더 생성 비활성화 (2026-01-16)

### 문제 상황
- exe 실행 시 `logs` 폴더가 자동 생성됨
- 불필요한 파일 생성으로 배포 환경이 지저분해짐

### 해결
- [x] 실행 파일 모드에서 파일 로깅 비활성화
- [x] 콘솔 출력만 사용하도록 수정
- [x] 개발 모드에서는 기존처럼 로그 파일 생성 유지

```python
def setup_logging():
    if getattr(sys, 'frozen', False):
        # 실행 파일 모드: 콘솔 출력만
        handlers=[logging.StreamHandler()]
    else:
        # 개발 모드: 파일 + 콘솔 출력
        handlers=[FileHandler, StreamHandler]
```

---

## 현재 상태 (2026-01-16)

### 작동 확인
- [x] 프로그램 시작 시 yt-dlp 자동 업데이트
- [x] 1080p 비디오 + 고품질 오디오 다운로드 및 병합 성공
- [x] MP4 포맷으로 최종 파일 저장
- [x] exe 모드에서 외부 yt-dlp.exe 자동 다운로드 및 사용
- [x] exe 모드에서 logs 폴더 생성 안 됨

### 테스트 결과
- 테스트 영상: `https://youtu.be/cwOXdmJdLgU`
- 다운로드된 파일: 1080p (32.15MB 비디오 + 20.43MB 오디오 병합)

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| 언어 | Python 3.12 |
| GUI | tkinter |
| 다운로드 | yt-dlp (개발모드) / yt-dlp.exe (배포모드) |
| 영상 처리 | ffmpeg |
| 빌드 | PyInstaller |

---

## 파일 구조

```
YT-Downloader-main/
├── youtube_downloader.py   # 메인 프로그램
├── youtube_downloader.spec # PyInstaller 빌드 설정
├── readme.md               # 빌드 가이드
├── TASKS.md                # 개발 기록 (본 문서)
├── ffmpeg.exe              # ffmpeg 실행 파일
├── ffprobe.exe             # ffprobe 실행 파일
├── *.dll                   # ffmpeg 관련 DLL 파일들
├── youricon.ico            # 프로그램 아이콘
├── dist/                   # 빌드된 exe 파일
│   └── youtube_downloader.exe
└── logs/                   # 다운로드 로그 폴더 (개발 모드만)
```

---

## 배포 시 주의사항

### exe 파일 배포
1. `dist/youtube_downloader.exe` 파일만 배포
2. 첫 실행 시 자동으로 `yt-dlp.exe` 다운로드됨
3. ffmpeg는 exe 안에 내장되어 있음

### 자동 업데이트 동작
- 시작할 때마다 yt-dlp.exe 업데이트 확인
- 최신 버전이면 스킵, 구버전이면 자동 업데이트
- 인터넷 연결 필요

---

## 향후 개선 사항
- [ ] 다운로드 진행률 표시 개선.
- [ ] 다중 영상 동시 다운로드 기능
- [ ] 업데이트 실패 시 사용자 알림 개선
