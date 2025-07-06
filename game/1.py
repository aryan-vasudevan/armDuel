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

dt = datetime.datetime
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGODB_URI)
db = client["website"]
questions = db["questions"]
users = db["users"]
game_codes = db["game_codes"]
game_codes.create_index("createdAt", expireAfterSeconds=180)

app = tk.Tk()
app.title("ArmDuel")
app.geometry("500x400")
app.resizable(False, False)

SERVER_URL = "ws://localhost:8765"
ws = None
loop = asyncio.new_event_loop()
player_name = ""
current_game_code = ""

# game state
score = 0
user_questions = []
current_question_index = 0
start_button = None
players_ready = 1
is_host = False
game_over = False

# websocket

def start_ws_loop():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(ws_handler())

async def ws_handler():
    global ws, players_ready, start_button, game_over
    try:
        async with websockets.connect(SERVER_URL) as websocket:
            ws = websocket
            await websocket.send(json.dumps({"type": "join", "room": current_game_code}))

            while True:
                msg = await websocket.recv()
                data = json.loads(msg)

                if data["type"] == "game_event":
                    if data["player"] != player_name and not game_over:
                        process_remote_event(data["player"], data["event"], data.get("score", 0))

                elif data["type"] == "player_joined":
                    players_ready += 1
                    if is_host and not game_over:
                        await websocket.send(json.dumps({"type": "start_game", "room": current_game_code}))

                elif data["type"] == "game_over":
                    if data.get("winner") != player_name:
                        def lose_screen():
                            global game_over
                            game_over = True
                            clear_screen()
                            tk.Label(app, text="You lost. 😢").pack()
                        app.after(0, lose_screen)

                elif data["type"] == "start_game":
                    if not game_over:
                        threading.Thread(target=joiner_countdown_then_start, daemon=True).start()

    except websockets.exceptions.ConnectionClosedOK:
        print("[INFO] Connection closed cleanly.")
    except Exception as e:
        print(f"[ERROR] WebSocket error: {e}")

def send_game_event(event):
    if ws:
        msg = json.dumps({
            "type": "game_event",
            "room": current_game_code,
            "player": player_name,
            "event": event,
            "score": score
        })
        asyncio.run_coroutine_threadsafe(ws.send(msg), loop)

# tkinter

def clear_screen():
    for widget in app.winfo_children():
        widget.destroy()

def update_score(name, won):
    user = users.find_one({"userName": name})
    if not user:
        users.insert_one({"userName": name, "score": 10 if won else 0})
    else:
        new_score = user["score"] + (10 if won else -5)
        users.update_one({"userName": name}, {"$set": {"score": new_score}})

def get_leaderboard():
    return list(users.find().sort("score", -1).limit(5))

def display_leaderboard():
    for u in get_leaderboard():
        print(f"{u['userName']}: {u['score']}")

def create_game(name):
    game_code = str(sha256(str(dt.now()).encode() + name.encode()).hexdigest())[0:6]
    game_codes.insert_one({
        "code": game_code,
        "createdAt": dt.now(datetime.timezone.utc),
        "createdBy": name
    })
    return game_code

def display_join_game_screen():
    player_name = name_entry.get()
    clear_screen()
    code = tk.Entry(app)
    code.pack()
    tk.Button(app, text="Join with Code", command=lambda: join_game_with_code(code.get(), player_name)).pack()

def join_game_with_code(code, name):
    global current_game_code, player_name, is_host
    is_host = False
    current_game_code = code
    player_name = name

    code_entry = game_codes.find_one({"code": code})
    if not code_entry:
        messagebox.showerror("Error", "Game code not found.")
        return

    game_codes.delete_one({"code": code})
    clear_screen()
    threading.Thread(target=start_ws_loop, daemon=True).start()
    tk.Label(text="Waiting for host to start...").pack()


def display_game_screen():
    global is_host
    is_host = True

    global player_name, current_game_code, start_button, players_ready
    player_name = name_entry.get()
    current_game_code = create_game(player_name)
    clear_screen()

    tk.Label(app, text="Your game code is:").pack()
    tk.Label(app, text=current_game_code).pack()

    players_ready = 1

    threading.Thread(target=start_ws_loop, daemon=True).start()

def joiner_countdown_then_start():
    for i in range(3, 0, -1):
        clear_screen()
        tk.Label(app, text=f"Game starting in {i}...").pack()
        app.update()
        time.sleep(1)
    start_game()

def process_remote_event(player, event, remote_score):
    global score, game_over
    if game_over:
        return

    score = -remote_score  # inverse

    app.after(0, show_current_question_only)

def show_current_question_only():
    global current_question_index

    clear_screen()

    if current_question_index >= len(user_questions):
        tk.Label(app, text="Game over! Out of questions.").pack()
        return

    curQ = user_questions[current_question_index]
    choices = user_questions[current_question_index]["shuffled_choices"]

    tk.Label(app, text=f"Your Score: {score}").pack()
    tk.Label(app, text=curQ["question"]).pack()

    for choice in choices:
        tk.Button(app, text=choice, command=lambda c=choice: check_answer(curQ, c)).pack()

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
    clear_screen()
    global current_question_index

    if current_question_index >= len(user_questions):
        tk.Label(app, text="Game over! Out of questions.").pack()
        return

    curQ = user_questions[current_question_index]
    choices = user_questions[current_question_index]["shuffled_choices"]

    tk.Label(app, text=f"Your Score: {score}").pack()

    tk.Label(app, text=curQ["question"]).pack()

    for choice in choices:
        tk.Button(app, text=choice, command=lambda c=choice: check_answer(curQ, c)).pack()

def check_answer(question, selected_choice):
    global current_question_index, score, game_over

    if game_over:
        return

    if selected_choice == question["correctAnswer"]:
        score += 1
        send_game_event("correct")
        if check_end_game():
            return
        current_question_index += 1
        show_question()
    else:
        clear_screen()
        tk.Label(app, text="Wrong! Try again in 2 seconds...").pack()
        app.update()

        def continue_after_delay():
            global current_question_index
            if game_over:
                return
            current_question_index += 1
            show_question()

        app.after(2000, continue_after_delay)

def check_end_game():
    global game_over
    if game_over:
        return True

    if score >= 3:
        game_over = True
        clear_screen()
        tk.Label(app, text="You won! 🎉").pack()
        if ws:
            asyncio.run_coroutine_threadsafe(
                ws.send(json.dumps({
                    "type": "game_over",
                    "room": current_game_code,
                    "winner": player_name
                })),
                loop
            )
        return True

    elif score <= -3:
        game_over = True
        clear_screen()
        tk.Label(app, text="You lost. 😢").pack()
        return True

    return False

# main
tk.Label(app, text="Enter your name:").pack()
name_entry = tk.Entry(app)
name_entry.pack()
tk.Button(app, text="Create Game", command=display_game_screen).pack()
tk.Button(app, text="Join Game", command=display_join_game_screen).pack()

app.mainloop()
