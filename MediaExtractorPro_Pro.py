import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import yt_dlp
import sys

class MediaExtractorPro(tk.Tk):
    def __init__(self):
        super().__init__()

        # 기본 설정
        self.title("Media Extractor Pro v2.5")
        self.geometry("700x850")
        self.configure(bg="#F2F2F7") # iOS 배경색
        self.resizable(False, False)

        # 폰트 설정
        if os.name == 'nt':
            self.font_main = "Segoe UI"
            self.font_bold = ("Segoe UI", 12, "bold")
            self.font_header = ("Segoe UI", 26, "bold")
        else:
            self.font_main = "Apple SD Gothic Neo"
            self.font_bold = ("Apple SD Gothic Neo", 12, "bold")
            self.font_header = ("Apple SD Gothic Neo", 26, "bold")

        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # 프로그레스바 스타일
        self.style.configure("Premium.Horizontal.TProgressbar", 
                             thickness=12, 
                             troughcolor='#E5E5EA', 
                             background='#007AFF', 
                             borderwidth=0)

        self.create_widgets()
        self.save_path = os.path.join(os.path.expanduser("~"), "Downloads")

    def create_widgets(self):
        # 상단 헤더
        header_frame = tk.Frame(self, bg="#FFFFFF", padx=40, pady=40)
        header_frame.pack(fill="x")
        
        tk.Label(header_frame, text="Media Extractor", font=self.font_header, 
                 fg="#1C1C1E", bg="#FFFFFF").pack(anchor="w")
        tk.Label(header_frame, text="Premium Batch Media Downloader", 
                 font=(self.font_main, 10, "bold"), fg="#8E8E93", bg="#FFFFFF").pack(anchor="w", pady=(5,0))

        # 메인 컨텐츠 영역
        content_frame = tk.Frame(self, bg="#F2F2F7", padx=40, pady=30)
        content_frame.pack(fill="both", expand=True)

        # 1. URL 입력 섹션
        tk.Label(content_frame, text="추출 대상 URL 목록", font=self.font_bold, 
                 fg="#1C1C1E", bg="#F2F2F7").pack(anchor="w", pady=(0, 10))
        
        input_wrapper = tk.Frame(content_frame, bg="#FFFFFF", padx=15, pady=15, 
                                 highlightthickness=1, highlightbackground="#D1D1D6")
        input_wrapper.pack(fill="x", pady=(0, 25))
        
        self.url_text = tk.Text(input_wrapper, height=7, font=(self.font_main, 11), 
                                 bg="#FFFFFF", fg="#1C1C1E", borderwidth=0, 
                                 highlightthickness=0, undo=True)
        self.url_text.pack(fill="x")
        self.url_text.insert("1.0", "여기에 유튜브 주소를 입력하세요 (여러 개 가능)")

        # 2. 설정 섹션
        settings_frame = tk.Frame(content_frame, bg="#F2F2F7")
        settings_frame.pack(fill="x", pady=(0, 30))

        # 저장 폴더
        path_frame = tk.Frame(settings_frame, bg="#F2F2F7")
        path_frame.pack(side="left", fill="x", expand=True)
        
        tk.Label(path_frame, text="저장 위치", font=self.font_bold, fg="#1C1C1E", bg="#F2F2F7").pack(anchor="w", pady=(0, 8))
        
        self.path_btn = tk.Button(path_frame, text="📥 Downloads", command=self.browse_folder, 
                                  bg="#FFFFFF", fg="#007AFF", font=(self.font_main, 10, "bold"), 
                                  padx=15, pady=8, relief="flat", cursor="hand2")
        self.path_btn.pack(anchor="w")

        # 포맷 선택
        format_frame = tk.Frame(settings_frame, bg="#F2F2F7")
        format_frame.pack(side="right")
        
        tk.Label(format_frame, text="포맷 설정", font=self.font_bold, fg="#1C1C1E", bg="#F2F2F7").pack(anchor="w", pady=(0, 8))
        
        self.format_var = tk.StringVar(value="video")
        toggle_bg = tk.Frame(format_frame, bg="#E5E5EA", padx=3, pady=3)
        toggle_bg.pack()

        # 라디오 버튼 커스텀 (iOS 토글 느낌)
        self.rb_v = tk.Radiobutton(toggle_bg, text="Video", variable=self.format_var, value="video", 
                                   indicatoron=0, width=10, font=(self.font_main, 10, "bold"), 
                                   bg="#E5E5EA", fg="#1C1C1E", selectcolor="#FFFFFF", 
                                   borderwidth=0, activebackground="#E5E5EA")
        self.rb_v.pack(side="left")
        
        self.rb_a = tk.Radiobutton(toggle_bg, text="Audio", variable=self.format_var, value="audio", 
                                   indicatoron=0, width=10, font=(self.font_main, 10, "bold"), 
                                   bg="#E5E5EA", fg="#1C1C1E", selectcolor="#FFFFFF", 
                                   borderwidth=0, activebackground="#E5E5EA")
        self.rb_a.pack(side="left")

        # 3. 추출 버튼
        self.start_btn = tk.Button(content_frame, text="추출 시작", command=self.start_task, 
                                    bg="#007AFF", fg="white", font=(self.font_main, 14, "bold"), 
                                    relief="flat", cursor="hand2", pady=15)
        self.start_btn.pack(fill="x", pady=(0, 30))

        # 4. 상태 및 로그
        status_header = tk.Frame(content_frame, bg="#F2F2F7")
        status_header.pack(fill="x", pady=(0, 10))
        
        tk.Label(status_header, text="진행 상태", font=self.font_bold, fg="#1C1C1E", bg="#F2F2F7").pack(side="left")
        self.status_label = tk.Label(status_header, text="Ready", font=(self.font_main, 10, "bold"), fg="#007AFF", bg="#F2F2F7")
        self.status_label.pack(side="right")

        self.progress = ttk.Progressbar(content_frame, style="Premium.Horizontal.TProgressbar", orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=(0, 20))

        log_wrapper = tk.Frame(content_frame, bg="#FFFFFF", highlightthickness=1, highlightbackground="#D1D1D6")
        log_wrapper.pack(fill="both", expand=True)

        self.log_text = tk.Text(log_wrapper, height=12, bg="#FFFFFF", fg="#3A3A3C", font=("Consolas", 10), 
                                 borderwidth=0, padx=15, pady=15, relief="flat")
        self.log_text.pack(fill="both", expand=True)

    def browse_folder(self):
        directory = filedialog.askdirectory()
        if directory:
            self.save_path = directory
            self.path_btn.config(text=f"📥 {os.path.basename(directory)}")

    def add_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def start_task(self):
        urls = [u.strip() for u in self.url_text.get("1.0", tk.END).split('\n') if u.strip()]
        if not urls or "여기에" in urls[0]:
            messagebox.showwarning("Warning", "URL을 입력해 주세요.")
            return

        self.start_btn.config(state="disabled", text="처리 중...", bg="#AEAEB2")
        self.progress['value'] = 0
        self.add_log(f"작업 시작: {len(urls)}개의 파일")
        
        threading.Thread(target=self.download_engine, args=(urls,), daemon=True).start()

    def download_engine(self, urls):
        is_audio = self.format_var.get() == "audio"
        
        def hook(d):
            if d['status'] == 'downloading':
                p = d.get('_percent_str', '0%').replace('%', '').strip()
                try:
                    self.progress['value'] = float(p)
                    self.status_label.config(text=f"Downloading... {p}%")
                except: pass
            elif d['status'] == 'finished':
                self.status_label.config(text="Processing...")

        for idx, url in enumerate(urls, 1):
            self.add_log(f"[{idx}/{len(urls)}] 분석 시도: {url}")
            
            opts = {
                'outtmpl': f'{self.save_path}/%(title)s.%(ext)s',
                'progress_hooks': [hook],
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
            }

            if is_audio:
                opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
                })
            else:
                opts.update({
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    'merge_output_format': 'mp4'
                })

            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
                self.add_log(f"성공: {url}")
            except Exception as e:
                self.add_log(f"실패: {url} ({str(e)})")

        self.add_log("--- 모든 작업이 종료되었습니다 ---")
        self.status_label.config(text="Completed", fg="#34C759")
        self.start_btn.config(state="normal", text="추출 시작", bg="#007AFF")
        messagebox.showinfo("Done", "모든 추출 작업이 완료되었습니다!")

if __name__ == "__main__":
    app = MediaExtractorPro()
    app.mainloop()
