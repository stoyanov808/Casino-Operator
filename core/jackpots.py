import random
from core.db import now_iso


JACKPOT_SEEDS = {
    "MINI": 50.00,
    "MINOR": 250.00,
    "MAJOR": 1500.00,
    "GRAND": 10000.00,
}

JACKPOT_CONTRIBUTIONS = {
    "MINI": 0.010,
    "MINOR": 0.006,
    "MAJOR": 0.003,
    "GRAND": 0.001,
}

JACKPOT_REVEAL_CHANCE = 0.018

JACKPOT_REVEAL_WEIGHTS = {
    "MINI": 74,
    "MINOR": 21,
    "MAJOR": 4,
    "GRAND": 1,
}

JACKPOT_RULES = {
    "MINI": "Reveal 3 MINI symbols in the shared jackpot reveal bonus.",
    "MINOR": "Reveal 3 MINOR symbols in the shared jackpot reveal bonus.",
    "MAJOR": "Reveal 3 MAJOR symbols in the shared jackpot reveal bonus.",
    "GRAND": "Reveal 3 GRAND symbols in the shared jackpot reveal bonus.",
}


def get_jackpot_pools(db):
    row = db.execute("SELECT * FROM jackpots WHERE id = 1").fetchone()

    return {
        "MINI": round(row["mini"], 2),
        "MINOR": round(row["minor"], 2),
        "MAJOR": round(row["major"], 2),
        "GRAND": round(row["grand"], 2),
    }


def add_jackpot_contribution(db, bet):
    db.execute(
        """
        UPDATE jackpots
        SET mini = mini + ?,
            minor = minor + ?,
            major = major + ?,
            grand = grand + ?,
            updated_at = ?
        WHERE id = 1
        """,
        (
            bet * JACKPOT_CONTRIBUTIONS["MINI"],
            bet * JACKPOT_CONTRIBUTIONS["MINOR"],
            bet * JACKPOT_CONTRIBUTIONS["MAJOR"],
            bet * JACKPOT_CONTRIBUTIONS["GRAND"],
            now_iso(),
        ),
    )


def reset_jackpot(db, name):
    if name not in JACKPOT_SEEDS:
        raise ValueError("Invalid jackpot name.")

    column = name.lower()
    seed = JACKPOT_SEEDS[name]

    db.execute(
        f"UPDATE jackpots SET {column} = ?, updated_at = ? WHERE id = 1",
        (seed, now_iso()),
    )


def no_reveal_bonus():
    return {
        "triggered": False,
        "award": None,
        "win": 0,
        "symbols": [],
    }


def maybe_create_reveal_bonus(db, bet, current_total_win, mode, max_win_multiplier):
    if mode != "base":
        return no_reveal_bonus()

    if current_total_win >= bet * max_win_multiplier:
        return no_reveal_bonus()

    if random.random() > JACKPOT_REVEAL_CHANCE:
        return no_reveal_bonus()

    names = list(JACKPOT_REVEAL_WEIGHTS.keys())
    weights = list(JACKPOT_REVEAL_WEIGHTS.values())
    award = random.choices(names, weights=weights, k=1)[0]

    pools = get_jackpot_pools(db)
    remaining_cap = max(0, bet * max_win_multiplier - current_total_win)
    raw_win = pools[award]
    win = min(raw_win, remaining_cap)

    if win <= 0:
        return no_reveal_bonus()

    reset_jackpot(db, award)

    return {
        "triggered": True,
        "award": award,
        "win": round(win, 2),
        "symbols": [award, award, award],
    }