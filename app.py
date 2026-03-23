import hmac
import os
import sqlite3

from flask import Flask, redirect, render_template, request, session, url_for


app = Flask(__name__)

# Use a stable default for local development; set HEALTH_SOC_SECRET_KEY in production.
app.config["SECRET_KEY"] = os.environ.get("HEALTH_SOC_SECRET_KEY", "dev-secret-change-me")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "health_soc.db")


def init_db() -> None:
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                vaccine TEXT NOT NULL
            )
            """
        )


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def is_logged_in() -> bool:
    return session.get("user") == "admin"


@app.route("/", methods=["GET"])
def root():
    if is_logged_in():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if hmac.compare_digest(username, "admin") and hmac.compare_digest(password, "admin"):
            session["user"] = "admin"
            return redirect(url_for("dashboard"))

        error = "Invalid username or password."

    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if not is_logged_in():
        return redirect(url_for("login"))

    error = None

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            name = (request.form.get("name") or "").strip()
            vaccine = (request.form.get("vaccine") or "").strip()

            if not name or not vaccine:
                error = "Both name and vaccine are required."
            else:
                with get_db_connection() as conn:
                    conn.execute(
                        "INSERT INTO patients (name, vaccine) VALUES (?, ?)",
                        (name, vaccine),
                    )
                return redirect(url_for("dashboard"))

        elif action == "delete":
            record_id = request.form.get("id")
            if not record_id:
                error = "Missing record id."
            else:
                with get_db_connection() as conn:
                    conn.execute("DELETE FROM patients WHERE id = ?", (record_id,))
                return redirect(url_for("dashboard"))

        else:
            error = "Unknown action."

    with get_db_connection() as conn:
        patients = conn.execute(
            "SELECT id, name, vaccine FROM patients ORDER BY id DESC"
        ).fetchall()

    return render_template("dashboard.html", patients=patients, error=error)


# Ensure the SQLite schema exists as soon as the app starts.
init_db()


if __name__ == "__main__":
    # Minimal dev server configuration.
    app.run(host="127.0.0.1", port=5000, debug=True)

