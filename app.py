import os
import asyncio
import threading
import json
import httpx
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 최신 Cobalt API (v10)
API_URL = 'https://api.cobalt.tools/'

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

async def download_task(urls, format_type, websocket, loop):
    is_audio = format_type == "audio"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for url in urls:
            if not url: continue
            
            asyncio.run_coroutine_threadsafe(
                manager.send_personal_message({"type": "log", "message": f"분석 중: {url}"}, websocket), loop
            )
            
            try:
                # v10 API 명세에 따른 요청 (isAudioOnly 대신 downloadMode 등 사용 가능하나 기본값 유지)
                response = await client.post(API_URL, json={
                    "url": url,
                    "downloadMode": "audio" if is_audio else "video",
                    "videoQuality": "1080",
                    "filenameStyle": "pretty"
                }, headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                })
                
                result = response.json()
                
                # v10 응답 처리
                if result.get('status') == 'error':
                    msg = result.get('text', '알 수 없는 오류')
                    asyncio.run_coroutine_threadsafe(
                        manager.send_personal_message({"type": "log", "message": f"실패: {msg}"}, websocket), loop
                    )
                elif result.get('status') in ['stream', 'redirect', 'tunnel']:
                    asyncio.run_coroutine_threadsafe(
                        manager.send_personal_message({
                            "type": "finished", 
                            "filename": "다운로드 준비 완료", 
                            "direct_url": result.get('url')
                        }, websocket), loop
                    )
                elif result.get('status') == 'picker':
                    asyncio.run_coroutine_threadsafe(
                        manager.send_personal_message({
                            "type": "finished", 
                            "filename": "다운로드 준비 완료", 
                            "direct_url": result.get('picker')[0].get('url')
                        }, websocket), loop
                    )
            except Exception as e:
                asyncio.run_coroutine_threadsafe(
                    manager.send_personal_message({"type": "log", "message": f"오류: {str(e)}"}, websocket), loop
                )

    asyncio.run_coroutine_threadsafe(
        manager.send_personal_message({"type": "all_done", "message": "완료"}, websocket), loop
    )

@app.get("/")
async def get_index():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    loop = asyncio.get_event_loop()
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg['type'] == 'start':
                asyncio.create_task(download_task(msg['urls'], msg['format'], websocket, loop))
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
