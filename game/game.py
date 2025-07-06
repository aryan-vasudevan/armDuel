import curses
import time
from random import shuffle
from db import connectDB
from esp_controller import send_push, GameOver

def load_shared_questions():
    db = connectDB()
    questions = db["questions"]
    sampled = list(questions.aggregate([{"$sample": {"size": 10}}]))
    return [format_question(q) for q in sampled]

def format_question(q):
    choices = q["wrongAnswers"] + [q["correctAnswer"]]
    shuffle(choices)
    return {
        "text": q["question"],
        "choices": choices,
        "correct_index": choices.index(q["correctAnswer"])
    }

def draw_screen(stdscr, player_qs, index, last_msg, cooldown_until):
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    mid = width // 2

    key_labels = {
        "A": ['a', 's', 'd', 'f'],
        "B": ['j', 'k', 'l', ';']
    }
    now = time.time()

    for player in ["A", "B"]:
        q = player_qs[player][index[player]]
        col = 0 if player == "A" else mid

        stdscr.addstr(0, col + 2, f"Player {player}", curses.A_BOLD)
        stdscr.addstr(1, col + 2, q["text"][:mid - 4])

        for j, choice in enumerate(q["choices"]):
            label = key_labels[player][j]
            stdscr.addstr(3 + j, col + 4, f"{label}) {choice}")

        # Show cooldown or message
        if now < cooldown_until[player]:
            rem = int(cooldown_until[player] - now)
            msg = f"⏳ Wait {rem}s..."
        else:
            msg = last_msg[player]
        stdscr.addstr(9, col + 2, msg, curses.A_DIM)

    stdscr.refresh()

    # Draw quit instruction
    stdscr.addstr(height - 2, 2, "Press 'q' to quit at any time.")
    stdscr.refresh()


def game(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)  # non-blocking getch

    shared = load_shared_questions()
    player_qs = {"A": shared, "B": shared}
    index = {"A": 0, "B": 0}
    last_msg = {"A": "", "B": ""}
    cooldown_until = {"A": 0, "B": 0}

    keymap = {
        ord('a'): ("A", 0), ord('s'): ("A", 1),
        ord('d'): ("A", 2), ord('f'): ("A", 3),
        ord('j'): ("B", 0), ord('k'): ("B", 1),
        ord('l'): ("B", 2), ord(';'): ("B", 3),
        ord('q'): ("QUIT", None)
    }

    while True:
        draw_screen(stdscr, player_qs, index, last_msg, cooldown_until)

        key = stdscr.getch()
        if key == -1:
            time.sleep(0.05)
            continue

        mapping = keymap.get(key)
        if not mapping:
            continue

        player, sel = mapping
        if player == "QUIT":
            return

        now = time.time()
        if now < cooldown_until[player]:
            continue

        q = player_qs[player][index[player]]
        if sel == q["correct_index"]:
            last_msg[player] = "✅ Correct!"
            draw_screen(stdscr, player_qs, index, last_msg, cooldown_until)
            try:
                send_push(player)
            except GameOver as e:
                # Determine winner message
                if e.winner == "WIN_RED":
                    win_msg = "🔴 Red side WINS!"
                else:
                    win_msg = "🟢 Green side WINS!"
                stdscr.clear()
                stdscr.addstr(curses.LINES//2, (curses.COLS - len(win_msg))//2, win_msg, curses.A_BLINK | curses.A_BOLD)
                stdscr.refresh()
                time.sleep(5)
                return
            index[player] = (index[player] + 1) % len(player_qs[player])
            time.sleep(0.5)
            last_msg[player] = ""
        else:
            cooldown_until[player] = now + 3

if __name__ == "__main__":
    curses.wrapper(game)
