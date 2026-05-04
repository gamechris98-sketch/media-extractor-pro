import os
import asyncio
import threading
import json
import httpx
import random
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

async def get_working_instances():
    """전 세계 실시간 생존 Cobalt 인스턴스 목록을 가져옵니다."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 공식 인스턴스 목록 API 시도
            resp = await client.get('https://instances.cobalt.tools/api/instances', timeout=5.0)
            if resp.status_code == 200:
                instances = resp.json()
                # 정상 작동하는 v10 인스턴스만 필터링
                return [inst['url'] for inst in instances if inst.get('version', '').startswith('10')]
    except:
        pass
    # 실패 시 기본 리스트 반환
    return [
        'https://api.cobalt.tools/',
        'https://cobalt.api.unblockvideos.com/',
        'https://cobalt.hyonsu.com/',
        'https://cobalt-api.lunar.icu/',
        'https://api.cobalt.hyonsu.com/'
    ]

async def download_task(urls, format_type, websocket, loop):
    is_audio = format_type == "audio"
    
    # 실시간으로 살아있는 서버들 확보
    instances = await get_working_instances()
    random.shuffle(instances) # 차단 분산을 위해 순서 섞기
    
    async with httpx.AsyncClient(timeout=20.0) as client:
        for url in urls:
            if not url: continue
            
            asyncio.run_coroutine_threadsafe(
                manager.send_personal_message({"type": "log", "message": f"전 세계 생존 엔진 탐색 중... ({len(instances)}개 대기)"}, websocket), loop
            )
            
            success = False
            # 최대 10개의 서버를 돌아가며 시도
            for target_api in instances[:10]:
                try:
                    asyncio.run_coroutine_threadsafe(
                        manager.send_personal_message({"type": "log", "message": f"엔진 시도 중: {target_api}"}, websocket), loop
                    )
                    
                    response = await client.post(target_api, json={
                        "url": url,
                        "downloadMode": "audio" if is_audio else "video",
                        "videoQuality": "1080",
                        "filenameStyle": "pretty"
                    }, headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15"
                    })
                    
                    if response.status_code != 200:
                        continue
                        
                    result = response.json()
                    if result.get('status') in ['stream', 'redirect', 'tunnel', 'picker']:
                        final_url = result.get('url') or result.get('picker')[0].get('url')
                        asyncio.run_coroutine_threadsafe(
                            manager.send_personal_message({
                                "type": "finished", 
                                "filename": "다운로드 준비 완료 (클릭!)", 
                                "direct_url": final_url
                            }, websocket), loop
                        )
                        success = True
                        break
                except:
                    continue
            
            if not success:
                asyncio.run_coroutine_threadsafe(
                    manager.send_personal_message({"type": "log", "message": "⚠️ 모든 외부 엔진이 응답하지 않습니다. 잠시 후 시도하거나 PC 버전을 사용해 주세요."}, websocket), loop
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
