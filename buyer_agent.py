import os
import json
from dotenv import load_dotenv
from openai import OpenAI


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise ValueError(
        "OPENROUTER_API_KEY was not found. "
        "Please check your .env file."
    )


# ============================================================
# OPENROUTER CLIENT
# ============================================================

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)


# ============================================================
# BUYER AGENT
# ============================================================

class BuyerAgent:

    def __init__(self, budget, intent):

        self.budget = budget
        self.intent = intent
        self.current_offer = 0


    # ========================================================
    # INITIAL BUYER OFFER
    # ========================================================

    def make_offer(self, selling_price):

        if self.intent == "High":

            offer_percent = 0.92

        elif self.intent == "Medium":

            offer_percent = 0.85

        else:

            offer_percent = 0.75


        self.current_offer = min(
            selling_price * offer_percent,
            self.budget
        )

        return self.current_offer


    # ========================================================
    # BUYER RESPONSE TO MERCHANT COUNTER
    # ========================================================

    def respond_to_counter(self, merchant_offer):

        # Buyer accepts if merchant offer is within budget

        if merchant_offer <= self.budget:

            return {
                "decision": "ACCEPT",
                "offer": merchant_offer
            }


        # Calculate the gap

        gap = merchant_offer - self.current_offer


        # Move halfway toward merchant price

        new_offer = (
            self.current_offer +
            (gap * 0.5)
        )


        # Never exceed buyer budget

        new_offer = min(
            new_offer,
            self.budget
        )


        self.current_offer = new_offer


        return {
            "decision": "COUNTER",
            "offer": new_offer
        }


    # ========================================================
    # LLM MERCHANT OFFER RECOMMENDATION
    # ========================================================

    def recommend_merchant_offer(
        self,
        buyer_message,
        selling_price,
        product_cost,
        minimum_price,
        current_buyer_offer,
        strategy
    ):

        """
        Uses the LLM to recommend the next merchant offer.

        The LLM provides intelligence.

        Python guardrails provide financial control.
        """


        prompt = f"""
You are DealMind, an autonomous merchant negotiation agent.

Your objective is to help the merchant close a profitable
transaction while respecting strict merchant constraints.

Analyze the buyer and recommend the best merchant response.

============================================================
BUYER INFORMATION
============================================================

Buyer message:
{buyer_message}

Buyer maximum budget:
₹{self.budget}

Current buyer offer:
₹{current_buyer_offer}

Buyer purchase intent:
{self.intent}


============================================================
MERCHANT INFORMATION
============================================================

Product selling price:
₹{selling_price}

Product cost:
₹{product_cost}

Protected minimum price:
₹{minimum_price}

Merchant strategy:
{strategy}


============================================================
YOUR TASK
============================================================

Determine whether the merchant should:

1. ACCEPT the buyer's current offer
2. COUNTER with another price
3. REJECT because a profitable deal is not possible


Consider:

- buyer budget
- buyer intent
- buyer urgency
- buyer flexibility
- buyer preferences
- merchant profit
- conversion probability
- merchant strategy
- price gap


============================================================
STRICT RULES
============================================================

The merchant MUST NEVER sell below the protected minimum price.

The merchant MUST NEVER sell below product cost.

The merchant MUST NEVER offer more than the normal selling price.

The recommended offer must be affordable for the buyer.

Do not invent buyer information.

Return ONLY valid JSON.

Required format:

{{
    "recommended_offer": number,
    "decision": "ACCEPT" or "COUNTER" or "REJECT",
    "reason": "short explanation",
    "confidence": number
}}

Confidence must be between 0 and 1.
"""


        try:

            response = client.chat.completions.create(

                model="openrouter/free",

                messages=[

                    {
                        "role": "system",
                        "content": (
                            "You are DealMind, a careful, "
                            "explainable and financially "
                            "bounded commerce negotiation agent. "
                            "Always return valid JSON."
                        )
                    },

                    {
                        "role": "user",
                        "content": prompt
                    }

                ],

                temperature=0.2
            )


            result = (
                response
                .choices[0]
                .message
                .content
                .strip()
            )


            # =================================================
            # REMOVE MARKDOWN CODE FENCES
            # =================================================

            if result.startswith("```"):

                result = result.replace(
                    "```json",
                    ""
                )

                result = result.replace(
                    "```",
                    ""
                )

                result = result.strip()


            # =================================================
            # CONVERT LLM RESPONSE TO JSON
            # =================================================

            data = json.loads(result)


            # =================================================
            # GET RECOMMENDED OFFER
            # =================================================

            recommended_offer = float(
                data["recommended_offer"]
            )


            # =================================================
            # HARD MERCHANT SAFETY CHECK
            # =================================================

            # If buyer cannot reach merchant minimum,
            # a valid transaction cannot happen.

            if self.budget < minimum_price:

                return {

                    "recommended_offer": self.budget,

                    "decision": "REJECT",

                    "reason": (
                        "The buyer's maximum budget is "
                        "below the merchant's protected "
                        "minimum price. A financially valid "
                        "deal cannot be created."
                    ),

                    "confidence": 1.0
                }


            # =================================================
            # GUARDRAIL 1 — MINIMUM PRICE
            # =================================================

            recommended_offer = max(
                recommended_offer,
                minimum_price
            )


            # =================================================
            # GUARDRAIL 2 — SELLING PRICE
            # =================================================

            recommended_offer = min(
                recommended_offer,
                selling_price
            )


            # =================================================
            # GUARDRAIL 3 — BUYER BUDGET
            # =================================================

            recommended_offer = min(
                recommended_offer,
                self.budget
            )


            # =================================================
            # GUARDRAIL 4 — PRODUCT COST
            # =================================================

            if recommended_offer < product_cost:

                return {

                    "recommended_offer": recommended_offer,

                    "decision": "REJECT",

                    "reason": (
                        "The recommended price would not "
                        "protect the merchant's product cost."
                    ),

                    "confidence": 1.0
                }


            # =================================================
            # VALIDATE DECISION
            # =================================================

            decision = data.get(
                "decision",
                "COUNTER"
            )

            if decision not in [
                "ACCEPT",
                "COUNTER",
                "REJECT"
            ]:

                decision = "COUNTER"


            # =================================================
            # CONFIDENCE
            # =================================================

            confidence = float(
                data.get(
                    "confidence",
                    0.5
                )
            )


            confidence = max(
                0.0,
                min(
                    confidence,
                    1.0
                )
            )


            # =================================================
            # UPDATE AGENT STATE
            # =================================================

            self.current_offer = (
                recommended_offer
            )


            # =================================================
            # RETURN LLM DECISION
            # =================================================

            return {

                "recommended_offer":
                    recommended_offer,

                "decision":
                    decision,

                "reason":
                    data.get(
                        "reason",
                        "Offer generated based on buyer and merchant context."
                    ),

                "confidence":
                    confidence
            }


        except Exception as e:

            print(
                "Negotiation LLM Error:",
                e
            )


            # =================================================
            # SAFE FALLBACK
            # =================================================

            if self.budget < minimum_price:

                return {

                    "recommended_offer":
                        self.budget,

                    "decision":
                        "REJECT",

                    "reason":
                        (
                            "The buyer's budget is below "
                            "the merchant's protected minimum."
                        ),

                    "confidence":
                        0.0
                }


            safe_offer = max(
                minimum_price,
                product_cost
            )


            safe_offer = min(
                safe_offer,
                selling_price,
                self.budget
            )


            return {

                "recommended_offer":
                    safe_offer,

                "decision":
                    "COUNTER",

                "reason":
                    (
                        "The LLM was temporarily unavailable. "
                        "DealMind applied the merchant's "
                        "financial safety rules."
                    ),

                "confidence":
                    0.0
            }


# ============================================================
# BUYER MESSAGE UNDERSTANDING
# ============================================================

def understand_buyer_message(message):

    """
    Uses the OpenRouter LLM to extract buyer intent,
    budget, flexibility, urgency, requirements and preferences.
    """


    prompt = f"""
You are DealMind's Buyer Intelligence Agent.

Analyze this buyer message:

"{message}"


Extract:

- budget
- flexibility
- urgency
- requirement
- preferences


Return ONLY valid JSON using exactly this structure:

{{
    "budget": number or null,
    "flexibility": "Low" or "Medium" or "High" or "Unknown",
    "urgency": "Low" or "Medium" or "High" or "Unknown",
    "requirement": "short description",
    "preferences": ["preference1", "preference2"]
}}


RULES:

1. Extract the buyer's budget only when it is explicitly
   mentioned or clearly stated.

2. If no budget is mentioned, return null.

3. "maximum budget", "cannot exceed", "my limit is"
   generally indicate Low flexibility.

4. "around", "approximately", "roughly"
   generally indicate Medium flexibility.

5. "I can negotiate", "flexible", "I can stretch"
   generally indicate High flexibility.

6. Words such as "today", "immediately", "urgent"
   indicate High urgency.

7. "soon" generally indicates Medium urgency.

8. If urgency is not mentioned, return Unknown.

9. Requirement should describe what the buyer actually wants.

10. Preferences should contain useful preferences explicitly
    mentioned by the buyer.

11. Do not invent information.

12. Always return valid JSON.
"""


    try:

        response = client.chat.completions.create(

            model="openrouter/free",

            messages=[

                {
                    "role": "system",
                    "content": (
                        "You are a precise buyer-intent "
                        "analysis agent. "
                        "Return only valid JSON."
                    )
                },

                {
                    "role": "user",
                    "content": prompt
                }

            ],

            temperature=0.2
        )


        result = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )


        # =====================================================
        # REMOVE MARKDOWN CODE FENCES
        # =====================================================

        if result.startswith("```"):

            result = result.replace(
                "```json",
                ""
            )

            result = result.replace(
                "```",
                ""
            )

            result = result.strip()


        # =====================================================
        # PARSE JSON
        # =====================================================

        data = json.loads(result)


        # =====================================================
        # ENSURE REQUIRED FIELDS EXIST
        # =====================================================

        return {

            "budget":
                data.get("budget"),

            "flexibility":
                data.get(
                    "flexibility",
                    "Unknown"
                ),

            "urgency":
                data.get(
                    "urgency",
                    "Unknown"
                ),

            "requirement":
                data.get(
                    "requirement",
                    message
                ),

            "preferences":
                data.get(
                    "preferences",
                    []
                )
        }


    except Exception as e:

        print(
            "Buyer Analysis LLM Error:",
            e
        )


        # =====================================================
        # SAFE FALLBACK
        # =====================================================

        return {

            "budget":
                None,

            "flexibility":
                "Unknown",

            "urgency":
                "Unknown",

            "requirement":
                message,

            "preferences":
                []
        }