import os
import hmac
import hashlib


# ============================================================
# RAZORPAY CONFIGURATION
# ============================================================

RAZORPAY_KEY_SECRET = os.getenv(
    "RAZORPAY_KEY_SECRET",
    ""
)


# ============================================================
# PAYMENT SIGNATURE VERIFICATION
# ============================================================

def verify_payment_signature(
    order_id,
    payment_id,
    signature
):
    """
    Verify that the payment response genuinely
    came from Razorpay.

    Returns:
        dict:
        {
            "success": True/False,
            "message": "..."
        }
    """

    try:

        # ----------------------------------------------------
        # CHECK SECRET
        # ----------------------------------------------------

        if not RAZORPAY_KEY_SECRET:

            return {
                "success": False,
                "message": (
                    "RAZORPAY_KEY_SECRET is not configured."
                )
            }


        # ----------------------------------------------------
        # CREATE VERIFICATION DATA
        # ----------------------------------------------------

        data = (
            f"{order_id}|{payment_id}"
        )


        # ----------------------------------------------------
        # GENERATE EXPECTED SIGNATURE
        # ----------------------------------------------------

        generated_signature = hmac.new(

            bytes(
                RAZORPAY_KEY_SECRET,
                "utf-8"
            ),

            bytes(
                data,
                "utf-8"
            ),

            hashlib.sha256

        ).hexdigest()


        # ----------------------------------------------------
        # COMPARE SIGNATURES SECURELY
        # ----------------------------------------------------

        is_valid = hmac.compare_digest(
            generated_signature,
            signature
        )


        # ----------------------------------------------------
        # RETURN RESULT
        # ----------------------------------------------------

        if is_valid:

            return {

                "success": True,

                "message": (
                    "Payment signature verified successfully."
                )

            }


        else:

            return {

                "success": False,

                "message": (
                    "Payment signature verification failed. "
                    "The payment response may not be valid."
                )

            }


    except Exception as e:

        return {

            "success": False,

            "message": (
                f"Payment verification error: {str(e)}"
            )

        }
   