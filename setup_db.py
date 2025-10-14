import os
import psycopg2
from dotenv import load_dotenv

# Load .env file where your DATABASE_URL is stored
load_dotenv()

# Get the connection string from your environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL is not set in your environment!")

try:
    # Connect to the database
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Create the users table if it doesn't exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            stripe_customer_id TEXT NOT NULL,
            face_embedding TEXT NOT NULL
        );
    """)

    conn.commit()
    cur.close()
    conn.close()

    print("✅ Table 'users' created successfully!")

except Exception as e:
    print("❌ Error creating table:", e)
