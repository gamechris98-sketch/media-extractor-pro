import os
import asyncio
import threading
import json
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp

app = FastAPI()

# 디렉토리 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 정적 파일 설정 (static 폴더 존재 여부 체크 후 마운트)
STATIC_DIR = os.path.join(BASE_DIR, "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 다운로드 파일 서버
app.mount("/downloads", StaticFiles(directory=DOWNLOAD_DIR), name="downloads")

# WebSocket 매니저
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
        if "Extracting" in msg or "[download]" in msg:
            self.send_log(msg)
    def warning(self, msg): self.send_log(f"Warning: {msg}")
    def error(self, msg): self.send_log(f"Error: {msg}")
    def send_log(self, message):
        asyncio.run_coroutine_threadsafe(
            manager.send_personal_message({"type": "log", "message": message}, self.websocket), self.loop
        )

def download_task(urls, format_type, websocket, loop):
    is_audio = format_type == "audio"
    def progress_hook(d):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%').replace('%', '').strip()
            asyncio.run_coroutine_threadsafe(
                manager.send_personal_message({"type": "progress", "percent": p, "filename": d.get('filename', '').split('/')[-1]}, websocket), loop
            )
        elif d['status'] == 'finished':
            asyncio.run_coroutine_threadsafe(
                manager.send_personal_message({"type": "finished", "filename": d.get('filename', '').split('/')[-1]}, websocket), loop
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
            ydl_opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]})
        else:
            ydl_opts.update({'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 'merge_output_format': 'mp4'})
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
        except Exception as e:
            asyncio.run_coroutine_threadsafe(manager.send_personal_message({"type": "log", "message": f"Error: {str(e)}"}, websocket), loop)

    asyncio.run_coroutine_threadsafe(manager.send_personal_message({"type": "all_done", "message": "완료"}, websocket), loop)

@app.get("/")
async def get_index():
    # Jinja2 대신 파일을 직접 전송하여 500 에러 가능성 원천 차단
    index_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>index.html Not Found</h1><p>Check if the file is in the root directory.</p>", status_code=404)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    loop = asyncio.get_event_loop()
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg['type'] == 'start':
                threading.Thread(target=download_task, args=(msg['urls'], msg['format'], websocket, loop)).start()
    except WebSocketDisconnect: manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
