# main.py

from pymongo import MongoClient
from dotenv_vault import load_dotenv
from hashlib import sha256
import datetime
import threading
import asyncio
import websockets
import json
from random import shuffle
import time
import os
import tkinter as tk
from tkinter import messagebox

# ESP controller imports
from esp_controller import send_push, GameOver, reset_position

# --- Initialization ---

dt = datetime.datetime
load_dotenv()

# MongoDB setup
MONGODB_URI = os.getenv("MONGODB_URI")
client       = MongoClient(MONGODB_URI)
db           = client["website"]
questions    = db["questions"]
users        = db["users"]
game_codes   = db["game_codes"]
game_codes.create_index("createdAt", expireAfterSeconds=180)

# Reset ESP32 at startup (ephemeral connect)
try:
    reset_position()
except Exception as e:
    print(f"[ERROR] Could not reset ESP32: {e}")

# Tkinter app
app = tk.Tk()
app.title("ArmDuel")
app.geometry("500x400")
app.resizable(False, False)

SERVER_URL = os.getenv("SERVER_URL")
ws         = None
loop       = asyncio.new_event_loop()

# game state
player_name       = ""
player_role       = ""    # "A" for host, "B" for joiner
current_game_code = ""
score             = 0
user_questions    = []
current_question_index = 0
game_over         = False

# --- WebSocket Handler ---

def start_ws_loop():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(ws_handler())

async def ws_handler():
    global ws, game_over
    try:
        async with websockets.connect(f"ws://{SERVER_URL}:8765") as websocket:
            ws = websocket
            await websocket.send(json.dumps({
                "type": "join",
                "room": current_game_code
            }))

            async for msg in websocket:
                data = json.loads(msg)

                # remote event (score sync)
                if data["type"] == "game_event" and data["player"] != player_name and not game_over:
                    process_remote_event(data["player"], data["event"], data.get("score", 0))

                # host start trigger
                elif data["type"] == "player_joined" and player_role == "A" and not game_over:
                    await websocket.send(json.dumps({
                        "type": "start_game",
                        "room": current_game_code
                    }))

                # remote win
                elif data["type"] == "game_over" and data.get("winner") != player_name:
                    app.after(0, lambda: show_end_screen(False))

                # start countdown
                elif data["type"] == "start_game" and not game_over:
                    threading.Thread(target=joiner_countdown_then_start, daemon=True).start()

    except Exception as e:
        print(f"[ERROR] WebSocket error: {e}")

def send_game_event(event):
    if ws:
        msg = json.dumps({
            "type":  "game_event",
            "room":  current_game_code,
            "player": player_name,
            "event": event,
            "score": score
        })
        asyncio.run_coroutine_threadsafe(ws.send(msg), loop)

# --- Tkinter UI Helpers ---

def clear_screen():
    for w in app.winfo_children():
        w.destroy()

def show_end_screen(won: bool):
    global game_over
    game_over = True
    clear_screen()
    text = "You won! 🎉" if won else "You lost. 😢"
    tk.Label(app, text=text, font=("Helvetica", 16)).pack()

def create_game(name):
    code = sha256(f"{dt.now()}-{name}".encode()).hexdigest()[:6]
    game_codes.insert_one({
        "code":      code,
        "createdAt": dt.now(datetime.timezone.utc),
        "createdBy": name
    })
    return code

def display_join_game_screen():
    global player_name, player_role
    player_name = name_entry.get().strip()
    player_role = "B"
    clear_screen()

    tk.Label(app, text="Enter Code:").pack(pady=5)
    code_entry = tk.Entry(app)
    code_entry.pack(pady=5)

    def on_join():
        code = code_entry.get().strip()
        if not game_codes.find_one({"code": code}):
            messagebox.showerror("Error", "Game code not found.")
            return
        game_codes.delete_one({"code": code})
        clear_screen()
        threading.Thread(target=start_ws_loop, daemon=True).start()
        tk.Label(app, text="Waiting for host…").pack()
    tk.Button(app, text="Join", command=on_join).pack(pady=10)

def display_game_screen():
    global player_name, player_role, current_game_code
    player_name       = name_entry.get().strip()
    player_role       = "A"
    current_game_code = create_game(player_name)
    clear_screen()

    tk.Label(app, text="Your game code is:", font=("Helvetica", 12)).pack(pady=5)
    tk.Label(app, text=current_game_code, font=("Courier", 24)).pack(pady=10)

    threading.Thread(target=start_ws_loop, daemon=True).start()

def joiner_countdown_then_start():
    for i in range(3, 0, -1):
        clear_screen()
        tk.Label(app, text=f"Game starts in {i}…", font=("Helvetica", 18)).pack()
        app.update()
        time.sleep(1)
    start_game()

# --- Quiz Logic ---

def process_remote_event(player, event, remote_score):
    global score
    score = -remote_score
    app.after(0, show_question)

def start_game():
    global user_questions, current_question_index, score
    user_questions = list(questions.aggregate([{"$sample": {"size": 10}}]))
    for q in user_questions:
        q["shuffled_choices"] = q["wrongAnswers"] + [q["correctAnswer"]]
        shuffle(q["shuffled_choices"])
    current_question_index = 0
    score = 0
    show_question()

def show_question():
    global current_question_index
    clear_screen()

    if current_question_index >= len(user_questions):
        show_end_screen(score > 0)
        return

    q = user_questions[current_question_index]
    tk.Label(app, text=f"Score: {score}", font=("Helvetica", 14)).pack(pady=5)
    tk.Label(app, text=q["question"], wraplength=480).pack(pady=10)

    for choice in q["shuffled_choices"]:
        tk.Button(app, text=choice,
                  command=lambda c=choice: check_answer(q, c)
        ).pack(fill="x", padx=50, pady=2)

def check_answer(question, selected):
    global score, current_question_index

    if selected == question["correctAnswer"]:
        score += 1
        send_game_event("correct")

        # send to ESP32
        try:
            send_push(player_role)
        except GameOver as e:
            won = ((e.winner == "WIN_RED" and player_role == "A") or
                   (e.winner == "WIN_GREEN" and player_role == "B"))
            show_end_screen(won)
            return

    else:
        tk.Label(app, text="Wrong! Next in 2s...", fg="red").pack()
        app.update()
        time.sleep(2)

    current_question_index += 1
    show_question()

# --- Main ---

tk.Label(app, text="Enter your name:").pack(pady=10)
name_entry = tk.Entry(app)
name_entry.pack(pady=5)

tk.Button(app, text="Create Game", command=display_game_screen).pack(pady=5)
tk.Button(app, text="Join Game",   command=display_join_game_screen).pack(pady=5)

app.mainloop()
