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

### 핵심 수정 사항

#### 1. 자동 업데이트 함수 수정 (`check_and_update_ytdlp`)
```python
# 변경 전
pip install --upgrade yt-dlp

# 변경 후
pip install --upgrade yt-dlp[default]  # yt-dlp-ejs 플러그인 포함
```

#### 2. 설정 간소화 (`get_latest_ytdlp_config`)
```python
# 터미널에서 성공한 설정과 동일하게 최소한의 설정만 적용
return {
    'nocheckcertificate': True,
    'youtube_include_dash_manifest': True,
    'youtube_include_hls_manifest': True,
}
```

#### 3. 다운로드 옵션 수정 (`_build_common_opts`)
- `check_formats` 옵션 제거
- `ignoreerrors: False`로 변경하여 오류 발생 시 바로 확인 가능

---

## 현재 상태 (2026-01-16)

### 작동 확인
- [x] 프로그램 시작 시 yt-dlp 및 yt-dlp-ejs 플러그인 자동 업데이트
- [x] 1080p 비디오 + 고품질 오디오 다운로드 및 병합 성공
- [x] MP4 포맷으로 최종 파일 저장

### 테스트 결과
- 테스트 영상: `https://youtu.be/cwOXdmJdLgU`
- 다운로드된 파일: 1080p (32.15MB 비디오 + 20.43MB 오디오 병합)

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| 언어 | Python 3.12 |
| GUI | tkinter |
| 다운로드 | yt-dlp (yt-dlp-ejs 플러그인) |
| 영상 처리 | ffmpeg |
| 로깅 | logging 모듈 |

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
└── logs/                   # 다운로드 로그 폴더
```

---

## 향후 개선 사항
- [ ] PyInstaller 빌드 시 yt-dlp-ejs 플러그인 포함 방법 연구
- [ ] 다운로드 진행률 표시 개선
- [ ] 다중 영상 동시 다운로드 기능
