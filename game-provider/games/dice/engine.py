import random


def play_dice(bet, pick):
    roll = random.randint(1, 6)
    win = bet * 5 if roll == pick else 0

    return {
        "roll": roll,
        "pick": pick,
        "win": round(win, 2),
    }