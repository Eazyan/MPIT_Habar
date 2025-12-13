from sqlalchemy import create_engine, text
import os
import sys

# Fallback URL if env is missing
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres/newsmaker")

def migrate():
    print(f"Connecting to {DATABASE_URL}...")
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN telegram_chat_id VARCHAR UNIQUE;"))
            conn.commit()
            print("Migration successful: Added telegram_chat_id")
        except Exception as e:
            print(f"Migration info (might be skipped if exists): {e}")

if __name__ == "__main__":
    migrate()
