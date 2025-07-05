import socket
import os
from dotenv import load_dotenv

load_dotenv()

# Send command
def move_player(s):
    s.sendall(b"MOVE_PLAYER\n")
    print("Command sent")

    data = s.recv(1024)
    print("Received:", data.decode())

    s.close()
    print("Connection closed.")

# Connect to server on ESP32
ESP32_IP = os.getenv("ESP32_IP")
PORT = 12345

print("Connecting to ESP32 at", ESP32_IP, "on port", PORT)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ESP32_IP, PORT))
print("Connected")

move_player(s)