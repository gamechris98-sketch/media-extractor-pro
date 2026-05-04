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
    
    # 현재 전 세계에서 생존해 있는 것으로 확인된 Cobalt 인스턴스들
    instances = [
        'https://api.cobalt.tools/',
        'https://cobalt.api.unblockvideos.com/',
        'https://cobalt-api.lunar.icu/',
        'https://api.cobalt.hyonsu.com/',
        'https://cobalt.v0.api-set.net/',
        'https://cobalt.hyper.p-e.kr/',
        'https://cobalt.k6.io/',
        'https://cobalt.03.p-e.kr/'
    ]
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        for url in urls:
            if not url: continue
            
            asyncio.run_coroutine_threadsafe(
                manager.send_personal_message({"type": "log", "message": f"전 세계 엔진 검색 중... ({url})"}, websocket), loop
            )
            
            success = False
            for target_api in instances:
                try:
                    # v10 API 규격에 맞춤
                    response = await client.post(target_api, json={
                        "url": url,
                        "downloadMode": "audio" if is_audio else "video",
                        "videoQuality": "1080",
                        "filenameStyle": "pretty"
                    }, headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
                    })
                    
                    if response.status_code != 200:
                        continue
                        
                    result = response.json()
                    
                    if result.get('status') in ['stream', 'redirect', 'tunnel', 'picker']:
                        final_url = result.get('url') or result.get('picker')[0].get('url')
                        asyncio.run_coroutine_threadsafe(
                            manager.send_personal_message({
                                "type": "finished", 
                                "filename": "다운로드 준비 완료!", 
                                "direct_url": final_url
                            }, websocket), loop
                        )
                        success = True
                        break
                except Exception:
                    continue
            
            if not success:
                asyncio.run_coroutine_threadsafe(
                    manager.send_personal_message({"type": "log", "message": "⚠️ 현재 모든 외부 엔진이 유튜브 차단에 막혔습니다. PC용 Pro 버전을 실행해 주세요!"}, websocket), loop
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
