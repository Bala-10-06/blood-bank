from app import format_database_error, get_database_config


MYSQL_ENV_VARS = [
    "MYSQL_HOST",
    "MYSQL_PORT",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "DB_PASSWORD",
    "MYSQL_DATABASE",
    "MYSQL_UNIX_SOCKET",
    "MYSQL_AUTH_PLUGIN",
]


def clear_mysql_env(monkeypatch):
    for name in MYSQL_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_database_config_defaults_to_tcp_localhost(monkeypatch):
    clear_mysql_env(monkeypatch)

    assert get_database_config() == {
        "host": "127.0.0.1",
        "user": "root",
        "password": "",
        "database": "blood_bank",
        "port": 3306,
    }


def test_database_config_uses_mysql_password_before_legacy_db_password(monkeypatch):
    clear_mysql_env(monkeypatch)
    monkeypatch.setenv("MYSQL_PASSWORD", "mysql-secret")
    monkeypatch.setenv("DB_PASSWORD", "legacy-secret")
    monkeypatch.setenv("MYSQL_HOST", "db.example.test")
    monkeypatch.setenv("MYSQL_PORT", "3307")
    monkeypatch.setenv("MYSQL_USER", "donor_app")
    monkeypatch.setenv("MYSQL_DATABASE", "donors")
    monkeypatch.setenv("MYSQL_UNIX_SOCKET", "/tmp/mysql.sock")
    monkeypatch.setenv("MYSQL_AUTH_PLUGIN", "mysql_native_password")

    assert get_database_config() == {
        "host": "db.example.test",
        "user": "donor_app",
        "password": "mysql-secret",
        "database": "donors",
        "port": 3307,
        "unix_socket": "/tmp/mysql.sock",
        "auth_plugin": "mysql_native_password",
    }


def test_database_error_formats_common_connection_failures():
    assert "no password was sent" in format_database_error(
        Exception("1045 (28000): Access denied for user 'root'@'localhost' (using password: NO)")
    )
    assert "Check that MySQL is running" in format_database_error(
        Exception("2003: Can't connect to MySQL server on '127.0.0.1:3306'")
    )
    assert "Run `mysql -u root -p < schema.sql` first" in format_database_error(
        Exception("1049 (42000): Unknown database 'blood_bank'")
    )


def test_normalize_dashboard_stats_defaults_missing_values():
    from app import normalize_dashboard_stats

    assert normalize_dashboard_stats({}) == {
        "total_donors": 0,
        "eligible_donors": 0,
        "average_age": 0,
        "latest_registration": None,
    }


def test_empty_dashboard_data_contains_safe_defaults():
    from app import empty_dashboard_data

    data = empty_dashboard_data("donor-1", "Test Donor")

    assert data["name"] == "Test Donor"
    assert data["user_id"] == "donor-1"
    assert data["profile"] is None
    assert data["eligibility"]["status"] == "Available"


def test_empty_admin_dashboard_data_contains_safe_defaults():
    from app import empty_admin_dashboard_data

    assert empty_admin_dashboard_data() == {
        "stats": {
            "total_donors": 0,
            "eligible_donors": 0,
            "average_age": 0,
            "latest_registration": None,
        },
        "blood_groups": [],
        "donors": [],
        "filters": {"search": "", "blood_group": "", "availability": ""},
    }


def test_admin_login_uses_environment_credentials(monkeypatch):
    from app import is_admin_login

    monkeypatch.setenv("ADMIN_ID", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret-admin")

    assert is_admin_login("admin", "secret-admin")
    assert not is_admin_login("admin", "wrong")


def test_dashboard_renders_only_logged_in_donor_profile(monkeypatch):
    from app import app

    def fake_dashboard_data(user_id):
        assert user_id == "donor-1"
        return {
            "name": "Test Donor",
            "user_id": "donor-1",
            "profile": {
                "blood_group": "O+",
                "age": 31,
                "height": 170,
                "weight": 70,
                "phone_number": "1234567890",
                "bad_habits": "No",
                "last_donated_at": None,
                "address": "Main Street",
                "created_at": None,
            },
            "eligibility": {"status": "Available", "next_available_date": None},
        }

    monkeypatch.setattr("app.get_dashboard_data", fake_dashboard_data)

    with app.test_client() as client:
        with client.session_transaction() as session:
            session["user_id"] = "donor-1"
            session["name"] = "Test Donor"

        response = client.get("/dashboard")

    assert response.status_code == 200
    assert b"Personal donor dashboard" in response.data
    assert b"Your donor profile" in response.data
    assert b"Registered donors" not in response.data
    assert b"Donors by blood group" not in response.data
    assert b"Test Donor" in response.data


def test_admin_dashboard_renders_all_donor_data(monkeypatch):
    from app import app

    monkeypatch.setattr(
        "app.get_admin_dashboard_data",
        lambda filters=None: {
            "stats": {
                "total_donors": 2,
                "eligible_donors": 1,
                "average_age": 30,
                "latest_registration": None,
            },
            "blood_groups": [{"blood_group": "A+", "donor_count": 1}],
            "donors": [
                {
                    "user_id": "donor-1",
                    "aadhar": "123456789012",
                    "name": "Test Donor",
                    "blood_group": "A+",
                    "age": 30,
                    "height": 170,
                    "weight": 70,
                    "address": "Main Street",
                    "phone_number": "1234567890",
                    "bad_habits": "No",
                    "last_donated_at": None,
                    "donation_status": "Available",
                    "next_available_date": None,
                    "created_at": None,
                }
            ],
            "filters": {"search": "", "blood_group": "", "availability": ""},
        },
    )

    with app.test_client() as client:
        with client.session_transaction() as session:
            session["user_id"] = "admin"
            session["name"] = "Administrator"
            session["role"] = "admin"

        response = client.get("/admin")

    assert response.status_code == 200
    assert b"Admin module" in response.data
    assert b"All donor records" in response.data
    assert b"Test Donor" in response.data


def test_donation_eligibility_uses_six_month_waiting_period():
    from datetime import date

    from app import add_months, get_donation_eligibility

    recent = get_donation_eligibility(date.today())
    old = get_donation_eligibility(date(2000, 1, 1))

    assert recent["status"] == "Not available"
    assert recent["next_available_date"] == add_months(date.today(), 6)
    assert old["status"] == "Available"


def test_admin_filters_build_specific_data_clause():
    from app import build_admin_filter_clause

    clause, params = build_admin_filter_clause({"search": "donor", "blood_group": "O+", "availability": "available"})

    assert "user_id LIKE" in clause
    assert "blood_group = %s" in clause
    assert "DATE_ADD" in clause
    assert params == ["%donor%", "%donor%", "%donor%", "%donor%", "O+"]
