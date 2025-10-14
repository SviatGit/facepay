import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def register_user(name, stripe_customer_id, face_embedding):
    """
    Registers a new user by inserting into the PostgreSQL database.
    Face embedding is stored as a JSON string.
    """
    user_id = stripe_customer_id  # Use Stripe customer ID as user ID

    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (user_id, name, stripe_customer_id, face_embedding)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id) DO NOTHING
                """, (
                    user_id,
                    name,
                    stripe_customer_id,
                    json.dumps(face_embedding)
                ))
    finally:
        conn.close()

    return {
        "user_id": user_id,
        "name": name,
        "stripe_customer_id": stripe_customer_id,
        "face_embedding": face_embedding
    }

def load_users():
    """
    Loads all users from the PostgreSQL database.
    """
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id, name, stripe_customer_id, face_embedding FROM users
                """)
                rows = cur.fetchall()
    finally:
        conn.close()

    users = []
    for row in rows:
        users.append({
            "user_id": row["user_id"],
            "name": row["name"],
            "stripe_customer_id": row["stripe_customer_id"],
            "face_embedding": json.loads(row["face_embedding"])  # Convert string to list
        })

    return users
