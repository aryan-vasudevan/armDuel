# esp_controller.py

import socket
import os
from dotenv import load_dotenv

load_dotenv()

ESP32_IP   = os.getenv("ESP32_IP")
ESP32_PORT = int(os.getenv("ESP32_PORT", "12345"))

class GameOver(Exception):
    def __init__(self, winner):
        self.winner = winner

def send_push(player: str):
    """Open a new socket for each push, then close it."""
    cmd = b"MOVE_PLAYER_A\n" if player == "A" else b"MOVE_PLAYER_B\n"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ESP32_IP, ESP32_PORT))
        s.sendall(cmd)
        while True:
            resp = s.recv(1024).decode().strip()
            if resp == "OK":
                return
            if resp in ("WIN_RED", "WIN_GREEN"):
                raise GameOver(resp)

def reset_position():
    """Open, reset, then close."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ESP32_IP, ESP32_PORT))
        s.sendall(b"RESET\n")
        s.recv(1024)

def close_connection():
    # no-op since sockets are ephemeral now
    pass