import os
import razorpay

from dotenv import load_dotenv


# Load environment variables
load_dotenv()


# Get Razorpay credentials
key_id = os.getenv("RAZORPAY_KEY_ID")
key_secret = os.getenv("RAZORPAY_KEY_SECRET")


if not key_id or not key_secret:

    print("❌ Razorpay API credentials were not found.")
    print("Please check your .env file.")

    raise SystemExit


print("✅ Razorpay API credentials found.")
print("🔄 Connecting to Razorpay...")


try:

    client = razorpay.Client(
        auth=(key_id, key_secret)
    )

    # ₹100 = 10,000 paise
    order_data = {
        "amount": 10000,
        "currency": "INR",
        "receipt": "test_dealmind_001"
    }

    order = client.order.create(
        data=order_data
    )

    print("\n🎉 RAZORPAY CONNECTION SUCCESSFUL!\n")

    print("Order ID:", order["id"])
    print("Amount:", order["amount"] / 100, "INR")
    print("Currency:", order["currency"])
    print("Status:", order["status"])


except Exception as e:

    print("\n❌ Razorpay Error:\n")
    print(e)