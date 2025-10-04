import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
import threading

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5000")

LOG_FILE = "data/payment_log.json"
LOG_LOCK = threading.Lock()

def log_payment(amount, currency, recipient, status, **kwargs):
    record = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "amount": amount,
        "currency": currency,
        "to": recipient,
        "status": status
    }
    record.update(kwargs)
    try:
        LOG_LOCK.acquire()
        try:
            with open(LOG_FILE, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = []
        data.append(record)
        with open(LOG_FILE, "w") as f:
            json.dump(data, f, indent=4)
    finally:
        LOG_LOCK.release()

def register_user(stripe_customer_id, name):
    """Simulated backend call to register user (usually store on backend)."""
    # In this simplified version, just return success
    return {"status": "success", "user_id": stripe_customer_id, "name": name}

def validate_recipient(recipient_account_id):
    """
    Validate if recipient Stripe Connect account ID is valid format.
    Real validation should query Stripe API - here just check non-empty.
    """
    if recipient_account_id and recipient_account_id.startswith("acct_"):
        return {"status": "success", "valid": True}
    else:
        return {"status": "error", "valid": False, "error": "Invalid Stripe Connect Account ID"}

def send_transfer(sender_customer_id, recipient_account_id, amount_cents):
    """
    Call backend (Stripe) to create a destination charge from sender customer to recipient connect account.
    """
    try:
        payload = {
            "sender_customer_id": sender_customer_id,
            "recipient_account_id": recipient_account_id,
            "amount_cents": amount_cents
        }
        res = requests.post(f"{BACKEND_URL}/charge_and_transfer", json=payload, timeout=15)
        data = res.json()

        if res.status_code == 200 and data.get("status") == "success":
            log_payment(
                amount=amount_cents / 100,
                currency="GBP",
                recipient=recipient_account_id,
                status="Completed",
                charge_id=data.get("charge_id")
            )
        else:
            log_payment(
                amount=amount_cents / 100,
                currency="GBP",
                recipient=recipient_account_id,
                status="Failed",
                error=data.get("error") or res.text
            )
        return data

    except Exception as e:
        log_payment(
            amount=amount_cents / 100,
            currency="GBP",
            recipient=recipient_account_id,
            status="Error",
            error=str(e)
        )
        print("[ERROR] Transfer request failed:", e)
        return {"status": "error", "error": str(e)}
