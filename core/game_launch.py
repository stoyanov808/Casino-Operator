from flask import current_app
from itsdangerous import URLSafeTimedSerializer


def create_game_launch_token(user, game_id):
    serializer = URLSafeTimedSerializer(
        current_app.config["GAME_LAUNCH_SECRET"]
    )

    return serializer.dumps({
        "user_id": user["id"],
        "username": user["username"],
        "game_id": game_id,
    })