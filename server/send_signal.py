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
    command = input("Press [a] to push A, [b] to push B, [r] to reset, [q] to quit: ").strip()

    if command == "a":
        s.sendall(b"MOVE_PLAYER_A\n")
        data = s.recv(1024)
        print("ESP32 responded:", data.decode().strip())
    elif command == "b":
        s.sendall(b"MOVE_PLAYER_B\n")
        data = s.recv(1024)
        print("ESP32 responded:", data.decode().strip())
    elif command == "q":
        print("Exiting...")
        break
    elif command == "r":
        s.sendall(b"RESET\n")
        data = s.recv(1024)
        print("ESP32 responded:", data.decode().strip())
    else:
        print("Unknown command")

s.close()
print("Connection closed.")

