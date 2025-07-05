from pymongo import MongoClient
from dotenv_vault import load_dotenv
from hashlib import sha256
import datetime
dt = datetime.datetime

import os
import tkinter as tk
from tkinter import messagebox

load_dotenv(dotenv_path="./.env")

MONGODB_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGODB_URI)
db = client["website"]
questions = db["questions"]
users = db["users"]
game_codes = db["game_codes"]
game_codes.create_index("createdAt", expireAfterSeconds=180)

def update_score(name, won):
    user = users.find_one({"userName": name})
    if not user:
        user.insert_one({"userName": name, "score": 10 if won else 0})
    else:
        new_score = user["score"] + (10 if won else -5)
        users.update_one({"userName": name}, {"$set": {"score": new_score}})

def get_leaderboard():
    return list(users.find().sort("score", -1).limit(5))


def display_leaderboard():
    for u in get_leaderboard():
        print(f"{u['userName']}: {u['score']}")

def submit_name():
    name = entry.get()
    if name:
        update_score(name, True)  # Assume win for demo
        messagebox.showinfo("Success", f"Score updated for {name}!")

def create_game(name):
    game_code = str(sha256(str(dt.now()).encode() + name.encode()).hexdigest())[0:6]
    print(game_code)
    game_codes.insert_one({
        "code": game_code,
        "createdAt": dt.now(datetime.timezone.utc),
        "createdBy": name
    })

def join_game_with_code(code):
    code_entry = game_codes.find_one({ "code": code })
    if not code_entry:
        return
    
    game_codes.delete_one({ "code": code})
    print("deleted code: " + code)

def start_game():
    userQuestions = list(questions.aggregate([{ "$sample": { "size": 10 } }]))
    for q in userQuestions:
        print (q)


# app = tk.Tk()
# app.title("ArmDuel")

# tk.Label(app, text="Enter your name:").pack()



# entry = tk.Entry(app)
# entry.pack()

# tk.Button(app, text="Submit", command=submit_name).pack()

# app.mainloop()

create_game("sohmywohmy")

join_game_with_code(input())