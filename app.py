import os
import asyncio
import threading
import json
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import yt_dlp

app = FastAPI()

# 디렉토리 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.mount("/downloads", StaticFiles(directory=DOWNLOAD_DIR), name="downloads")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# WebSocket 관리를 위한 클래스
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

manager = ConnectionManager()

class YdlLogger:
    def __init__(self, websocket, loop):
        self.websocket = websocket
        self.loop = loop

    def debug(self, msg):
        if msg.startswith('[download]'):
            self.send_log(msg)
        elif 'Extracting' in msg:
            self.send_log(msg)

    def warning(self, msg):
        self.send_log(f"Warning: {msg}")

    def error(self, msg):
        self.send_log(f"Error: {msg}")

    def send_log(self, message):
        future = asyncio.run_coroutine_threadsafe(
            manager.send_personal_message({"type": "log", "message": message}, self.websocket),
            self.loop
        )

def download_task(urls, format_type, websocket, loop):
    is_audio = format_type == "audio"
    
    def progress_hook(d):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%').replace('%', '').strip()
            asyncio.run_coroutine_threadsafe(
                manager.send_personal_message({
                    "type": "progress", 
                    "percent": p,
                    "filename": d.get('filename', '').split('/')[-1]
                }, websocket),
                loop
            )
        elif d['status'] == 'finished':
            asyncio.run_coroutine_threadsafe(
                manager.send_personal_message({
                    "type": "finished",
                    "filename": d.get('filename', '').split('/')[-1]
                }, websocket),
                loop
            )

    for url in urls:
        if not url: continue
        
        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'progress_hooks': [progress_hook],
            'logger': YdlLogger(websocket, loop),
            'nocheckcertificate': True,
        }

        if is_audio:
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            ydl_opts.update({
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'merge_output_format': 'mp4',
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            asyncio.run_coroutine_threadsafe(
                manager.send_personal_message({"type": "log", "message": f"Critical Error: {str(e)}"}, websocket),
                loop
            )

    asyncio.run_coroutine_threadsafe(
        manager.send_personal_message({"type": "all_done", "message": "모든 작업이 완료되었습니다."}, websocket),
        loop
    )

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    loop = asyncio.get_event_loop()
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg['type'] == 'start':
                urls = msg['urls']
                format_type = msg['format']
                # 별도 스레드에서 다운로드 실행
                thread = threading.Thread(target=download_task, args=(urls, format_type, websocket, loop))
                thread.start()
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
