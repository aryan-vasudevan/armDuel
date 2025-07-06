from pymongo import MongoClient
from dotenv_vault import load_dotenv
from hashlib import sha256
import datetime
import threading
import asyncio
import websockets
import json
from random import shuffle

import os
import tkinter as tk
from tkinter import messagebox

dt = datetime.datetime
load_dotenv(dotenv_path="../.env")

MONGODB_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGODB_URI)
db = client["website"]
questions = db["questions"]
users = db["users"]
game_codes = db["game_codes"]
game_codes.create_index("createdAt", expireAfterSeconds=180)

app = tk.Tk()
app.title("ArmDuel")

SERVER_URL = "ws://localhost:8765"
ws = None
loop = asyncio.new_event_loop()
player_name = ""
current_game_code = ""

# websocket
def start_ws_loop():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(ws_handler())

async def ws_handler():
    global ws
    async with websockets.connect(SERVER_URL) as websocket:
        ws = websocket
        await websocket.send(json.dumps({"type": "join", "room": current_game_code}))
        while True:
            msg = await websocket.recv()
            data = json.loads(msg)
            if data["type"] == "game_event":
                show_remote_event(data["player"], data["event"])

def send_game_event(event):
    if ws:
        msg = json.dumps({
            "type": "game_event",
            "room": current_game_code,
            "player": player_name,
            "event": event
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
    global current_game_code, player_name
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
    # tk.Button(app, text="Start Game", command=start_game).pack()

def display_game_screen():
    global player_name, current_game_code
    player_name = name_entry.get()
    current_game_code = create_game(player_name)
    clear_screen()

    tk.Label(app, text="Your game code is:").pack()
    tk.Label(app, text=current_game_code).pack()

    threading.Thread(target=start_ws_loop, daemon=True).start()
    tk.Button(app, text="Start Game", command=start_game).pack()

def show_remote_event(player, event):
    messagebox.showinfo("Update", f"{player} got it {event}!")

def start_game():
    global user_questions, current_question_index
    user_questions = list(questions.aggregate([{"$sample": {"size": 10}}]))
    current_question_index = 0
    show_question()

def show_question():
    clear_screen()
    global current_question_index

    if current_question_index >= len(user_questions):
        tk.Label(app, text="Game over!").pack()
        return

    curQ = user_questions[current_question_index]
    choices = curQ["wrongAnswers"] + [curQ["correctAnswer"]]
    shuffle(choices)

    tk.Label(app, text=curQ["question"]).pack()

    for choice in choices:
        tk.Button(app, text=choice, command=lambda c=choice: check_answer(curQ, c)).pack()

def check_answer(question, selected_choice):
    global current_question_index

    if selected_choice == question["correctAnswer"]:
        messagebox.showinfo("Correct!", "You got it right!")
        send_game_event("correct")
    else:
        messagebox.showinfo("Wrong", "That's not correct.")

    current_question_index += 1
    show_question()


    # tk.Label(app, text="Game in progress...").pack()
    # tk.Button(app, text="Simulate Correct Answer", command=lambda: send_game_event("correct")).pack()

def check_answer(curQ, num):
    pass

# main
tk.Label(app, text="Enter your name:").pack()
name_entry = tk.Entry(app)
name_entry.pack()
tk.Button(app, text="Create Game", command=display_game_screen).pack()
tk.Button(app, text="Join Game", command=display_join_game_screen).pack()

app.mainloop()