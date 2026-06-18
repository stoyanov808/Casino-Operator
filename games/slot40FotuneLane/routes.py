
import json
import random

from flask import Blueprint, g, jsonify, render_template, request

from core.auth import login_required
from core.db import get_db, now_iso
from core.jackpots import (
    JACKPOT_RULES,
    add_jackpot_contribution,
    get_jackpot_pools,
    maybe_create_reveal_bonus,
)
from games.slot40FotuneLane.config import (
    COLS,
    FREE_SPIN_AWARDS,
    MAX_WIN_MULTIPLIER,
    PAYTABLE,
    ROWS,
    SCATTER,
    SCATTER_PAYOUTS,
    STRIP_LEN,
    SYMBOL_IDS,
    SYMBOL_META,
    TARGET_RTP,
    WILD,
)
from games.slot40FotuneLane.engine import create_spin, evaluate_grid
from games.slot40FotuneLane.paylines import PAYLINES


slot_bp = Blueprint("slot", __name__)


def format_wild_multipliers(wild_multipliers):
    """
    Converts the engine wild multiplier dictionary into a frontend-friendly list.

    Expected engine format:
        {"row:col": multiplier}
    """
    formatted = []

    if not wild_multipliers:
        return formatted

    for key, value in wild_multipliers.items():
        try:
            row, col = str(key).split(":")
            formatted.append({
                "row": int(row),
                "col": int(col),
                "multiplier": value,
            })
        except Exception:
            continue

    return formatted


def make_bonus_buy_trigger_spin(bet):
    """
    Creates the visual bonus-buy trigger spin.

    This does not calculate a normal paid spin.
    It creates a fake/visual trigger spin after the user buys the bonus.

    It guarantees at least 3 scatters.
    It can also land 4 or 5 scatters.
    The scatter reels are random instead of always reels 1, 2, and 3.
    """
    strip_len = max(STRIP_LEN, 120)
    stop = min(50, strip_len - ROWS - 1)
    stops = [stop for _ in range(COLS)]

    normal_symbols = [
        symbol for symbol in SYMBOL_IDS
        if symbol != SCATTER
    ]

    reels = []
    grid = [[None for _ in range(COLS)] for _ in range(ROWS)]
    winning_cells = []

    for col in range(COLS):
        reel = [random.choice(normal_symbols) for _ in range(strip_len)]
        reels.append(reel)

        for row in range(ROWS):
            grid[row][col] = reel[stop + row]

    # Bonus-buy scatter count.
    # 3 scatters = common
    # 4 scatters = uncommon
    # 5 scatters = rare
    scatter_count = random.choices(
        [3, 4, 5],
        weights=[80, 17, 3],
        k=1,
    )[0]

    scatter_count = min(scatter_count, COLS)

    # Pick random reels for the scatters.
    # sorted() keeps the display left-to-right, but the selected reels are random.
    scatter_reels = sorted(random.sample(range(COLS), scatter_count))

    for col in scatter_reels:
        row = random.randint(0, ROWS - 1)

        grid[row][col] = SCATTER
        reels[col][stop + row] = SCATTER
        winning_cells.append([row, col])

    bonus_spins_awarded = FREE_SPIN_AWARDS.get(scatter_count, 10)

    return {
        "mode": "bonus_buy_trigger",
        "bet": bet,
        "reels": reels,
        "stops": stops,
        "grid": grid,

        "win": 0,
        "totalWin": 0,
        "scatterWin": 0,
        "lineWins": [],
        "wins": [],
        "winningCells": winning_cells,

        "scatterCount": scatter_count,
        "freeSpinAward": bonus_spins_awarded,
        "freeSpinRetrigger": 0,
        "freeSpinsAwarded": bonus_spins_awarded,

        "expandingWildReel": None,
        "wildMultipliers": [],

        "revealBonus": {
            "triggered": False,
            "award": None,
            "win": 0,
            "symbols": [],
        },
    }


@slot_bp.route("/")
@login_required
def page():
    return render_template("games/slot.html")


@slot_bp.route("/api/config")
@login_required
def api_config():
    return jsonify({
        "rows": ROWS,
        "cols": COLS,
        "stripLength": STRIP_LEN,
        "symbolIds": SYMBOL_IDS,
        "symbolMeta": SYMBOL_META,
        "wild": WILD,
        "scatter": SCATTER,
        "paylines": PAYLINES,
        "paytable": PAYTABLE,
        "scatterPayouts": SCATTER_PAYOUTS,
        "freeSpinAwards": FREE_SPIN_AWARDS,
        "jackpotRules": JACKPOT_RULES,
        "jackpotPools": get_jackpot_pools(get_db()),
        "maxWinMultiplier": MAX_WIN_MULTIPLIER,
        "targetRTP": TARGET_RTP,
        "user": {
            "balance": round(g.user["balance"], 2),
            "freeSpins": g.user["free_spins"],
            "freeSpinBet": g.user["free_spin_bet"],
        },
    })


@slot_bp.route("/api/buy-bonus", methods=["POST"])
@login_required
def api_buy_bonus():
    data = request.get_json(silent=True) or {}

    try:
        bet = int(data.get("bet", 10))
    except Exception:
        return jsonify({"error": "Invalid bet."}), 400

    if bet < 1:
        return jsonify({"error": "Bet must be at least 1."}), 400

    buy_cost = bet * 100

    # Create the trigger spin before updating the user,
    # because this decides whether the buy lands 3, 4, or 5 scatters.
    trigger_spin = make_bonus_buy_trigger_spin(bet)
    bonus_spins = int(trigger_spin["freeSpinsAwarded"])

    db = get_db()
    db.execute("BEGIN IMMEDIATE")

    try:
        user = db.execute(
            "SELECT * FROM users WHERE id = ?",
            (g.user["id"],),
        ).fetchone()

        if not user:
            db.execute("ROLLBACK")
            return jsonify({"error": "User not found."}), 404

        if float(user["balance"]) < buy_cost:
            db.execute("ROLLBACK")
            return jsonify({
                "error": f"Not enough balance. Bonus buy costs ${buy_cost}."
            }), 400

        new_balance = float(user["balance"]) - buy_cost
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
                user["id"],
            ),
        )

        # Bonus buys contribute to the shared jackpot pools.
        add_jackpot_contribution(db, buy_cost)

        db.execute(
            """
            INSERT INTO game_rounds
            (user_id, game, bet, mode, win, jackpot_award, jackpot_win, data_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                "fruit_fortune_40",
                buy_cost,
                "buy_bonus",
                0,
                None,
                0,
                json.dumps({
                    "buyCost": buy_cost,
                    "bonusSpinsAwarded": bonus_spins,
                    "scatterCount": trigger_spin["scatterCount"],
                    "triggerSpin": trigger_spin,
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
        "bonusSpinsAwarded": bonus_spins,
        "buyCost": buy_cost,
        "scatterCount": trigger_spin["scatterCount"],
        "jackpotPools": jackpot_pools,
        "triggerSpin": trigger_spin,
    })


@slot_bp.route("/api/spin", methods=["POST"])
@login_required
def api_spin():
    db = get_db()
    data = request.get_json(silent=True) or {}

    try:
        requested_bet = max(1, int(data.get("bet", 10)))
    except Exception:
        requested_bet = 10

    try:
        db.execute("BEGIN IMMEDIATE")

        user = db.execute(
            "SELECT * FROM users WHERE id = ?",
            (g.user["id"],),
        ).fetchone()

        if not user:
            db.execute("ROLLBACK")
            return jsonify({"error": "User not found."}), 404

        if int(user["free_spins"] or 0) > 0:
            mode = "free"
            bet = max(1, int(user["free_spin_bet"] or requested_bet))

            db.execute(
                """
                UPDATE users
                SET free_spins = free_spins - 1
                WHERE id = ?
                """,
                (user["id"],),
            )

        else:
            mode = "base"
            bet = requested_bet

            if float(user["balance"]) < bet:
                db.execute("ROLLBACK")
                return jsonify({"error": "Not enough balance."}), 400

            db.execute(
                """
                UPDATE users
                SET balance = balance - ?,
                    free_spin_bet = ?
                WHERE id = ?
                """,
                (bet, bet, user["id"]),
            )

            add_jackpot_contribution(db, bet)

        reels, stops, grid, expanding_wild_reel, wild_multipliers = create_spin(mode)

        evaluation = evaluate_grid(
            grid=grid,
            bet=bet,
            mode=mode,
            wild_multipliers=wild_multipliers,
        )

        total_win = round(float(evaluation.get("totalWin", 0)), 2)

        reveal_bonus = maybe_create_reveal_bonus(
            db=db,
            bet=bet,
            current_total_win=total_win,
            mode=mode,
            max_win_multiplier=MAX_WIN_MULTIPLIER,
        )

        jackpot_win = round(float(reveal_bonus.get("win", 0)), 2)
        total_credit = total_win + jackpot_win

        free_spin_delta = int(evaluation.get("freeSpinAward", 0)) + int(
            evaluation.get("freeSpinRetrigger", 0)
        )

        db.execute(
            """
            UPDATE users
            SET balance = balance + ?,
                free_spins = free_spins + ?
            WHERE id = ?
            """,
            (
                total_credit,
                free_spin_delta,
                user["id"],
            ),
        )

        db.execute(
            """
            INSERT INTO game_rounds
            (user_id, game, bet, mode, win, jackpot_award, jackpot_win, data_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                "fruit_fortune_40",
                bet,
                mode,
                total_win,
                reveal_bonus.get("award"),
                jackpot_win,
                json.dumps({
                    "grid": grid,
                    "wins": evaluation.get("wins", []),
                    "wildMultipliers": format_wild_multipliers(wild_multipliers),
                    "expandingWildReel": expanding_wild_reel,
                }),
                now_iso(),
            ),
        )

        updated_user = db.execute(
            "SELECT * FROM users WHERE id = ?",
            (user["id"],),
        ).fetchone()

        jackpot_pools = get_jackpot_pools(db)

        result = {
            "reels": reels,
            "stops": stops,
            "grid": grid,
            "bet": bet,
            "mode": mode,

            "expandingWildReel": expanding_wild_reel,
            "wildMultipliers": format_wild_multipliers(wild_multipliers),

            "revealBonus": reveal_bonus,
            "jackpotPools": jackpot_pools,
            "jackpotWin": jackpot_win,
            "jackpotAward": reveal_bonus.get("award"),

            "balance": round(updated_user["balance"], 2),
            "freeSpins": int(updated_user["free_spins"]),
            "freeSpinBet": int(updated_user["free_spin_bet"]),

            "win": total_win,
            "totalWin": total_win,

            **evaluation,
        }

        # Keep aliases stable even if evaluation contains same keys.
        result["win"] = total_win
        result["totalWin"] = total_win
        result["jackpotWin"] = jackpot_win

        db.execute("COMMIT")

        return jsonify(result)

    except Exception:
        db.execute("ROLLBACK")
        raise

