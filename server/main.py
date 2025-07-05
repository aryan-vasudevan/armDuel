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

while True:
    command = input("Press [a] to push, [q] to quit: ").strip()

    if command == "a":
        s.sendall(b"MOVE_PLAYER\n")
        data = s.recv(1024)
        print("ESP32 responded:", data.decode().strip())
    elif command == "q":
        print("Exiting...")
        break
    else:
        print("Unknown command")

s.close()
print("Connection closed.")

