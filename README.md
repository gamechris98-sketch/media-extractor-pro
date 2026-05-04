# Media Extractor Pro Web 🚀

Premium web-based batch media downloader powered by **FastAPI** and **yt-dlp**. Featuring a sleek iOS-inspired Glassmorphism UI.

[한국어 설명은 아래에 있습니다]

## Key Features
- **Modern UI**: iOS 17 style Glassmorphism with smooth animations.
- **Full Responsive**: Perfectly optimized for PC, Tablet, and Mobile browsers.
- **Batch Processing**: Download multiple videos/audios simultaneously.
- **Live Updates**: Real-time progress tracking via WebSockets.
- **Format Toggle**: Extract high-quality MP4 video or MP3 audio.

## Installation & Run

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/media-extractor-pro.git
   cd media-extractor-pro
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg** (Required for merging video/audio and MP3 conversion)
   - Windows: `choco install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - macOS: `brew install ffmpeg`

4. **Run the application**
   ```bash
   python app.py
   ```
   Open `http://localhost:8000` in your browser.

---

## 주요 기능
- **모던 UI**: iOS 17 스타일의 Glassmorphism과 부드러운 애니메이션 적용.
- **반응형 디자인**: PC, 태블릿, 모바일 모든 환경에 최적화된 화면.
- **일괄 처리**: 여러 URL을 한 번에 입력하여 연속 다운로드 가능.
- **실시간 로그**: WebSocket을 통한 다운로드 진행률 및 상태 실시간 표시.
- **포맷 선택**: 고화질 MP4 영상 또는 MP3 음원 추출 지원.

## 실행 방법

1. **저장소 클론**
   ```bash
   git clone https://github.com/your-username/media-extractor-pro.git
   cd media-extractor-pro
   ```

2. **필수 라이브러리 설치**
   ```bash
   pip install -r requirements.txt
   ```

3. **FFmpeg 설치** (영상/음성 병합 및 MP3 변환 필수)
   - Windows: `choco install ffmpeg` 또는 [ffmpeg.org](https://ffmpeg.org/download.html)에서 직접 다운로드
   - macOS: `brew install ffmpeg`

4. **프로그램 실행**
   ```bash
   python app.py
   ```
   브라우저에서 `http://localhost:8000`에 접속하세요.

## License
MIT License.
