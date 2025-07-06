import asyncio
import websockets
import json
from dotenv_vault import load_dotenv
import os

load_dotenv()

SERVER_URL = str(os.getenv("SERVER_URL"))

rooms = {}

async def handler(websocket):
    current_room = None
    try:
        async for message in websocket:
            if not message:
                continue
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
                continue

            msg_type = data.get("type")
            if msg_type == "join":
                room = data.get("room")
                if room is None:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Missing room in join message"
                    }))
                    continue

                if room not in rooms:
                    rooms[room] = []
                rooms[room].append(websocket)
                current_room = room
                print(f"[INFO] Client joined room: {room} (total: {len(rooms[room])})")

                if len(rooms[room]) == 2:
                    print(f"[INFO] Room {room} is full. Starting game.")
                    for client in rooms[room]:
                        try:
                            await client.send(json.dumps({
                                "type": "start_game"
                            }))
                        except Exception as e:
                            print(f"[ERROR] Failed to send start_game to client: {e}")

            elif msg_type == "game_event" and current_room:
                print(f"[INFO] Broadcasting game_event in room {current_room}")
                for client in rooms.get(current_room, []):
                    if client != websocket:
                        try:
                            await client.send(json.dumps({
                                "type": "game_event",
                                "player": data.get("player"),
                                "event": data.get("event"),
                                "score": data.get("score")
                            }))
                        except Exception as e:
                            print(f"[ERROR] Failed to send message to client: {e}")
            elif msg_type == "game_over" and current_room:
                for client in rooms[current_room]:
                    if client != websocket:
                        await client.send(json.dumps({
                            "type": "game_over",
                            "winner": data.get("winner")
                        }))

            else:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Unknown message type or not in a room"
                }))

    except websockets.exceptions.ConnectionClosed as e:
        print(f"[INFO] Client disconnected - Code: {e.code} Reason: {e.reason}")
    except Exception as e:
        print(f"[ERROR] Server error: {e}")
    finally:
        if current_room and websocket in rooms.get(current_room, []):
            rooms[current_room].remove(websocket)
            print(f"[INFO] Removed client from room {current_room}")

async def main():
    async with websockets.serve(handler, SERVER_URL, 8765, ping_interval=None):
        print(f"WebSocket server running on ws://{SERVER_URL}:8765")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())