from sqlalchemy import create_engine, text
import os
import sys

# Fallback URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres/newsmaker")

def unlink_telegram(chat_id):
    print(f"Connecting to DB...")
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        try:
            # Find user first
            result = conn.execute(text("SELECT email FROM users WHERE telegram_chat_id = :cid"), {"cid": str(chat_id)})
            user = result.fetchone()
            
            if user:
                print(f"Found user linked to {chat_id}: {user[0]}")
                conn.execute(text("UPDATE users SET telegram_chat_id = NULL WHERE telegram_chat_id = :cid"), {"cid": str(chat_id)})
                conn.commit()
                print("✅ Successfully unlinked!")
            else:
                print("⚠️ No user found with this Telegram ID.")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python reset_telegram_link.py <TELEGRAM_CHAT_ID>")
    else:
        unlink_telegram(sys.argv[1])
