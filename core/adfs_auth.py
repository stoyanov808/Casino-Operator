from authlib.integrations.flask_client import OAuth
from flask import Blueprint, current_app, redirect, session, url_for

from core.db import get_db, now_iso


adfs_bp = Blueprint(
    "adfs",
    __name__,
    url_prefix="/auth/adfs",
)

oauth = OAuth()


def init_adfs_oauth(app):
    oauth.init_app(app)

    if not app.config.get("ADFS_ENABLED", True):
        return

    client_id = app.config.get("ADFS_CLIENT_ID", "")
    client_secret = app.config.get("ADFS_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        app.logger.warning("ADFS is enabled but client ID/secret is missing.")
        return

    oauth.register(
        name="adfs",
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url=app.config["ADFS_METADATA_URL"],
        client_kwargs={
            "scope": app.config.get(
                "ADFS_SCOPES",
                "openid profile email",
            ),
        },
    )


def ensure_sso_columns(db):
    existing_columns = {
        row["name"]
        for row in db.execute("PRAGMA table_info(users)").fetchall()
    }

    migrations = [
        ("adfs_sub", "ALTER TABLE users ADD COLUMN adfs_sub TEXT"),
        ("email", "ALTER TABLE users ADD COLUMN email TEXT"),
        ("auth_provider", "ALTER TABLE users ADD COLUMN auth_provider TEXT"),
    ]

    for column_name, sql in migrations:
        if column_name not in existing_columns:
            db.execute(sql)

    db.commit()


def clean_username(value):
    value = str(value or "").strip().lower()

    if "\\" in value:
        value = value.split("\\", 1)[1]

    if "@" in value:
        value = value.split("@", 1)[0]

    allowed = []

    for char in value:
        if char.isalnum() or char in ["_", "-", "."]:
            allowed.append(char)

    username = "".join(allowed).strip("._-")

    if not username:
        username = "adfs_user"

    return username[:40]


def get_claim(claims, *names):
    for name in names:
        value = claims.get(name)

        if value:
            return value

    return None


def make_unique_username(db, base_username):
    base_username = clean_username(base_username)
    username = base_username

    counter = 1

    while db.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,),
    ).fetchone():
        counter += 1
        suffix = str(counter)
        username = f"{base_username[:40 - len(suffix)]}{suffix}"

    return username


def get_user_by_adfs_identity(db, adfs_sub, email):
    if adfs_sub:
        user = db.execute(
            """
            SELECT *
            FROM users
            WHERE adfs_sub = ?
            """,
            (adfs_sub,),
        ).fetchone()

        if user:
            return user

    if email:
        user = db.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

        if user:
            return user

    return None


def get_or_create_adfs_user(claims):
    db = get_db()
    ensure_sso_columns(db)

    adfs_sub = get_claim(
        claims,
        "sub",
        "sid",
        "primarysid",
        "oid",
    )

    email = get_claim(
        claims,
        "email",
        "upn",
        "unique_name",
        "preferred_username",
    )

    display_name = get_claim(
        claims,
        "name",
        "given_name",
        "unique_name",
        "preferred_username",
        "upn",
        "email",
        "sub",
    )

    if not adfs_sub:
        adfs_sub = email or display_name

    existing_user = get_user_by_adfs_identity(
        db=db,
        adfs_sub=adfs_sub,
        email=email,
    )

    if existing_user:
        db.execute(
            """
            UPDATE users
            SET adfs_sub = ?,
                email = ?,
                auth_provider = ?
            WHERE id = ?
            """,
            (
                adfs_sub,
                email,
                "adfs",
                existing_user["id"],
            ),
        )
        db.commit()

        return db.execute(
            "SELECT * FROM users WHERE id = ?",
            (existing_user["id"],),
        ).fetchone()

    username_source = email or display_name or adfs_sub
    username = make_unique_username(db, username_source)

    values_by_column = {
        "username": username,
        "password_hash": "ADFS_SSO_NO_LOCAL_PASSWORD",
        "balance": 10000.0,
        "free_spins": 0,
        "free_spin_bet": 10,
        "adfs_sub": adfs_sub,
        "email": email,
        "auth_provider": "adfs",
        "created_at": now_iso(),
    }

    table_columns = {
        row["name"]
        for row in db.execute("PRAGMA table_info(users)").fetchall()
    }

    insert_columns = [
        column
        for column in values_by_column
        if column in table_columns
    ]

    placeholders = ", ".join(["?"] * len(insert_columns))
    column_sql = ", ".join(insert_columns)

    values = [
        values_by_column[column]
        for column in insert_columns
    ]

    db.execute(
        f"""
        INSERT INTO users ({column_sql})
        VALUES ({placeholders})
        """,
        values,
    )

    db.commit()

    return db.execute(
        """
        SELECT *
        FROM users
        WHERE username = ?
        """,
        (username,),
    ).fetchone()


def get_adfs_client():
    client = oauth.create_client("adfs")

    if client is None:
        return None

    return client


@adfs_bp.route("/login")
def login():
    if not current_app.config.get("ADFS_ENABLED", True):
        return redirect(url_for("auth.login"))

    client = get_adfs_client()

    if client is None:
        return "ADFS is not configured. Missing client ID or client secret.", 500

    redirect_uri = current_app.config["ADFS_REDIRECT_URI"]

    return client.authorize_redirect(redirect_uri)


@adfs_bp.route("/callback")
def callback():
    client = get_adfs_client()

    if client is None:
        return "ADFS is not configured. Missing client ID or client secret.", 500

    token = client.authorize_access_token()

    claims = token.get("userinfo")

    if not claims:
        try:
            claims = client.parse_id_token(token)
        except Exception:
            claims = None

    if not claims:
        try:
            claims = client.userinfo(token=token)
        except Exception:
            claims = None

    if not claims:
        return "Could not read ADFS user claims.", 500

    claims = dict(claims)

    user = get_or_create_adfs_user(claims)

    session.clear()
    session["user_id"] = user["id"]
    session["auth_provider"] = "adfs"

    return redirect("/")