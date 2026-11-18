import sys
from sqlalchemy import create_engine, inspect, text
from config import SQLALCHEMY_DATABASE_URI

url = SQLALCHEMY_DATABASE_URI
is_postgres = url.startswith(("postgresql://", "postgresql+"))
is_sqlite = url.startswith("sqlite:///")

if not (is_postgres or is_sqlite):
    raise SystemExit("STOP: Unsupported database type.")

if is_postgres and "--confirm-postgres" not in sys.argv:
    raise SystemExit(
        "STOP: PostgreSQL migration requires --confirm-postgres."
    )

print("Database type:", "PostgreSQL" if is_postgres else "SQLite")

engine = create_engine(url)

with engine.begin() as conn:
    inspector = inspect(conn)
    tables = inspector.get_table_names()

    if "users" not in tables:
        raise SystemExit("STOP: users table was not found.")

    user_columns = {
        column["name"]
        for column in inspector.get_columns("users")
    }

    if "email" not in user_columns:
        conn.execute(
            text("ALTER TABLE users ADD COLUMN email VARCHAR(120)")
        )
        print("Added users.email")
    else:
        print("users.email already exists")

    if is_postgres:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS password_reset_attempts (
                id BIGSERIAL PRIMARY KEY,
                ip_hash VARCHAR(64) NOT NULL,
                attempted_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
            )
        """))
    else:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS password_reset_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_hash VARCHAR(64) NOT NULL,
                attempted_at DATETIME NOT NULL
            )
        """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS
        ix_password_reset_attempts_ip_hash
        ON password_reset_attempts(ip_hash)
    """))

    if is_postgres:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id BIGSERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL
                    REFERENCES users(id) ON DELETE CASCADE,
                token_hash VARCHAR(64) NOT NULL UNIQUE,
                expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                used_at TIMESTAMP WITHOUT TIME ZONE NULL,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
            )
        """))
    else:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL
                    REFERENCES users(id) ON DELETE CASCADE,
                token_hash VARCHAR(64) NOT NULL UNIQUE,
                expires_at DATETIME NOT NULL,
                used_at DATETIME NULL,
                created_at DATETIME NOT NULL
            )
        """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS
        ix_password_reset_tokens_user_id
        ON password_reset_tokens(user_id)
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS
        ix_password_reset_tokens_token_hash
        ON password_reset_tokens(token_hash)
    """))

    print("Password reset token table and indexes are ready.")

with engine.connect() as conn:
    inspector = inspect(conn)
    columns = {
        column["name"]
        for column in inspector.get_columns("users")
    }

    if "email" not in columns:
        raise SystemExit("VERIFICATION FAILED: users.email missing.")

    table_names = set(inspector.get_table_names())

    if "password_reset_tokens" not in table_names:
        raise SystemExit("VERIFICATION FAILED: token table missing.")

    if "password_reset_attempts" not in table_names:
        raise SystemExit("VERIFICATION FAILED: rate-limit table missing.")


print("VERIFICATION PASSED.")
print("No existing passwords or account records were changed.")
