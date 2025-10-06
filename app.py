import os
import stripe
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@app.route('/charge_and_transfer', methods=['POST'])
def charge_and_transfer():
    data = request.json
    sender_customer_id = data.get("sender_customer_id")
    recipient_account_id = data.get("recipient_account_id")
    amount_cents = data.get("amount_cents")

    try:
        # Create a PaymentIntent with transfer_data for destination charge
        payment_intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency='gbp',
            customer=sender_customer_id,
            payment_method_types=["card"],
            payment_method="pm_card_visa",  # For testing, in prod get real pm
            off_session=True,
            confirm=True,
            transfer_data={"destination": recipient_account_id},
        )
        return jsonify({
            "status": "success",
            "charge_id": payment_intent.id,
            "message": "Charge successful"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 400

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))  # Render sets PORT
    app.run(host="0.0.0.0", port=port)
