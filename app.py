import os
import base64
import io
import json
import threading
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from PIL import Image
from dotenv import load_dotenv
import stripe
import numpy as np

from face_utils import get_face_embedding, find_matching_user_by_embedding
from user_store import register_user

# === Load env variables and Stripe key ===
load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# === App Setup ===
app = Flask(__name__)
CORS(app)

LOG_FILE = "data/payment_log.json"
LOG_LOCK = threading.Lock()

# === Logging Payments ===
def log_payment(amount, currency, recipient, status, **kwargs):
    record = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "amount": amount,
        "currency": currency,
        "to": recipient,
        "status": status
    }
    record.update(kwargs)

    with LOG_LOCK:
        try:
            with open(LOG_FILE, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = []
        data.append(record)
        with open(LOG_FILE, "w") as f:
            json.dump(data, f, indent=4)

# === Serve Frontend Files ===
@app.route("/")
def serve_index():
    return send_from_directory("frontend", "index.html")

@app.route("/style.css")
def serve_css():
    return send_from_directory("frontend", "style.css")

@app.route("/script.js")
def serve_js():
    return send_from_directory("frontend", "script.js")

# === API: Register Face + Stripe ID ===
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json()
    name = data.get("name")
    stripe_id = data.get("stripe_id")
    image_data = data.get("image_data")

    if not all([name, stripe_id, image_data]):
        return jsonify({"status": "error", "error": "Missing fields"}), 400

    try:
        img_bytes = base64.b64decode(image_data.split(",")[1])
        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        np_image = np.array(image)

        embedding = get_face_embedding(np_image)
        user = register_user(name, stripe_id, embedding)

        return jsonify({"status": "success", "user_id": user["user_id"]})
    except Exception as e:
        return jsonify({"status": "error", "error": f"Registration failed: {e}"}), 400

# === API: Verify Face ===
@app.route("/api/verify", methods=["POST"])
def api_verify():
    data = request.get_json()
    image_data = data.get("image_data")

    if not image_data:
        return jsonify({"status": "error", "error": "No image data provided"}), 400

    try:
        img_bytes = base64.b64decode(image_data.split(",")[1])
        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        np_image = np.array(image)

        embedding = get_face_embedding(np_image)
        user = find_matching_user_by_embedding(embedding)

        if user:
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "error": "Face not recognized"}), 401
    except Exception as e:
        return jsonify({"status": "error", "error": f"Verification failed: {e}"}), 400

# === API: Pay After Face Verification ===
@app.route("/api/pay", methods=["POST"])
def api_pay():
    data = request.get_json()
    recipient_id = data.get("recipient_id")
    amount = data.get("amount")
    image_data = data.get("image_data")

    if not all([recipient_id, amount, image_data]):
        return jsonify({"status": "error", "error": "Missing fields"}), 400

    try:
        img_bytes = base64.b64decode(image_data.split(",")[1])
        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        np_image = np.array(image)
        embedding = get_face_embedding(np_image)

        user = find_matching_user_by_embedding(embedding)
        if not user:
            return jsonify({"status": "error", "error": "Face not recognized"}), 401

        if not recipient_id.startswith("acct_"):
            return jsonify({"status": "error", "error": "Invalid recipient ID"}), 400

        cents = int(float(amount) * 100)
        payload = {
            "sender_customer_id": user["user_id"],
            "recipient_account_id": recipient_id,
            "amount_cents": cents
        }

        res = charge_and_transfer_internal(payload)
        return jsonify(res)

    except Exception as e:
        return jsonify({"status": "error", "error": f"Payment failed: {e}"}), 400

# === Stripe Logic ===
def charge_and_transfer_internal(data):
    try:
        sender_customer_id = data.get("sender_customer_id")
        recipient_account_id = data.get("recipient_account_id")
        amount_cents = data.get("amount_cents")

        payment_intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="gbp",
            customer=sender_customer_id,
            payment_method_types=["card"],
            payment_method="pm_card_visa",
            off_session=True,
            confirm=True,
            transfer_data={"destination": recipient_account_id},
        )

        log_payment(
            amount=amount_cents / 100,
            currency="GBP",
            recipient=recipient_account_id,
            status="Completed",
            charge_id=payment_intent.id
        )

        return {
            "status": "success",
            "charge_id": payment_intent.id,
            "message": "Charge successful"
        }

    except Exception as e:
        log_payment(
            amount=data.get("amount_cents", 0) / 100,
            currency="GBP",
            recipient=data.get("recipient_account_id"),
            status="Failed",
            error=str(e)
        )
        print("[ERROR] Stripe payment failed:", e)
        return {"status": "error", "error": str(e)}

# === Run App ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
