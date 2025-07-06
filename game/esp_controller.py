# esp_controller.py

import socket
import os
from dotenv import load_dotenv

load_dotenv()

ESP32_IP = os.getenv("ESP32_IP")
PORT = 12345

print("Connecting to ESP32 at", ESP32_IP, "on port", PORT)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ESP32_IP, PORT))
print("Connected to ESP32")

def send_push(player):
    if player == "A":
        s.sendall(b"MOVE_PLAYER_A\n")
    elif player == "B":
        s.sendall(b"MOVE_PLAYER_B\n")
    else:
        return
    data = s.recv(1024)
    print(f"ESP32 responded to {player}:", data.decode().strip())

def reset_position():
    s.sendall(b"RESET\n")
    data = s.recv(1024)
    print("ESP32 responded to RESET:", data.decode().strip())

def close_connection():
    s.close()
    print("ESP32 connection closed.")
