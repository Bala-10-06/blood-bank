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
