from functools import wraps

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from core.db import get_db, now_iso


auth_bp = Blueprint("auth", __name__)


def init_auth_hooks(app):
    @app.before_request
    def load_user():
        user_id = session.get("user_id")
        g.user = None

        if user_id:
            g.user = get_db().execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()

    @app.context_processor
    def inject_user():
        return {"current_user": g.get("user")}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for("auth.login"))

        return view(*args, **kwargs)

    return wrapped


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if len(username) < 3 or len(password) < 6:
            flash("Username must be at least 3 characters and password at least 6 characters.", "bad")
            return redirect(url_for("auth.register"))

        try:
            get_db().execute(
                """
                INSERT INTO users
                (username, password_hash, balance, free_spins, free_spin_bet, created_at)
                VALUES (?, ?, 1000, 0, 10, ?)
                """,
                (username, generate_password_hash(password), now_iso()),
            )
        except Exception:
            flash("Username already exists.", "bad")
            return redirect(url_for("auth.register"))

        flash("Account created. Log in.", "good")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = get_db().execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.", "bad")
            return redirect(url_for("auth.login"))

        session.clear()
        session["user_id"] = user["id"]

        return redirect(url_for("platform.lobby"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))