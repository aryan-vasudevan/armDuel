import asyncio
import websockets
import json

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

                rooms.setdefault(room, []).append(websocket)
                current_room = room
                print(f"[INFO] Client {websocket.remote_address} joined room: {room}")

            elif msg_type == "game_event" and current_room:
                print(f"[INFO] Broadcasting game_event from {data.get('player')} in room {current_room}")
                for client in rooms.get(current_room, []):
                    if client != websocket:
                        try:
                            await client.send(json.dumps({
                                "type": "game_event",
                                "player": data.get("player"),
                                "event": data.get("event")
                            }))
                        except Exception as e:
                            print(f"[ERROR] Failed to send message to client {client.remote_address}: {e}")

            else:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Unknown message type or not in a room"
                }))

    except websockets.exceptions.ConnectionClosed as e:
        print(f"[INFO] Client disconnected: {websocket.remote_address} - Code: {e.code} Reason: {e.reason}")
    except Exception as e:
        print(f"[ERROR] Server error: {e}")
    finally:
        if current_room and websocket in rooms.get(current_room, []):
            rooms[current_room].remove(websocket)
            print(f"[INFO] Removed client {websocket.remote_address} from room {current_room}")

async def main():
    # Disable automatic ping/pong to reduce idle disconnections, adjust as needed
    async with websockets.serve(handler, "0.0.0.0", 8765, ping_interval=None):
        print("WebSocket server running on ws://localhost:8765")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
