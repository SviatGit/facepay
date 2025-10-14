import numpy as np
from deepface import DeepFace
from scipy.spatial.distance import euclidean
import psycopg2
import os
import ast  # To safely parse the stringified list from DB

from dotenv import load_dotenv
load_dotenv()

# === Connect to PostgreSQL ===
def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

# === Get embedding from image ===
def get_face_embedding(image):
    img_rgb = image[:, :, ::-1]
    embedding_obj = DeepFace.represent(img_path=img_rgb, model_name="Facenet")[0]
    return embedding_obj["embedding"]

# === Compare embeddings against DB users ===
def find_matching_user_by_embedding(captured_embedding, threshold=10):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_id, name, stripe_customer_id, face_embedding FROM users")
        rows = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        print("[DB ERROR] Failed to fetch users:", e)
        return None

    for row in rows:
        user_id, name, stripe_customer_id, stored_embedding_str = row

        try:
            # Parse string back into list of floats
            stored_embedding = ast.literal_eval(stored_embedding_str)
        except Exception as e:
            print(f"[ERROR] Failed to parse embedding for user {user_id}: {e}")
            continue

        dist = euclidean(captured_embedding, stored_embedding)
        if dist < threshold:
            return {
                "user_id": user_id,
                "name": name,
                "stripe_customer_id": stripe_customer_id
            }

    return None
