import os
import razorpay

from dotenv import load_dotenv


# Load variables from .env
load_dotenv()


def get_razorpay_client():

    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")

    if not key_id or not key_secret:
        raise ValueError(
            "Razorpay API credentials were not found."
        )

    client = razorpay.Client(
        auth=(key_id, key_secret)
    )

    return client


def create_payment_order(
    amount,
    receipt
):

    try:

        client = get_razorpay_client()

        # Razorpay accepts INR in paise
        amount_in_paise = int(amount * 100)

        order_data = {
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": receipt
        }

        order = client.order.create(
            data=order_data
        )

        return {
            "success": True,
            "order_id": order["id"],
            "amount": order["amount"] / 100,
            "currency": order["currency"],
            "status": order["status"]
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }