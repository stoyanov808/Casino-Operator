import json

from flask import Blueprint, g, jsonify, render_template, request

from core.auth import login_required
from core.db import get_db, now_iso
from core.jackpots import add_jackpot_contribution, get_jackpot_pools, maybe_create_reveal_bonus
from games.dice.engine import play_dice


dice_bp = Blueprint("dice", __name__)

DICE_MAX_WIN_MULTIPLIER = 5000


@dice_bp.route("/")
@login_required
def page():
    return render_template("games/dice.html")


@dice_bp.route("/api/play", methods=["POST"])
@login_required
def api_play():
    db = get_db()
    data = request.get_json(force=True) or {}

    try:
        bet = max(1, int(data.get("bet", 10)))
        pick = int(data.get("pick", 1))
    except ValueError:
        return jsonify({"error": "Invalid bet or pick."}), 400

    if pick < 1 or pick > 6:
        return jsonify({"error": "Pick must be between 1 and 6."}), 400

    try:
        db.execute("BEGIN IMMEDIATE")

        user = db.execute(
            "SELECT * FROM users WHERE id = ?",
            (g.user["id"],),
        ).fetchone()

        if user["balance"] < bet:
            db.execute("ROLLBACK")
            return jsonify({"error": "Not enough balance."}), 400

        db.execute(
            "UPDATE users SET balance = balance - ? WHERE id = ?",
            (bet, user["id"]),
        )

        add_jackpot_contribution(db, bet)

        outcome = play_dice(bet, pick)

        reveal_bonus = maybe_create_reveal_bonus(
            db=db,
            bet=bet,
            current_total_win=outcome["win"],
            mode="base",
            max_win_multiplier=DICE_MAX_WIN_MULTIPLIER,
        )

        total_credit = outcome["win"] + reveal_bonus["win"]

        db.execute(
            "UPDATE users SET balance = balance + ? WHERE id = ?",
            (total_credit, user["id"]),
        )

        db.execute(
            """
            INSERT INTO game_rounds
            (user_id, game, bet, mode, win, jackpot_award, jackpot_win, data_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                "dice",
                bet,
                "base",
                outcome["win"],
                reveal_bonus["award"],
                reveal_bonus["win"],
                json.dumps({"roll": outcome["roll"], "pick": pick}),
                now_iso(),
            ),
        )

        updated_user = db.execute(
            "SELECT * FROM users WHERE id = ?",
            (user["id"],),
        ).fetchone()

        response = {
            "bet": bet,
            "pick": pick,
            "roll": outcome["roll"],
            "win": outcome["win"],
            "revealBonus": reveal_bonus,
            "balance": round(updated_user["balance"], 2),
            "jackpotPools": get_jackpot_pools(db),
        }

        db.execute("COMMIT")

        return jsonify(response)

    except Exception:
        db.execute("ROLLBACK")
        raise