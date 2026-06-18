from flask import Blueprint, current_app, g, render_template

from core.auth import login_required
from core.game_launch import create_game_launch_token


provider_bp = Blueprint("provider", __name__)


@provider_bp.route("/play/fruit-fortune")
@login_required
def play_fruit_fortune():
    token = create_game_launch_token(
        user=g.user,
        game_id="fruit-fortune",
    )

    provider_url = current_app.config["GAME_PROVIDER_URL"]
    game_url = f"{provider_url}/fruit-fortune?session={token}"

    return render_template(
        "games/provider_frame.html",
        game_title="Fruit Fortune 40",
        game_url=game_url,
    )