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

    assert empty_dashboard_data("donor-1", "Test Donor") == {
        "name": "Test Donor",
        "user_id": "donor-1",
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


def test_dashboard_renders_mysql_summary(monkeypatch):
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
                "address": "Main Street",
            },
            "stats": {
                "total_donors": 4,
                "eligible_donors": 3,
                "average_age": 29.5,
                "latest_registration": None,
            },
            "blood_groups": [{"blood_group": "O+", "donor_count": 2}],
            "recent_donors": [],
        }

    monkeypatch.setattr("app.get_dashboard_data", fake_dashboard_data)

    with app.test_client() as client:
        with client.session_transaction() as session:
            session["user_id"] = "donor-1"
            session["name"] = "Test Donor"

        response = client.get("/dashboard")

    assert response.status_code == 200
    assert b"MySQL-powered dashboard" in response.data
    assert b"Registered donors" in response.data
    assert b"Donors by blood group" in response.data
    assert b"Test Donor" in response.data
