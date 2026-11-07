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