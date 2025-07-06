import socket
import os
from dotenv import load_dotenv

load_dotenv()

ESP32_IP = os.getenv("ESP32_IP")
PORT = 12345

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ESP32_IP, PORT))

class GameOver(Exception):
    def __init__(self, winner):
        self.winner = winner

def send_push(player: str):
    cmd = b"MOVE_PLAYER_A\n" if player=="A" else b"MOVE_PLAYER_B\n"
    s.sendall(cmd)
    while True:
        resp = s.recv(1024).decode().strip()
        if resp == "OK":
            return
        if resp in ("WIN_RED", "WIN_GREEN"):
            raise GameOver(resp)

def reset_position():
    s.sendall(b"RESET\n")
    s.recv(1024)

def close_connection():
    s.close()
