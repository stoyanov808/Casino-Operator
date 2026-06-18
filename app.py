from flask import Flask
from core.game_provider_routes import provider_bp
from config import Config
from core.db import close_db, init_db
from core.auth import auth_bp, init_auth_hooks
from core.routes import platform_bp
from games.slot40FotuneLane.routes import slot_bp
from games.dice.routes import dice_bp
from config import Config
from core.provider_wallet_routes import provider_wallet_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    app.teardown_appcontext(close_db)

    init_db(app)
    init_auth_hooks(app)
    app.register_blueprint(provider_wallet_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(platform_bp)
    app.register_blueprint(slot_bp, url_prefix="/games/fruit-fortune")
    app.register_blueprint(dice_bp, url_prefix="/games/dice")
    app.register_blueprint(provider_bp)
    return app


app = create_app()

print("GAME_LAUNCH_SECRET =", app.config.get("GAME_LAUNCH_SECRET"))
print("GAME_PROVIDER_URL =", app.config.get("GAME_PROVIDER_URL"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)