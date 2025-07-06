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
from tkinter import messagebox, scrolledtext

from openai import OpenAI 

# ESP controller imports
from esp_controller import send_push, GameOver, reset_position

# --- Initialization ---
dt = datetime.datetime
load_dotenv()
ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# MongoDB setup
MONGODB_URI = os.getenv("MONGODB_URI")
client       = MongoClient(MONGODB_URI)
db           = client["website"]
questions    = db["questions"]
users        = db["users"]
game_codes   = db["game_codes"]
game_codes.create_index("createdAt", expireAfterSeconds=180)

# Determine role and host flag
player_role   = ""  # 'A' for host, 'B' for joiner
IS_HOST       = False

# Tkinter app
app = tk.Tk()
app.title("ArmDuel")
app.geometry("500x400")
app.resizable(False, False)

SERVER_URL        = os.getenv("SERVER_URL")
ws                = None
loop              = asyncio.new_event_loop()
current_game_code = ""

# Game state
player_name            = ""
score                  = 0
user_questions         = []
wrong_questions        = []  # track questions answered incorrectly
current_question_index = 0
game_over              = False
players_ready          = 1  # host counts as ready

# --- Helper Functions ---

def clear_screen():
    for w in app.winfo_children():
        w.destroy()


def show_end_screen(won: bool):
    global game_over
    game_over = True
    clear_screen()
    msg = "You won! 🎉" if won else "You lost. 😢"
    tk.Label(app, text=msg, font=("Helvetica", 16)).pack(pady=20)
    # after displaying result, show resource window
    app.after(1000, show_resources_window)


def show_resources_window():
    # Generate summary for wrong questions
    if not wrong_questions:
        tk.messagebox.showinfo("Resources", "You answered all questions correctly! Great job.")
        return
    # prepare prompt
    prompt = "The following questions were answered incorrectly: \n"
    for i, q in enumerate(wrong_questions, 1):
        prompt += f"{i}. {q['question']} Choices: {', '.join(q['shuffled_choices'])}, Correct: {q['correctAnswer']}\n"
    prompt += (
        "Provide a concise summary of the key concepts needed to answer these questions. These questions were answered wrong in a game, so you're providing some helpful guidance. "
        "Also, suggest at least two educational resources per concept (including YouTube videos with URLs) for further learning. Start your response with introducing the concepts that they got wrong in the game."
    )
    # call OpenAI
    response = ai_client.responses.create(
        model="gpt-4.1",
        tools=[{"type": "web_search_preview"}],
        input=prompt,
    )
    summary = response.output_text
    # display in new window
    res_win = tk.Toplevel(app)
    res_win.title("Review & Resources")
    text = scrolledtext.ScrolledText(res_win, wrap=tk.WORD, width=80, height=20)
    text.pack(padx=10, pady=10)
    text.insert(tk.END, summary)
    text.configure(state='disabled')


def check_end_game():
    global game_over
    if game_over:
        return True
    if score >= 3 or score <= -3:
        game_over = True
        # broadcast game over
        if ws:
            payload = {"type": "game_over", "room": current_game_code, "winner": player_name}
            asyncio.run_coroutine_threadsafe(ws.send(json.dumps(payload)), loop)
        show_end_screen(score >= 3)
        return True
    return False

# --- WebSocket Handler ---

def start_ws_loop():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(ws_handler())

async def ws_handler():
    global ws, game_over, players_ready, score
    try:
        async with websockets.connect(f"ws://{SERVER_URL}:8765") as websocket:
            ws = websocket
            await ws.send(json.dumps({"type": "join", "room": current_game_code, "player": player_name}))
            async for msg in ws:
                data = json.loads(msg)
                t = data.get("type")
                if t == "player_joined" and player_role == "A" and not game_over:
                    players_ready += 1
                    if players_ready >= 2:
                        await websocket.send(json.dumps({"type": "start_game", "room": current_game_code}))
                elif t == "start_game" and not game_over:
                    threading.Thread(target=joiner_countdown_then_start, daemon=True).start()
                elif t == "game_event" and data.get("player") != player_name and not game_over:
                    score = -data.get("score", 0)
                    if IS_HOST:
                        try:
                            send_push('B')
                        except GameOver:
                            show_end_screen(False)
                            return
                    app.after(0, show_question)
                elif t == "game_over" and data.get("winner") != player_name:
                    show_end_screen(False)
                    return
    except Exception as e:
        print(f"[ERROR] WebSocket error: {e}")

# --- Send Game Event ---

def send_game_event(event):
    if ws:
        payload = {"type": "game_event", "room": current_game_code, "player": player_name, "event": event, "score": score}
        asyncio.run_coroutine_threadsafe(ws.send(json.dumps(payload)), loop)

# --- Screens ---

def create_game(name):
    code = sha256(f"{dt.now()}-{name}".encode()).hexdigest()[:6]
    game_codes.insert_one({"code": code, "createdAt": dt.now(datetime.timezone.utc), "createdBy": name})
    return code


def display_join_game_screen():
    global player_name, player_role, current_game_code, IS_HOST, players_ready
    player_name = name_entry.get().strip()
    player_role = "B"
    IS_HOST = False
    players_ready = 1
    clear_screen()
    tk.Label(app, text="Enter Game Code:").pack(pady=5)
    code_entry = tk.Entry(app)
    code_entry.pack(pady=5)
    def on_join():
        global current_game_code
        code = code_entry.get().strip()
        if not game_codes.find_one({"code": code}):
            messagebox.showerror("Error", "Invalid code.")
            return
        game_codes.delete_one({"code": code})
        current_game_code = code
        clear_screen()
        tk.Label(app, text="Waiting for host…").pack(pady=20)
        threading.Thread(target=start_ws_loop, daemon=True).start()
    tk.Button(app, text="Join", command=on_join).pack(pady=10)


def display_game_screen():
    global player_name, player_role, current_game_code, IS_HOST, players_ready
    player_name = name_entry.get().strip()
    player_role = "A"
    IS_HOST = True
    players_ready = 1
    current_game_code = create_game(player_name)
    clear_screen()
    tk.Label(app, text="Your Game Code:").pack(pady=5)
    tk.Label(app, text=current_game_code, font=("Courier", 24)).pack(pady=10)
    threading.Thread(target=start_ws_loop, daemon=True).start()

# --- Countdown + Quiz ---

def joiner_countdown_then_start():
    for i in range(3, 0, -1):
        clear_screen()
        tk.Label(app, text=f"Game starts in {i}…", font=("Helvetica", 18)).pack(pady=20)
        app.update()
        time.sleep(1)
    start_game()


def start_game():
    global user_questions, current_question_index, score, wrong_questions
    user_questions = list(questions.aggregate([{"$sample": {"size": 10}}]))
    wrong_questions = []
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
        check_end_game()
        return
    q = user_questions[current_question_index]
    tk.Label(app, text=f"Score: {score}", font=("Helvetica", 14)).pack(pady=5)
    tk.Label(app, text=q["question"], wraplength=480).pack(pady=10)
    for choice in q["shuffled_choices"]:
        tk.Button(app, text=choice, command=lambda c=choice: check_answer(q, c)).pack(fill="x", padx=50, pady=2)

# --- Answer Handling ---

def check_answer(question, selected):
    global score, current_question_index, wrong_questions
    if selected == question["correctAnswer"]:
        score += 1
        send_game_event("correct")
        if IS_HOST:
            try:
                send_push('A')
            except GameOver:
                show_end_screen(True)
                return
    else:
        wrong_questions.append(question)
        tk.Label(app, text="Wrong! Next question…", fg="red").pack()
        app.update()
        time.sleep(2)
    if not check_end_game():
        current_question_index += 1
        show_question()

# --- Main Launch ---

tk.Label(app, text="Enter your name:").pack(pady=10)
name_entry = tk.Entry(app)
name_entry.pack(pady=5)

tk.Button(app, text="Create Game", command=display_game_screen).pack(pady=5)
tk.Button(app, text="Join Game",   command=display_join_game_screen).pack(pady=5)

app.mainloop()
