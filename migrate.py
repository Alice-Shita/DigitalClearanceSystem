import json
from database import get_db, init_db

init_db()

conn = get_db()

# ---------------- STUDENTS ----------------
with open("students.json", "r") as f:
    students = json.load(f)

conn.execute("DELETE FROM students")

for sid, data in students.items():

    conn.execute(
        "INSERT INTO students (sid, data) VALUES (?, ?)",
        (
            sid,
            json.dumps(data)
        )
    )

print("Students migrated.")


# ---------------- USERS ----------------
with open("users.json", "r") as f:
    users = json.load(f)

conn.execute("DELETE FROM users")

for username, data in users.items():

    conn.execute(
        "INSERT INTO users (username, data) VALUES (?, ?)",
        (
            username,
            json.dumps(data)
        )
    )

print("Users migrated.")

conn.commit()
conn.close()

print("Migration complete!")