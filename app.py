import os
from datetime import date, datetime
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

            if is_admin_login(user_id, password):
                session["user_id"] = user_id
                session["name"] = "Administrator"
                session["role"] = "admin"
                flash("Admin login successful.", "success")
                return redirect(url_for("admin_dashboard"))

            try:
                user = find_user(user_id)
            except Exception as exc:
                flash(f"Login failed: {format_database_error(exc)}", "error")
                return render_template("login.html")

            if user and check_password_hash(user["password_hash"], password):
                session["user_id"] = user_id
                session["name"] = user["name"]
                session["role"] = "donor"
                flash("Login successful.", "success")
                return redirect(url_for("dashboard"))

            flash("Invalid user id or password.", "error")

        return render_template("login.html")

    @app.route("/dashboard", methods=["GET", "POST"])
    def dashboard():
        if "user_id" not in session:
            flash("Please login first.", "error")
            return redirect(url_for("login"))

        if request.method == "POST":
            try:
                update_last_donation_date(session["user_id"], request.form.get("last_donated_at", ""))
            except ValueError as exc:
                flash(str(exc), "error")
            except Exception as exc:
                flash(f"Last donation date could not be updated: {format_database_error(exc)}", "error")
            else:
                flash("Last donation date updated successfully.", "success")
            return redirect(url_for("dashboard"))

        try:
            dashboard_data = get_dashboard_data(session["user_id"])
        except Exception as exc:
            flash(f"Dashboard data could not be loaded: {format_database_error(exc)}", "error")
            dashboard_data = empty_dashboard_data(session.get("user_id"), session.get("name"))

        dashboard_data.setdefault("eligibility", get_donation_eligibility(None))
        return render_template("dashboard.html", current_date=date.today().isoformat(), **dashboard_data)

    @app.route("/admin")
    def admin_dashboard():
        if session.get("role") != "admin":
            flash("Admin access is required.", "error")
            return redirect(url_for("login"))

        filters = get_admin_filters(request.args)

        try:
            admin_data = get_admin_dashboard_data(filters)
        except Exception as exc:
            flash(f"Admin data could not be loaded: {format_database_error(exc)}", "error")
            admin_data = empty_admin_dashboard_data(filters)

        return render_template("admin.html", blood_group_options=BLOOD_GROUPS, **admin_data)

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


def is_admin_login(user_id: str, password: str) -> bool:
    admin_id = os.environ.get("ADMIN_ID", "admin")
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    return bool(admin_password) and user_id.strip() == admin_id and password == admin_password


def empty_dashboard_data(user_id: str, name: str | None = None) -> Dict[str, Any]:
    return {
        "name": name,
        "user_id": user_id,
        "profile": None,
        "eligibility": get_donation_eligibility(None),
    }


def get_dashboard_data(user_id: str) -> Dict[str, Any]:
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT user_id, name, blood_group, age, height, weight, address, phone_number, bad_habits, last_donated_at, created_at
            FROM donors
            WHERE user_id = %s
            """,
            (user_id.strip(),),
        )
        profile = cursor.fetchone()

        return {
            "name": profile["name"] if profile else None,
            "user_id": user_id,
            "profile": profile,
            "eligibility": get_donation_eligibility(profile.get("last_donated_at") if profile else None),
        }
    finally:
        cursor.close()
        connection.close()


def empty_admin_dashboard_data(filters: Dict[str, str] | None = None) -> Dict[str, Any]:
    return {
        "stats": {
            "total_donors": 0,
            "eligible_donors": 0,
            "average_age": 0,
            "latest_registration": None,
        },
        "blood_groups": [],
        "donors": [],
        "filters": filters or get_admin_filters({}),
    }


def get_admin_dashboard_data(filters: Dict[str, str] | None = None) -> Dict[str, Any]:
    filters = filters or get_admin_filters({})
    where_clause, params = build_admin_filter_clause(filters)
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_donors,
                SUM(CASE WHEN bad_habits = 'No' AND (last_donated_at IS NULL OR DATE_ADD(last_donated_at, INTERVAL 6 MONTH) <= CURDATE()) THEN 1 ELSE 0 END) AS eligible_donors,
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
            SELECT user_id, aadhar, name, blood_group, age, height, weight, address, phone_number, bad_habits, last_donated_at, created_at
            FROM donors
            {where_clause}
            ORDER BY created_at DESC, id DESC
            """.format(where_clause=where_clause),
            tuple(params),
        )
        donors = cursor.fetchall()

        return {
            "stats": normalize_dashboard_stats(stats),
            "blood_groups": blood_groups,
            "donors": [enrich_donor_availability(donor) for donor in donors],
            "filters": filters,
        }
    finally:
        cursor.close()
        connection.close()


def parse_iso_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Enter the last donation date in YYYY-MM-DD format.") from exc


def add_months(original: date, months: int) -> date:
    month = original.month - 1 + months
    year = original.year + month // 12
    month = month % 12 + 1
    month_lengths = [
        31,
        29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ]
    return original.replace(year=year, month=month, day=min(original.day, month_lengths[month - 1]))


def get_donation_eligibility(last_donated_at: Any) -> Dict[str, Any]:
    if not last_donated_at:
        return {"available": True, "next_available_date": None, "status": "Available"}

    if isinstance(last_donated_at, datetime):
        last_donated_at = last_donated_at.date()
    elif isinstance(last_donated_at, str):
        last_donated_at = parse_iso_date(last_donated_at)

    next_available_date = add_months(last_donated_at, 6)
    available = next_available_date <= date.today()
    return {
        "available": available,
        "next_available_date": next_available_date,
        "status": "Available" if available else "Not available",
    }


def update_last_donation_date(user_id: str, last_donated_at: str) -> None:
    last_donated_at = last_donated_at.strip()
    if not last_donated_at:
        parsed_date = None
    else:
        parsed_date = parse_iso_date(last_donated_at)
        if parsed_date > date.today():
            raise ValueError("Last donation date cannot be in the future.")

    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "UPDATE donors SET last_donated_at = %s WHERE user_id = %s",
            (parsed_date, user_id.strip()),
        )
        connection.commit()
    finally:
        cursor.close()
        connection.close()


def get_admin_filters(args: Any) -> Dict[str, str]:
    return {
        "search": args.get("search", "").strip(),
        "blood_group": args.get("blood_group", "").strip(),
        "availability": args.get("availability", "").strip(),
    }


def build_admin_filter_clause(filters: Dict[str, str]) -> tuple[str, list[Any]]:
    clauses = []
    params: list[Any] = []

    if filters.get("search"):
        clauses.append("(user_id LIKE %s OR name LIKE %s OR phone_number LIKE %s OR aadhar LIKE %s)")
        search = f"%{filters['search']}%"
        params.extend([search, search, search, search])

    if filters.get("blood_group") in BLOOD_GROUPS:
        clauses.append("blood_group = %s")
        params.append(filters["blood_group"])

    if filters.get("availability") == "available":
        clauses.append(
            "bad_habits = 'No' AND "
            "(last_donated_at IS NULL OR DATE_ADD(last_donated_at, INTERVAL 6 MONTH) <= CURDATE())"
        )
    elif filters.get("availability") == "not_available":
        clauses.append(
            "(bad_habits = 'Yes' OR "
            "(last_donated_at IS NOT NULL AND DATE_ADD(last_donated_at, INTERVAL 6 MONTH) > CURDATE()))"
        )

    if not clauses:
        return "", params
    return "WHERE " + " AND ".join(clauses), params


def enrich_donor_availability(donor: Dict[str, Any]) -> Dict[str, Any]:
    eligibility = get_donation_eligibility(donor.get("last_donated_at"))
    donor["donation_status"] = "Not available" if donor.get("bad_habits") == "Yes" else eligibility["status"]
    donor["next_available_date"] = None if donor.get("bad_habits") == "Yes" else eligibility["next_available_date"]
    return donor


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
