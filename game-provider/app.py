import json
import os
import random
from urllib import error as urlerror
from urllib import request as urlrequest
from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    session as flask_session,
)
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

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


app = Flask(__name__)

app.secret_key = os.environ.get(
    "PROVIDER_SECRET_KEY",
    "dev-provider-secret-change-this",
)

# Important for local testing:
# casino app and provider app are both localhost but different ports.
# Browser cookies are shared by hostname, not port.
app.config["SESSION_COOKIE_NAME"] = "provider_session"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

GAME_LAUNCH_SECRET = os.environ.get(
    "GAME_LAUNCH_SECRET",
    "dev-game-launch-secret-change-this",
)

CASINO_WALLET_API_URL = os.environ.get(
    "CASINO_WALLET_API_URL",
    "http://localhost:5000/provider-api/wallet",
)

WALLET_API_SECRET = os.environ.get(
    "WALLET_API_SECRET",
    "dev-wallet-secret-change-this",
)

SESSION_MAX_AGE_SECONDS = int(
    os.environ.get("SESSION_MAX_AGE_SECONDS", "3600")
)


JACKPOT_RULES = {
    "MINI": {"label": "MINI", "start": 50},
    "MINOR": {"label": "MINOR", "start": 250},
    "MAJOR": {"label": "MAJOR", "start": 1500},
    "GRAND": {"label": "GRAND", "start": 10000},
}


def validate_session_token(token):
    serializer = URLSafeTimedSerializer(GAME_LAUNCH_SECRET)

    try:
        return serializer.loads(token, max_age=SESSION_MAX_AGE_SECONDS)
    except SignatureExpired:
        abort(401, "Game session expired.")
    except BadSignature:
        abort(401, "Invalid game session.")


def get_launch_session():
    token = flask_session.get("launch_token")

    if not token:
        data = request.get_json(silent=True) or {}
        token = data.get("session")

    if not token:
        token = request.args.get("session")

    if not token:
        abort(401, "Missing game session.")

    launch_session = validate_session_token(token)

    if launch_session.get("game_id") != "fruit-fortune":
        abort(403, "Wrong game session.")

    return launch_session


def wallet_headers():
    return {
        "Authorization": f"Bearer {WALLET_API_SECRET}",
        "Content-Type": "application/json",
    }


def wallet_post(path, payload):
    url = f"{CASINO_WALLET_API_URL}{path}"

    body = json.dumps(payload).encode("utf-8")

    req = urlrequest.Request(
        url=url,
        data=body,
        headers=wallet_headers(),
        method="POST",
    )

    try:
        with urlrequest.urlopen(req, timeout=10) as response:
            raw = response.read().decode("utf-8")

            if raw:
                data = json.loads(raw)
            else:
                data = {}

            return data, None

    except urlerror.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")

        try:
            data = json.loads(raw)
        except Exception:
            data = {
                "error": "Casino wallet API returned an error.",
                "statusCode": error.code,
                "body": raw[:500],
            }

        return None, (jsonify(data), error.code)

    except urlerror.URLError as error:
        return None, (
            jsonify({
                "error": "Could not reach casino wallet API.",
                "details": str(error.reason),
            }),
            502,
        )

    except Exception as error:
        return None, (
            jsonify({
                "error": "Provider wallet request failed.",
                "details": str(error),
            }),
            500,
        )


def wallet_get_state(launch_session):
    return wallet_post(
        "/state",
        {
            "user_id": launch_session["user_id"],
        },
    )

def save_wallet_state(wallet_state):
    user = wallet_state.get("user", {})

    flask_session["wallet_user"] = {
        "id": user.get("id"),
        "username": user.get("username"),
        "balance": float(user.get("balance", 0)),
        "freeSpins": int(user.get("freeSpins", 0)),
        "freeSpinBet": int(user.get("freeSpinBet", 10)),
    }


def get_cached_wallet_user():
    user = flask_session.get("wallet_user")

    if not user:
        return None

    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "balance": float(user.get("balance", 0)),
        "freeSpins": int(user.get("freeSpins", 0)),
        "freeSpinBet": int(user.get("freeSpinBet", 10)),
    }

def format_wild_multipliers(wild_multipliers):
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


def make_empty_reveal_bonus():
    return {
        "triggered": False,
        "award": None,
        "win": 0,
        "symbols": [],
    }


def make_bonus_buy_trigger_spin(bet):
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

    scatter_count = random.choices(
        [3, 4, 5],
        weights=[80, 17, 3],
        k=1,
    )[0]

    scatter_count = min(scatter_count, COLS)
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

        "revealBonus": make_empty_reveal_bonus(),
    }


@app.route("/")
def index():
    return redirect("/health")


@app.route("/health")
def health():
    return {
        "status": "ok",
        "service": "game-provider",
    }


@app.route("/fruit-fortune")
def fruit_fortune():
    token = request.args.get("session")

    if not token:
        abort(401, "Missing session token.")

    launch_session = validate_session_token(token)

    if launch_session.get("game_id") != "fruit-fortune":
        abort(403, "Wrong game session.")

    flask_session["launch_token"] = token

    wallet_state, error = wallet_get_state(launch_session)

    if error:
        return error

    user = wallet_state["user"]
    save_wallet_state(wallet_state)

    return render_template(
        "fruit_fortune.html",
        username=user["username"],
        user_id=user["id"],
        game_id=launch_session.get("game_id"),
        balance=round(float(user["balance"]), 2),
    )


@app.route("/api/me")
def api_me():
    launch_session = get_launch_session()

    wallet_state, error = wallet_get_state(launch_session)

    if error:
        return error

    user = wallet_state["user"]

    return jsonify({
        "username": user["username"],
        "userId": user["id"],
        "balance": round(float(user["balance"]), 2),
        "freeSpins": int(user["freeSpins"]),
        "freeSpinBet": int(user["freeSpinBet"]),
        "jackpotPools": wallet_state.get("jackpotPools", {}),
    })


@app.route("/api/config")
@app.route("/games/fruit-fortune/api/config")
@app.route("/fruit-fortune/api/config")
def api_config():
    launch_session = get_launch_session()

    wallet_state, error = wallet_get_state(launch_session)

    if error:
        return error

    user = wallet_state["user"]
    save_wallet_state(wallet_state)

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
        "jackpotPools": wallet_state.get("jackpotPools", {}),
        "maxWinMultiplier": MAX_WIN_MULTIPLIER,
        "targetRTP": TARGET_RTP,
        "user": {
            "username": user["username"],
            "userId": user["id"],
            "balance": round(float(user["balance"]), 2),
            "freeSpins": int(user["freeSpins"]),
            "freeSpinBet": int(user["freeSpinBet"]),
        },
    })


@app.route("/api/buy-bonus", methods=["POST"])
@app.route("/games/fruit-fortune/api/buy-bonus", methods=["POST"])
@app.route("/fruit-fortune/api/buy-bonus", methods=["POST"])
def api_buy_bonus():
    launch_session = get_launch_session()
    data = request.get_json(silent=True) or {}

    try:
        bet = int(data.get("bet", 10))
    except Exception:
        return jsonify({"error": "Invalid bet."}), 400

    if bet < 1:
        return jsonify({"error": "Bet must be at least 1."}), 400

    trigger_spin = make_bonus_buy_trigger_spin(bet)
    bonus_spins = int(trigger_spin["freeSpinsAwarded"])
    scatter_count = int(trigger_spin["scatterCount"])

    settlement, error = wallet_post(
        "/buy-bonus",
        {
            "user_id": launch_session["user_id"],
            "bet": bet,
            "bonus_spins": bonus_spins,
            "scatter_count": scatter_count,
            "round_data": {
                "triggerSpin": trigger_spin,
            },
        },
    )

    if error:
        return error

    return jsonify({
        "balance": round(float(settlement["balance"]), 2),
        "freeSpins": int(settlement["freeSpins"]),
        "freeSpinBet": int(settlement["freeSpinBet"]),
        "bonusSpinsAwarded": bonus_spins,
        "buyCost": int(settlement.get("buyCost", bet * 100)),
        "scatterCount": scatter_count,
        "jackpotPools": settlement.get("jackpotPools", {}),
        "triggerSpin": trigger_spin,
    })


@app.route("/api/spin", methods=["POST"])
@app.route("/games/fruit-fortune/api/spin", methods=["POST"])
@app.route("/fruit-fortune/api/spin", methods=["POST"])
def api_spin():
    launch_session = get_launch_session()
    data = request.get_json(silent=True) or {}

    try:
        requested_bet = max(1, int(data.get("bet", 10)))
    except Exception:
        requested_bet = 10

    user = get_cached_wallet_user()

    if not user:
        wallet_state, error = wallet_get_state(launch_session)

        if error:
            return error

        save_wallet_state(wallet_state)
        user = wallet_state["user"]

    if int(user["freeSpins"] or 0) > 0:
        mode = "free"
        bet = max(1, int(user["freeSpinBet"] or requested_bet))
        used_free_spin = True
    else:
        mode = "base"
        bet = requested_bet
        used_free_spin = False

        if float(user["balance"]) < bet:
            return jsonify({"error": "Not enough balance."}), 400

    reels, stops, grid, expanding_wild_reel, wild_multipliers = create_spin(mode)

    evaluation = evaluate_grid(
        grid=grid,
        bet=bet,
        mode=mode,
        wild_multipliers=wild_multipliers,
    )

    total_win = round(float(evaluation.get("totalWin", 0)), 2)

    free_spin_delta = int(evaluation.get("freeSpinAward", 0)) + int(
        evaluation.get("freeSpinRetrigger", 0)
    )

    reveal_bonus = make_empty_reveal_bonus()
    jackpot_win = 0
    total_credit = total_win + jackpot_win

    round_data = {
        "grid": grid,
        "wins": evaluation.get("wins", []),
        "wildMultipliers": format_wild_multipliers(wild_multipliers),
        "expandingWildReel": expanding_wild_reel,
        "revealBonus": reveal_bonus,
    }

    settlement, error = wallet_post(
        "/settle-spin",
        {
            "user_id": launch_session["user_id"],
            "game": "fruit_fortune_40",
            "mode": mode,
            "used_free_spin": used_free_spin,
            "bet": bet,
            "win": total_credit,
            "free_spin_delta": free_spin_delta,
            "round_data": round_data,
        },
    )

    if error:
        flask_session.pop("wallet_user", None)
        return error

    flask_session["wallet_user"] = {
        "id": launch_session["user_id"],
        "username": launch_session.get("username"),
        "balance": float(settlement["balance"]),
        "freeSpins": int(settlement["freeSpins"]),
        "freeSpinBet": int(settlement["freeSpinBet"]),
    }

    result = {
        "reels": reels,
        "stops": stops,
        "grid": grid,
        "bet": bet,
        "mode": mode,

        "expandingWildReel": expanding_wild_reel,
        "wildMultipliers": format_wild_multipliers(wild_multipliers),

        "revealBonus": reveal_bonus,
        "jackpotPools": settlement.get("jackpotPools", {}),
        "jackpotWin": jackpot_win,
        "jackpotAward": None,

        "balance": round(float(settlement["balance"]), 2),
        "freeSpins": int(settlement["freeSpins"]),
        "freeSpinBet": int(settlement["freeSpinBet"]),

        "win": total_win,
        "totalWin": total_win,

        **evaluation,
    }

    result["win"] = total_win
    result["totalWin"] = total_win
    result["jackpotWin"] = jackpot_win

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5100, debug=True, threaded=True)