import os
from db import init_db

DB_FILE = "complaints.db"

if os.path.exists(DB_FILE):
    os.remove(DB_FILE)
    print("✅ Old complaints.db deleted!")
else:
    print("ℹ complaints.db not found, creating new one...")

init_db()
print("✅ New database created successfully!")