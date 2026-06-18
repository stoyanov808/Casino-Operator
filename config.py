import os


BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "dev-secret-change-this",
    )

    DATABASE = os.environ.get(
        "DATABASE",
        os.path.join(BASE_DIR, "casino.db"),
    )

    GAME_PROVIDER_URL = os.environ.get(
        "GAME_PROVIDER_URL",
        "http://localhost:5100",
    )

    GAME_LAUNCH_SECRET = os.environ.get(
        "GAME_LAUNCH_SECRET",
        "dev-game-launch-secret-change-this",
    )

    WALLET_API_SECRET = os.environ.get(
        "WALLET_API_SECRET",
        "dev-wallet-secret-change-this",
    )

    SESSION_COOKIE_NAME = "casino_session"
    SESSION_COOKIE_SAMESITE = "Lax"

    ADFS_ENABLED = os.environ.get(
        "ADFS_ENABLED",
        "true",
    ).lower() == "true"

    ADFS_CLIENT_ID = os.environ.get(
        "ADFS_CLIENT_ID",
        "",
    )

    ADFS_CLIENT_SECRET = os.environ.get(
        "ADFS_CLIENT_SECRET",
        "",
    )

    ADFS_METADATA_URL = os.environ.get(
        "ADFS_METADATA_URL",
        "https://WIN-VV4SC04G6I4.dev.local/adfs/.well-known/openid-configuration",
    )

    ADFS_REDIRECT_URI = os.environ.get(
        "ADFS_REDIRECT_URI",
        "https://casino.dev.local/auth/adfs/callback",
    )

    ADFS_SCOPES = os.environ.get(
        "ADFS_SCOPES",
        "openid profile email",
    )