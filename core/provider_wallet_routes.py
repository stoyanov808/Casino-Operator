import json

from flask import Blueprint, current_app, jsonify, request

from core.db import get_db, now_iso
from core.jackpots import add_jackpot_contribution, get_jackpot_pools


provider_wallet_bp = Blueprint(
    "provider_wallet",
    __name__,
    url_prefix="/provider-api/wallet",
)


def require_provider_auth():
    expected = current_app.config.get(
        "WALLET_API_SECRET",
        "dev-wallet-secret-change-this",
    )

    auth_header = request.headers.get("Authorization", "")

    return auth_header == f"Bearer {expected}"


@provider_wallet_bp.before_request
def protect_provider_wallet_api():
    if not require_provider_auth():
        return jsonify({"error": "Unauthorized provider request."}), 401


@provider_wallet_bp.route("/state", methods=["POST"])
def wallet_state():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"error": "Missing user_id."}), 400

    db = get_db()

    user = db.execute(
        """
        SELECT id, username, balance, free_spins, free_spin_bet
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()

    if not user:
        return jsonify({"error": "User not found."}), 404

    return jsonify({
        "user": {
            "id": user["id"],
            "username": user["username"],
            "balance": round(float(user["balance"] or 0), 2),
            "freeSpins": int(user["free_spins"] or 0),
            "freeSpinBet": int(user["free_spin_bet"] or 10),
        },
        "jackpotPools": get_jackpot_pools(db),
    })


@provider_wallet_bp.route("/settle-spin", methods=["POST"])
def settle_spin():
    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id")
    game = data.get("game", "fruit_fortune_40")
    used_free_spin = bool(data.get("used_free_spin", False))

    try:
        bet = max(1, int(data.get("bet", 10)))
        win = round(float(data.get("win", 0)), 2)
        free_spin_delta = int(data.get("free_spin_delta", 0))
    except Exception:
        return jsonify({"error": "Invalid settlement values."}), 400

    if not user_id:
        return jsonify({"error": "Missing user_id."}), 400

    db = get_db()
    db.execute("BEGIN IMMEDIATE")

    try:
        user = db.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        if not user:
            db.execute("ROLLBACK")
            return jsonify({"error": "User not found."}), 404

        balance = float(user["balance"] or 0)
        free_spins = int(user["free_spins"] or 0)
        free_spin_bet = int(user["free_spin_bet"] or bet)

        if used_free_spin:
            if free_spins <= 0:
                db.execute("ROLLBACK")
                return jsonify({"error": "No free spins available."}), 400

            mode = "free"
            bet = free_spin_bet
            free_spins -= 1
        else:
            mode = "base"

            if balance < bet:
                db.execute("ROLLBACK")
                return jsonify({"error": "Not enough balance."}), 400

            balance -= bet
            free_spin_bet = bet
            add_jackpot_contribution(db, bet)

        balance += win
        free_spins += free_spin_delta

        db.execute(
            """
            UPDATE users
            SET balance = ?,
                free_spins = ?,
                free_spin_bet = ?
            WHERE id = ?
            """,
            (
                balance,
                free_spins,
                free_spin_bet,
                user_id,
            ),
        )

        db.execute(
            """
            INSERT INTO game_rounds
            (user_id, game, bet, mode, win, jackpot_award, jackpot_win, data_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                game,
                bet,
                mode,
                win,
                None,
                0,
                json.dumps({
                    "mode": mode,
                    "bet": bet,
                    "win": win,
                }),
                now_iso(),
            ),
        )

        jackpot_pools = get_jackpot_pools(db)

        db.execute("COMMIT")

    except Exception:
        db.execute("ROLLBACK")
        raise

    return jsonify({
        "balance": round(balance, 2),
        "freeSpins": free_spins,
        "freeSpinBet": free_spin_bet,
        "jackpotPools": jackpot_pools,
    })


@provider_wallet_bp.route("/buy-bonus", methods=["POST"])
def buy_bonus():
    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id")

    try:
        bet = max(1, int(data.get("bet", 10)))
        bonus_spins = max(1, int(data.get("bonus_spins", 10)))
        scatter_count = int(data.get("scatter_count", 3))
    except Exception:
        return jsonify({"error": "Invalid bonus buy values."}), 400

    if not user_id:
        return jsonify({"error": "Missing user_id."}), 400

    buy_cost = bet * 100

    db = get_db()
    db.execute("BEGIN IMMEDIATE")

    try:
        user = db.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        if not user:
            db.execute("ROLLBACK")
            return jsonify({"error": "User not found."}), 404

        balance = float(user["balance"] or 0)

        if balance < buy_cost:
            db.execute("ROLLBACK")
            return jsonify({
                "error": f"Not enough balance. Bonus buy costs ${buy_cost}."
            }), 400

        new_balance = balance - buy_cost
        new_free_spins = int(user["free_spins"] or 0) + bonus_spins

        db.execute(
            """
            UPDATE users
            SET balance = ?,
                free_spins = ?,
                free_spin_bet = ?
            WHERE id = ?
            """,
            (
                new_balance,
                new_free_spins,
                bet,
                user_id,
            ),
        )

        add_jackpot_contribution(db, buy_cost)

        db.execute(
            """
            INSERT INTO game_rounds
            (user_id, game, bet, mode, win, jackpot_award, jackpot_win, data_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                "fruit_fortune_40",
                buy_cost,
                "buy_bonus",
                0,
                None,
                0,
                json.dumps({
                    "buyCost": buy_cost,
                    "bonusSpinsAwarded": bonus_spins,
                    "scatterCount": scatter_count,
                }),
                now_iso(),
            ),
        )

        jackpot_pools = get_jackpot_pools(db)

        db.execute("COMMIT")

    except Exception:
        db.execute("ROLLBACK")
        raise

    return jsonify({
        "balance": round(new_balance, 2),
        "freeSpins": new_free_spins,
        "freeSpinBet": bet,
        "buyCost": buy_cost,
        "bonusSpinsAwarded": bonus_spins,
        "scatterCount": scatter_count,
        "jackpotPools": jackpot_pools,
    })