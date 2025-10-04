import json
import os
import threading

USER_FILE = "data/users.json"
LOCK = threading.Lock()

def load_users():
    if not os.path.exists(USER_FILE):
        return []
    with LOCK:
        with open(USER_FILE, "r") as f:
            return json.load(f)

def save_users(users):
    with LOCK:
        with open(USER_FILE, "w") as f:
            json.dump(users, f, indent=4)

def register_user(name, stripe_customer_id, face_embedding):
    users = load_users()
    user_id = stripe_customer_id  # Use Stripe customer ID as user_id
    new_user = {
        "user_id": user_id,
        "name": name,
        "stripe_customer_id": stripe_customer_id,
        "face_embedding": face_embedding
    }
    users.append(new_user)
    save_users(users)
    return new_user

#https://connect.stripe.com/d/setup/s/_T9WQFwo7OouMo3TWDCFZPau2Db/YWNjdF8xU0RETnVMbXBXakJBWjAz/07671af6ba4010217
#https://dashboard.stripe.com/b/acct_1SDDNuLmpWjBAZ03/account/status