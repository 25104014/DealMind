def calculate_profit(price, cost):
    return price - cost


def evaluate_deal(
    selling_price,
    product_cost,
    minimum_price,
    buyer_budget,
    inventory,
    buyer_intent
):
    """
    Decide whether DealMind should:
    ACCEPT, COUNTER, or REJECT
    """

    # Calculate normal and minimum profit
    normal_profit = calculate_profit(
        selling_price,
        product_cost
    )

    minimum_profit = calculate_profit(
        minimum_price,
        product_cost
    )

    # ------------------------------------------------
    # CASE 1: Buyer can pay the normal selling price
    # ------------------------------------------------
    if buyer_budget >= selling_price:

        return {
            "decision": "ACCEPT",
            "offer_price": selling_price,
            "profit": normal_profit,
            "reason": "Buyer budget is sufficient for the full price."
        }

    # ------------------------------------------------
    # CASE 2: Buyer cannot pay full price,
    # but can pay merchant's minimum price
    # ------------------------------------------------
    if buyer_budget >= minimum_price:

        return {
            "decision": "ACCEPT",
            "offer_price": buyer_budget,
            "profit": buyer_budget - product_cost,
            "reason": "Buyer budget satisfies the merchant's minimum price."
        }

    # ------------------------------------------------
    # CASE 3: Buyer budget is below minimum price
    # Try a counter-offer
    # ------------------------------------------------

    # Start slightly above the minimum acceptable price
    counter_offer = minimum_price + 1000

    # Do not exceed the original selling price
    counter_offer = min(
        counter_offer,
        selling_price
    )

    # If inventory is high, merchant has more flexibility
    if inventory >= 10 and buyer_intent == "High":

        return {
            "decision": "COUNTER",
            "offer_price": counter_offer,
            "profit": counter_offer - product_cost,
            "reason": (
                "High purchase intent and sufficient inventory "
                "justify a controlled counter-offer."
            )
        }

    # ------------------------------------------------
    # CASE 4: Merchant should reject
    # ------------------------------------------------

    return {
        "decision": "REJECT",
        "offer_price": None,
        "profit": None,
        "reason": (
            "Buyer budget is below the merchant's "
            "minimum acceptable price."
        )
    }
def negotiate_round(
    current_offer,
    buyer_budget,
    minimum_price,
    product_cost,
    buyer_intent,
    inventory
):
    """
    Handle one negotiation round.
    """

    # Buyer can accept the current offer
    if current_offer <= buyer_budget:
        return {
            "status": "ACCEPTED",
            "offer": current_offer,
            "message": (
                f"Deal accepted at ₹{current_offer:,.0f}."
            )
        }

    # Calculate the next merchant counter-offer
    difference = current_offer - buyer_budget

    next_offer = current_offer - (difference / 2)

    # Never go below merchant minimum
    next_offer = max(
        next_offer,
        minimum_price
    )

    # If buyer is still below minimum,
    # merchant cannot safely continue.
    if buyer_budget < minimum_price:
        return {
            "status": "NEGOTIATE",
            "offer": next_offer,
            "message": (
                f"DealMind counter-offers "
                f"₹{next_offer:,.0f}."
            )
        }

    return {
        "status": "ACCEPTED",
        "offer": buyer_budget,
        "message": (
            f"DealMind accepts ₹{buyer_budget:,.0f}."
        )
    }