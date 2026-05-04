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

# 대체 Cobalt API 인스턴스 (더 안정적인 공용 인스턴스 시도)
# 여러 인스턴스 중 하나를 무작위로 선택하거나 가장 안정적인 곳을 지정합니다.
API_URL = 'https://api.cobalt.tools/' # 기본 인스턴스

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
    
    # 여러 인스턴스 후보군
    instances = [
        'https://api.cobalt.tools/',
        'https://cobalt.hyonsu.com/', # 한국 인스턴스 등 대체지
    ]
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for url in urls:
            if not url: continue
            
            asyncio.run_coroutine_threadsafe(
                manager.send_personal_message({"type": "log", "message": f"추출 엔진 가동 중: {url}"}, websocket), loop
            )
            
            success = False
            for target_api in instances:
                try:
                    response = await client.post(target_api, json={
                        "url": url,
                        "downloadMode": "audio" if is_audio else "video",
                        "videoQuality": "1080",
                    }, headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    })
                    
                    result = response.json()
                    
                    if result.get('status') == 'error':
                        continue # 다음 인스턴스로 시도
                        
                    if result.get('status') in ['stream', 'redirect', 'tunnel']:
                        asyncio.run_coroutine_threadsafe(
                            manager.send_personal_message({
                                "type": "finished", 
                                "filename": "추출 완료", 
                                "direct_url": result.get('url')
                            }, websocket), loop
                        )
                        success = True
                        break
                except:
                    continue
            
            if not success:
                asyncio.run_coroutine_threadsafe(
                    manager.send_personal_message({"type": "log", "message": "현재 모든 추출 엔진이 응답하지 않습니다. 잠시 후 다시 시도해 주세요."}, websocket), loop
                )

    asyncio.run_coroutine_threadsafe(
        manager.send_personal_message({"type": "all_done", "message": "종료"}, websocket), loop
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
