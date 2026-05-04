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

# 외부 고성능 추출 API (Cobalt API)
API_URL = 'https://api.cobalt.tools/api/json'

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
                # 외부 API 호출 (서버에서 호출하므로 CORS 문제 없음)
                response = await client.post(API_URL, json={
                    "url": url,
                    "isAudioOnly": is_audio,
                    "vQuality": "1080",
                    "filenameStyle": "pretty"
                }, headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                })
                
                result = response.json()
                
                if result.get('status') == 'error':
                    msg = result.get('text', '알 수 없는 오류')
                    asyncio.run_coroutine_threadsafe(
                        manager.send_personal_message({"type": "log", "message": f"실패: {msg}"}, websocket), loop
                    )
                elif result.get('status') in ['stream', 'redirect']:
                    # 성공 시 클라이언트에 직접 다운로드 URL 전달
                    asyncio.run_coroutine_threadsafe(
                        manager.send_personal_message({
                            "type": "finished", 
                            "filename": "다운로드 준비 완료 (클릭)", 
                            "direct_url": result.get('url')
                        }, websocket), loop
                    )
                elif result.get('status') == 'picker':
                    asyncio.run_coroutine_threadsafe(
                        manager.send_personal_message({
                            "type": "finished", 
                            "filename": "다운로드 준비 완료 (클릭)", 
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
                # 비동기 테스크 실행
                asyncio.create_task(download_task(msg['urls'], msg['format'], websocket, loop))
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
