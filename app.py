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
            user = find_user(user_id)

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
        return render_template("dashboard.html", name=session.get("name"), user_id=session.get("user_id"))

    @app.route("/logout")
    def logout():
        session.clear()
        flash("Logged out successfully.", "success")
        return redirect(url_for("login"))

    return app


def get_db_connection():
    import mysql.connector

    password = os.environ.get("MYSQL_PASSWORD")
    if password is None:
        password = os.environ.get("DB_PASSWORD", "")

    return mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        user=os.environ.get("MYSQL_USER", "root"),
        password=password,
        database=os.environ.get("MYSQL_DATABASE", "blood_bank"),
    )


def format_database_error(exc: Exception) -> str:
    message = str(exc)
    if "1045" in message and "using password: NO" in message:
        return (
            "MySQL rejected the connection because no password was sent. "
            "Put your Workbench password in MYSQL_PASSWORD in the .env file, "
            "then restart the Flask app."
        )
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
