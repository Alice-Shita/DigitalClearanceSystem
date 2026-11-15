
import os


BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)


# Keep the local SQLite path for maintenance scripts.
DATABASE_URL = os.path.join(
    BASE_DIR,
    "database.db"
)


# Use Render PostgreSQL when DATABASE_URL is configured.
# Otherwise, use local SQLite.
_raw_database_url = os.environ.get("DATABASE_URL", "").strip()

if _raw_database_url:
    if _raw_database_url.startswith("postgres://"):
        _raw_database_url = _raw_database_url.replace(
            "postgres://",
            "postgresql+psycopg://",
            1
        )
    elif _raw_database_url.startswith("postgresql://"):
        _raw_database_url = _raw_database_url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1
        )

    SQLALCHEMY_DATABASE_URI = _raw_database_url
else:
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + DATABASE_URL


UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "uploads"
)


PROFILE_PICS_FOLDER = os.path.join(
    UPLOAD_FOLDER,
    "profile_pics"
)


DOCUMENTS_FOLDER = os.path.join(
    UPLOAD_FOLDER,
    "documents"
)
