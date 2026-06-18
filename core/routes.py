from flask import Blueprint, g, jsonify, redirect, render_template, url_for

from core.auth import login_required
from core.db import get_db
from core.jackpots import get_jackpot_pools


platform_bp = Blueprint("platform", __name__)


@platform_bp.route("/")
def home():
    if g.user:
        return redirect(url_for("platform.lobby"))

    return redirect(url_for("auth.login"))


@platform_bp.route("/lobby")
@login_required
def lobby():
    jackpots = get_jackpot_pools(get_db())

    return render_template("lobby.html", jackpots=jackpots)


@platform_bp.route("/api/me")
@login_required
def api_me():
    return jsonify({
        "username": g.user["username"],
        "balance": round(g.user["balance"], 2),
        "freeSpins": g.user["free_spins"],
        "freeSpinBet": g.user["free_spin_bet"],
        "jackpotPools": get_jackpot_pools(get_db()),
    })