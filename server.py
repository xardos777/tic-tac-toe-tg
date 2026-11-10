from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

app = FastAPI()

rooms = dict()

@app.get("/")
async def get_game():
    return FileResponse("index.html")

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()
    
    if room_id not in rooms:
        rooms[room_id] = {"players": list(), "rematch": set()}
    
    room = rooms[room_id]
    
    if len(room["players"]) >= 2:
        await websocket.send_json({"type": "error", "message": "Комната уже заполнена!"})
        await websocket.close()
        return

    room["players"].append(websocket)
    symbol = "X" if len(room["players"]) == 1 else "O"
    await websocket.send_json({"type": "init", "symbol": symbol})

    if len(room["players"]) == 2:
        for player in room["players"]:
            await player.send_json({"type": "start"})

    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "rematch":
                room["rematch"].add(websocket)
                
                if len(room["rematch"]) == 2:
                    room["rematch"].clear()
                    room["players"].reverse()
                    for idx, player in enumerate(room["players"]):
                        new_symbol = "X" if idx == 0 else "O"
                        await player.send_json({"type": "restart_game", "symbol": new_symbol})
                else:
                    for player in room["players"]:
                        if player != websocket:
                            await player.send_json({"type": "opponent_wants_rematch"})
            else:
                for player in room["players"]:
                    if player != websocket:
                        await player.send_json(data)
                        
    except WebSocketDisconnect:
        if room_id in rooms and websocket in room["players"]:
            room["players"].remove(websocket)
            room["rematch"].discard(websocket)
            for player in room["players"]:
                await player.send_json({"type": "opponent_left"})
            if not rooms[room_id]["players"]:
                del rooms[room_id]
