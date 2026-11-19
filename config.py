import os


BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)


DATABASE_URL = os.path.join(
    BASE_DIR,
    "database.db"
)


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

# SQLAlchemy database connection:
# Render supplies DATABASE_URL through its environment.
# Local development safely falls back to the original SQLite file.
SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "").strip()

if SQLALCHEMY_DATABASE_URI:
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://",
            "postgresql+psycopg://",
            1
        )
    elif SQLALCHEMY_DATABASE_URI.startswith("postgresql://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1
        )
else:
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + DATABASE_URL

