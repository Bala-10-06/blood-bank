import os
from typing import Any, Dict

from dotenv import load_dotenv

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from validation import BLOOD_GROUPS, validate_registration


load_dotenv()


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

    @app.route("/")
    def home():
        return redirect(url_for("login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            form = request.form.to_dict()
            errors = validate_registration(form)
            if errors:
                for error in errors:
                    flash(error, "error")
                return render_template("register.html", blood_groups=BLOOD_GROUPS, form=form)

            try:
                save_user(form)
            except Exception as exc:
                flash(f"Registration failed: {format_database_error(exc)}", "error")
                return render_template("register.html", blood_groups=BLOOD_GROUPS, form=form)

            flash("Registration successful. Please login.", "success")
            return redirect(url_for("login"))

        return render_template("register.html", blood_groups=BLOOD_GROUPS, form={})

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            user_id = request.form.get("user_id", "").strip()
            password = request.form.get("password", "")
            try:
                user = find_user(user_id)
            except Exception as exc:
                flash(f"Login failed: {format_database_error(exc)}", "error")
                return render_template("login.html")

            if user and check_password_hash(user["password_hash"], password):
                session["user_id"] = user_id
                session["name"] = user["name"]
                flash("Login successful.", "success")
                return redirect(url_for("dashboard"))

            flash("Invalid user id or password.", "error")

        return render_template("login.html")

    @app.route("/dashboard")
    def dashboard():
        if "user_id" not in session:
            flash("Please login first.", "error")
            return redirect(url_for("login"))

        try:
            dashboard_data = get_dashboard_data(session["user_id"])
        except Exception as exc:
            flash(f"Dashboard data could not be loaded: {format_database_error(exc)}", "error")
            dashboard_data = empty_dashboard_data(session.get("user_id"), session.get("name"))

        return render_template("dashboard.html", **dashboard_data)

    @app.route("/logout")
    def logout():
        session.clear()
        flash("Logged out successfully.", "success")
        return redirect(url_for("login"))

    return app


def get_db_connection():
    import mysql.connector

    return mysql.connector.connect(**get_database_config())


def get_database_config() -> Dict[str, Any]:
    """Build the MySQL connection settings from environment variables."""
    password = os.environ.get("MYSQL_PASSWORD")
    if password is None:
        password = os.environ.get("DB_PASSWORD", "")

    config: Dict[str, Any] = {
        "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
        "user": os.environ.get("MYSQL_USER", "root"),
        "password": password,
        "database": os.environ.get("MYSQL_DATABASE", "blood_bank"),
        "port": int(os.environ.get("MYSQL_PORT", "3306")),
    }

    unix_socket = os.environ.get("MYSQL_UNIX_SOCKET")
    if unix_socket:
        config["unix_socket"] = unix_socket

    auth_plugin = os.environ.get("MYSQL_AUTH_PLUGIN")
    if auth_plugin:
        config["auth_plugin"] = auth_plugin

    return config


def format_database_error(exc: Exception) -> str:
    message = str(exc)
    if "1045" in message and "using password: NO" in message:
        return (
            "MySQL rejected the connection because no password was sent. "
            "Put your Workbench password in MYSQL_PASSWORD in the .env file, "
            "then restart the Flask app."
        )
    if "2003" in message or "Can't connect to MySQL server" in message:
        return (
            "Could not connect to the MySQL server. Check that MySQL is running "
            "and that MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, and "
            "MYSQL_DATABASE in your .env file match your local setup."
        )
    if "1049" in message or "Unknown database" in message:
        return "The MySQL database was not found. Run `mysql -u root -p < schema.sql` first."
    return message


def save_user(form: Dict[str, Any]) -> None:
    query = """
        INSERT INTO donors
            (user_id, password_hash, aadhar, name, blood_group, age, height, weight, address, phone_number, bad_habits)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        form["user_id"].strip(),
        generate_password_hash(form["password"]),
        form["aadhar"].strip(),
        form["name"].strip(),
        form["blood_group"],
        int(form["age"]),
        float(form["height"]),
        float(form["weight"]),
        form["address"].strip(),
        form["phone_number"].strip(),
        form["bad_habits"],
    )

    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(query, values)
        connection.commit()
    finally:
        cursor.close()
        connection.close()


def empty_dashboard_data(user_id: str, name: str | None = None) -> Dict[str, Any]:
    return {
        "name": name,
        "user_id": user_id,
        "profile": None,
        "stats": {
            "total_donors": 0,
            "eligible_donors": 0,
            "average_age": 0,
            "latest_registration": None,
        },
        "blood_groups": [],
        "recent_donors": [],
    }


def get_dashboard_data(user_id: str) -> Dict[str, Any]:
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT user_id, name, blood_group, age, height, weight, address, phone_number, bad_habits, created_at
            FROM donors
            WHERE user_id = %s
            """,
            (user_id.strip(),),
        )
        profile = cursor.fetchone()

        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_donors,
                SUM(CASE WHEN bad_habits = 'No' THEN 1 ELSE 0 END) AS eligible_donors,
                ROUND(AVG(age), 1) AS average_age,
                MAX(created_at) AS latest_registration
            FROM donors
            """
        )
        stats = cursor.fetchone() or {}

        cursor.execute(
            """
            SELECT blood_group, COUNT(*) AS donor_count
            FROM donors
            GROUP BY blood_group
            ORDER BY FIELD(blood_group, 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')
            """
        )
        blood_groups = cursor.fetchall()

        cursor.execute(
            """
            SELECT name, blood_group, age, phone_number, created_at
            FROM donors
            ORDER BY created_at DESC, id DESC
            LIMIT 5
            """
        )
        recent_donors = cursor.fetchall()

        return {
            "name": profile["name"] if profile else None,
            "user_id": user_id,
            "profile": profile,
            "stats": normalize_dashboard_stats(stats),
            "blood_groups": blood_groups,
            "recent_donors": recent_donors,
        }
    finally:
        cursor.close()
        connection.close()


def normalize_dashboard_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "total_donors": stats.get("total_donors") or 0,
        "eligible_donors": stats.get("eligible_donors") or 0,
        "average_age": stats.get("average_age") or 0,
        "latest_registration": stats.get("latest_registration"),
    }


def find_user(user_id: str):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT user_id, password_hash, name FROM donors WHERE user_id = %s",
            (user_id.strip(),),
        )
        return cursor.fetchone()
    finally:
        cursor.close()
        connection.close()


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
