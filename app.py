import streamlit as st
import streamlit.components.v1 as components
import uuid
import os
import json
import random

from dotenv import load_dotenv
from openai import OpenAI

from core.negotiation import (
    evaluate_deal,
    negotiate_round
)

from agents.buyer_agent import (
    BuyerAgent,
    understand_buyer_message
)

from core.payment_gateway import create_payment_order
from core.payment_verification import verify_payment_signature


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="DealMind",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# LOAD CUSTOM CSS
# ============================================================

def load_css():
    css_path = os.path.join("assets", "style.css")

    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as css_file:
            st.markdown(
                f"<style>{css_file.read()}</style>",
                unsafe_allow_html=True
            )


load_css()


# ============================================================
# RAZORPAY CONFIGURATION
# ============================================================

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")


# ============================================================
# OPENROUTER CONFIGURATION
# ============================================================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")


# ============================================================
# FAST TRACK CONFIGURATION
# ============================================================

AUTO_ACCEPT_BUDGET_THRESHOLD = 68000.0


# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================

DEFAULT_SESSION_VALUES = {
    "negotiation_started": False,
    "current_offer": None,
    "round_number": 0,
    "conversation": [],
    "buyer_analysis": None,
    "deal_status": "NOT_STARTED",
    "final_price": None,
    "final_reason": "",

    "payment_order": None,
    "payment_status": "NOT_CREATED",
    "payment_verification_result": None,

    "product_name": "Business Laptop",
    "selling_price": 70000.0,
    "max_discount_percent": 12.0,
    "product_cost": 58000.0,
    "minimum_price": 64000.0,
    "negotiation_strategy": "Balanced",
    "inventory": 18,
    "max_rounds": 5,

    "buyer_budget": 68000.0,
    "buyer_intent": "High",

    "buyer_requirement": (
        "I need a reliable laptop for software development."
    ),

    "buyer_message": (
        "I need a reliable laptop for software development. "
        "My budget is around ₹68,000, and I'd like to close "
        "the deal today if possible."
    )
}


for key, value in DEFAULT_SESSION_VALUES.items():

    if key not in st.session_state:
        st.session_state[key] = value


if "wizard_page" not in st.session_state:
    st.session_state.wizard_page = 0


if "success_voice_played" not in st.session_state:
    st.session_state.success_voice_played = False


if "failure_voice_played" not in st.session_state:
    st.session_state.failure_voice_played = False


if "ai_chat_history" not in st.session_state:
    st.session_state.ai_chat_history = []


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def close_deal(final_price, reason="Deal successfully accepted."):

    st.session_state.deal_status = "ACCEPTED"
    st.session_state.final_price = float(final_price)
    st.session_state.final_reason = reason


def reject_deal(reason):

    st.session_state.deal_status = "REJECTED"
    st.session_state.final_price = None
    st.session_state.final_reason = reason


def reset_application():

    keep_keys = (
        "product_name",
        "selling_price",
        "max_discount_percent",
        "product_cost",
        "minimum_price",
        "negotiation_strategy",
        "inventory",
        "max_rounds",
        "buyer_budget",
        "buyer_intent",
        "buyer_requirement",
        "buyer_message"
    )

    for key, value in DEFAULT_SESSION_VALUES.items():

        if key not in keep_keys:
            st.session_state[key] = value


# ============================================================
# BROWSER VOICE ANNOUNCEMENT
# ============================================================

def speak_message(message):

    escaped_message = json.dumps(message)

    components.html(
        f"""
        <script>
            window.parent.speechSynthesis.cancel();

            const message = new SpeechSynthesisUtterance(
                {escaped_message}
            );

            message.rate = 0.9;
            message.pitch = 1;
            message.volume = 1;

            window.parent.speechSynthesis.speak(message);
        </script>
        """,
        height=0
    )


# ============================================================
# RAZORPAY CHECKOUT
# ============================================================

def show_razorpay_checkout(order_id, amount, product_name):

    if not RAZORPAY_KEY_ID:

        st.error(
            "❌ Razorpay Key ID is missing. "
            "Please configure RAZORPAY_KEY_ID."
        )

        return


    amount_paise = int(float(amount) * 100)


    checkout_options = {
        "key": RAZORPAY_KEY_ID,
        "amount": amount_paise,
        "currency": "INR",
        "name": "DealMind",
        "description": f"Payment for {product_name}",
        "order_id": order_id,
        "theme": {
            "color": "#0f4dff"
        }
    }


    options_json = json.dumps(checkout_options)


    checkout_html = f"""
    <!DOCTYPE html>

    <html>

    <head>

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <script src="https://checkout.razorpay.com/v1/checkout.js"></script>

        <style>

            html,
            body {{
                margin: 0;
                padding: 0;
                height: 100%;
                background: transparent;
                font-family: Arial, sans-serif;
            }}

            body {{
                padding: 20px;
                display: flex;
                justify-content: center;
                align-items: flex-start;
            }}

            button {{
                width: 100%;
                max-width: 600px;
                background: linear-gradient(
                    135deg,
                    #0f4dff,
                    #072e99
                );
                color: white;
                border: none;
                padding: 18px 30px;
                font-size: 18px;
                font-weight: 700;
                border-radius: 12px;
                cursor: pointer;
            }}

            .result-card {{
                width: 100%;
                max-width: 600px;
                text-align: center;
                padding: 26px;
                background: #f0fdf4;
                border: 1px solid #bbf7d0;
                border-radius: 16px;
                color: #166534;
                box-sizing: border-box;
            }}

            .field-row {{
                text-align: left;
                margin: 14px 0;
            }}

            .field-row label {{
                display: block;
                font-size: 12px;
                font-weight: 700;
                margin-bottom: 4px;
            }}

            .field-with-copy {{
                display: flex;
                gap: 8px;
            }}

            .field-with-copy input {{
                flex: 1;
                padding: 10px;
                border-radius: 8px;
                border: 1px solid #86efac;
            }}

            .copy-btn {{
                width: auto;
                min-width: 70px;
                padding: 10px;
                font-size: 13px;
                background: #16a34a;
            }}

        </style>

    </head>

    <body>

        <button id="rzp-button">
            💳 Proceed to Secure Payment
        </button>


        <script>

            var options = {options_json};


            options.handler = function(response) {{

                var paymentId =
                    response.razorpay_payment_id || "";

                var orderId =
                    response.razorpay_order_id || "";

                var signature =
                    response.razorpay_signature || "";


                document.body.innerHTML = `

                    <div class="result-card">

                        <h2>
                            🎉 Payment Successful!
                        </h2>

                        <p>
                            Copy the details below and paste them
                            into the DealMind verification section.
                        </p>


                        <div class="field-row">

                            <label>
                                Razorpay Payment ID
                            </label>

                            <div class="field-with-copy">

                                <input
                                    id="payment-id"
                                    readonly
                                    value="${{paymentId}}"
                                >

                                <button
                                    class="copy-btn"
                                    onclick="copyValue('payment-id')"
                                >
                                    Copy
                                </button>

                            </div>

                        </div>


                        <div class="field-row">

                            <label>
                                Razorpay Order ID
                            </label>

                            <div class="field-with-copy">

                                <input
                                    id="order-id"
                                    readonly
                                    value="${{orderId}}"
                                >

                                <button
                                    class="copy-btn"
                                    onclick="copyValue('order-id')"
                                >
                                    Copy
                                </button>

                            </div>

                        </div>


                        <div class="field-row">

                            <label>
                                Razorpay Signature
                            </label>

                            <div class="field-with-copy">

                                <input
                                    id="signature"
                                    readonly
                                    value="${{signature}}"
                                >

                                <button
                                    class="copy-btn"
                                    onclick="copyValue('signature')"
                                >
                                    Copy
                                </button>

                            </div>

                        </div>

                    </div>

                `;

            }};


            function copyValue(id) {{

                var input =
                    document.getElementById(id);

                input.select();

                navigator.clipboard.writeText(
                    input.value
                );

            }}


            var rzp =
                new Razorpay(options);


            document
                .getElementById("rzp-button")
                .onclick = function(event) {{

                    rzp.open();

                    event.preventDefault();

                }};

        </script>

    </body>

    </html>
    """


    components.html(
        checkout_html,
        height=700,
        scrolling=True
    )


# ============================================================
# ANIMATION HELPERS
# ============================================================

def render_walking_buyer(caption):

    st.markdown(
        f"""
        <div class="walk-track">

            <div class="walking-figure">
                🚶‍♂️
            </div>

            <div class="walk-caption">
                {caption}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


def render_money_rain(count=28):

    symbols = [
        "₹",
        "💵",
        "🪙",
        "💸"
    ]

    pieces = []


    for _ in range(count):

        left = random.randint(0, 96)

        delay = round(
            random.uniform(0, 2.2),
            2
        )

        duration = round(
            random.uniform(2.6, 4.6),
            2
        )

        size = round(
            random.uniform(1.0, 1.9),
            2
        )

        symbol = random.choice(symbols)


        pieces.append(
            f'''
            <span
                class="money-piece"
                style="
                    left:{left}%;
                    animation-delay:{delay}s;
                    animation-duration:{duration}s;
                    font-size:{size}rem;
                "
            >
                {symbol}
            </span>
            '''
        )


    st.markdown(
        f'''
        <div class="money-rain">
            {"".join(pieces)}
        </div>
        ''',
        unsafe_allow_html=True
    )


# ============================================================
# WIZARD CONFIGURATION
# ============================================================

STEPS = [

    {
        "icon": "✨",
        "label": "Welcome"
    },

    {
        "icon": "🏪",
        "label": "Merchant Setup"
    },

    {
        "icon": "🤖",
        "label": "AI Buyer"
    },

    {
        "icon": "🤝",
        "label": "Negotiation"
    },

    {
        "icon": "💳",
        "label": "Payment & Outcome"
    }

]


QUOTES = [

    {
        "eyebrow": "TRUST, BUILT IN",
        "title": "Trust is the currency of modern commerce.",
        "body": (
            "DealMind is a Razorpay-inspired negotiation engine "
            "where AI-driven conversations meet merchant-grade safety."
        ),
        "tags": [
            "🧠 AI-Powered Negotiation",
            "🔒 Merchant Protection",
            "💳 Secure Payments"
        ]
    },

    {
        "eyebrow": "STEP 1 · FOUNDATIONS",
        "title": "Every great deal starts with a protected foundation.",
        "body": (
            "Set your pricing, margins and discount limits."
        ),
        "tags": [
            "📊 Clear Economics",
            "🛡️ Guardrailed Discounts"
        ]
    },

    {
        "eyebrow": "STEP 2 · UNDERSTANDING INTENT",
        "title": "Understanding intent is the first step to a great transaction.",
        "body": (
            "Describe your buyer in plain language."
        ),
        "tags": [
            "💬 Natural Language",
            "🎯 Intent Detection"
        ]
    },

    {
        "eyebrow": "STEP 3 · THE CONVERSATION",
        "title": "Where intelligent conversations become confident decisions.",
        "body": (
            "Watch the negotiation unfold round by round."
        ),
        "tags": [
            "🔁 Round-by-Round",
            "⚡ Fast-Track Accept"
        ]
    },

    {
        "eyebrow": "STEP 4 · SETTLEMENT",
        "title": "Payments that just work — every single time.",
        "body": (
            "Complete the deal using secure payment verification."
        ),
        "tags": [
            "🔒 Signature Verified",
            "⚡ Secure Payment"
        ]
    }

]


def render_quote_banner(step_index):

    quote = QUOTES[step_index]


    tags_html = "<span>•</span>".join(
        f"<div class='tag-pill'>{tag}</div>"
        for tag in quote["tags"]
    )


    st.markdown(
        f"""
        <div class="razorpay-quote-section">

            <div class="quote-label">
                {quote['eyebrow']}
            </div>

            <h1>
                {quote['title']}
            </h1>

            <p>
                {quote['body']}
            </p>

            <div class="quote-highlights">
                {tags_html}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


def go_to_page(index):

    st.session_state.wizard_page = index

    st.rerun()


def render_stepper():

    current = st.session_state.wizard_page


    st.markdown(
        '<div class="stepper-wrapper">',
        unsafe_allow_html=True
    )


    cols = st.columns(len(STEPS))


    for i, (col, step) in enumerate(
        zip(cols, STEPS)
    ):

        with col:

            state_class = (

                "done"

                if i < current

                else "active"

                if i == current

                else "upcoming"

            )


            st.markdown(
                f"""
                <div class="step-indicator {state_class}">

                    <div class="step-circle">
                        {step['icon']}
                    </div>

                    <div class="step-label">
                        {step['label']}
                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )


            if st.button(
                " ",
                key=f"step_jump_{i}",
                help=f"Go to {step['label']}"
            ):

                go_to_page(i)


    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )


def render_nav_buttons(
    back_enabled=True,
    next_enabled=True,
    next_label="Continue →",
    next_help=None
):

    st.markdown("<br>", unsafe_allow_html=True)


    col_back, col_spacer, col_next = st.columns(
        [1, 3, 1]
    )


    with col_back:

        if (
            back_enabled
            and st.session_state.wizard_page > 0
        ):

            if st.button(
                "← Back",
                use_container_width=True
            ):

                go_to_page(
                    st.session_state.wizard_page - 1
                )


    with col_next:

        if (
            st.session_state.wizard_page
            < len(STEPS) - 1
        ):

            if st.button(
                next_label,
                type="primary",
                use_container_width=True,
                disabled=not next_enabled,
                help=next_help
            ):

                go_to_page(
                    st.session_state.wizard_page + 1
                )


# ============================================================
# SESSION VARIABLES
# ============================================================

product_name = st.session_state.product_name
selling_price = st.session_state.selling_price
max_discount_percent = st.session_state.max_discount_percent
product_cost = st.session_state.product_cost
minimum_price = st.session_state.minimum_price
negotiation_strategy = st.session_state.negotiation_strategy
inventory = st.session_state.inventory
max_rounds = st.session_state.max_rounds
buyer_budget = st.session_state.buyer_budget
buyer_intent = st.session_state.buyer_intent
buyer_requirement = st.session_state.buyer_requirement
buyer_message = st.session_state.buyer_message


discount_based_minimum = (
    selling_price
    * (1 - max_discount_percent / 100)
)


effective_minimum_price = max(
    minimum_price,
    discount_based_minimum,
    product_cost
)


# ============================================================
# STEPPER NAVIGATION
# ============================================================

render_stepper()

render_quote_banner(
    st.session_state.wizard_page
)


# ============================================================
# PAGE 0 — WELCOME
# ============================================================

if st.session_state.wizard_page == 0:

    render_walking_buyer(
        "A buyer just walked in, ready to negotiate…"
    )


    st.markdown("### What DealMind does")


    c1, c2, c3 = st.columns(3)


    with c1:

        st.markdown(
            """
            <div class="feature-card">
                <div class="feature-icon">🏪</div>
                <h4>Merchant-Safe Pricing</h4>
                <p>Set a floor price the AI can never cross.</p>
            </div>
            """,
            unsafe_allow_html=True
        )


    with c2:

        st.markdown(
            """
            <div class="feature-card">
                <div class="feature-icon">🤖</div>
                <h4>AI-Understood Buyers</h4>
                <p>Natural language turned into buyer intent.</p>
            </div>
            """,
            unsafe_allow_html=True
        )


    with c3:

        st.markdown(
            """
            <div class="feature-card">
                <div class="feature-icon">💳</div>
                <h4>Secure Checkout</h4>
                <p>Razorpay-powered payment verification.</p>
            </div>
            """,
            unsafe_allow_html=True
        )


    st.markdown("<br>", unsafe_allow_html=True)


    if st.button(
        "🚀 Get Started",
        type="primary",
        use_container_width=True
    ):

        go_to_page(1)


# ============================================================
# PAGE 1 — MERCHANT SETUP
# ============================================================

elif st.session_state.wizard_page == 1:

    st.header("🏪 Merchant Configuration")


    col1, col2 = st.columns(2)


    with col1:

        st.text_input(
            "Product Name",
            key="product_name"
        )


        st.number_input(
            "Selling Price (₹)",
            min_value=1.0,
            step=1000.0,
            key="selling_price"
        )


        st.number_input(
            "Maximum Discount Allowed (%)",
            min_value=0.0,
            max_value=100.0,
            step=1.0,
            key="max_discount_percent"
        )


    with col2:

        st.number_input(
            "Product Cost (₹)",
            min_value=1.0,
            step=1000.0,
            key="product_cost"
        )


        st.number_input(
            "Minimum Acceptable Price (₹)",
            min_value=1.0,
            step=1000.0,
            key="minimum_price"
        )


        st.selectbox(
            "Merchant Negotiation Goal",
            [
                "Maximum Profit",
                "Balanced",
                "Maximum Conversion"
            ],
            key="negotiation_strategy"
        )


    st.number_input(
        "Inventory Available",
        min_value=0,
        step=1,
        key="inventory"
    )


    st.number_input(
        "Maximum Negotiation Rounds",
        min_value=1,
        max_value=10,
        step=1,
        key="max_rounds"
    )


    discount_based_minimum = (
        st.session_state.selling_price
        * (
            1
            - st.session_state.max_discount_percent
            / 100
        )
    )


    effective_minimum_price = max(
        st.session_state.minimum_price,
        discount_based_minimum,
        st.session_state.product_cost
    )


    normal_profit = (
        st.session_state.selling_price
        - st.session_state.product_cost
    )


    st.divider()

    st.header("📊 Merchant Economics")


    c1, c2, c3, c4 = st.columns(4)


    with c1:

        st.metric(
            "Selling Price",
            f"₹{st.session_state.selling_price:,.0f}"
        )


    with c2:

        st.metric(
            "Product Cost",
            f"₹{st.session_state.product_cost:,.0f}"
        )


    with c3:

        st.metric(
            "Normal Profit",
            f"₹{normal_profit:,.0f}"
        )


    with c4:

        st.metric(
            "Protected Minimum",
            f"₹{effective_minimum_price:,.0f}"
        )


    st.info(
        f"""
🔒 **Merchant Safety Protection**

DealMind will not accept a deal below
**₹{effective_minimum_price:,.0f}**.
"""
    )


    render_nav_buttons(
        back_enabled=False
    )


# ============================================================
# PAGE 2 — AI BUYER
# ============================================================

elif st.session_state.wizard_page == 2:

    st.header("🤖 AI Buyer Simulator")


    render_walking_buyer(
        "Reading the buyer's intent…"
    )


    col1, col2 = st.columns(2)


    with col1:

        st.number_input(
            "AI Buyer's Maximum Budget (₹)",
            min_value=1.0,
            step=1000.0,
            key="buyer_budget"
        )


    with col2:

        st.selectbox(
            "Purchase Intent",
            [
                "Low",
                "Medium",
                "High"
            ],
            key="buyer_intent"
        )


    st.text_area(
        "Buyer's Requirement",
        key="buyer_requirement"
    )


    st.text_area(
        "💬 Natural Language Buyer Request",
        key="buyer_message",
        height=120
    )


    if st.button(
        "🧠 Analyze Buyer with AI",
        use_container_width=True
    ):

        with st.spinner(
            "DealMind is understanding the buyer..."
        ):

            try:

                analysis = understand_buyer_message(
                    st.session_state.buyer_message
                )

                st.session_state.buyer_analysis = analysis


            except Exception as error:

                st.error(
                    f"AI analysis failed:\n\n{error}"
                )


    if st.session_state.buyer_analysis:

        st.subheader(
            "🧠 DealMind's Understanding of the Buyer"
        )


        analysis = (
            st.session_state.buyer_analysis
        )


        detected_budget = analysis.get(
            "budget"
        )


        if detected_budget is not None:

            budget_display = (
                f"₹{float(detected_budget):,.0f}"
            )

        else:

            budget_display = "Not detected"


        c1, c2, c3 = st.columns(3)


        with c1:

            st.metric(
                "Detected Budget",
                budget_display
            )


        with c2:

            st.metric(
                "Flexibility",
                analysis.get(
                    "flexibility",
                    "Unknown"
                )
            )


        with c3:

            st.metric(
                "Urgency",
                analysis.get(
                    "urgency",
                    "Unknown"
                )
            )


        st.write(
            "**Requirement:**",
            analysis.get(
                "requirement",
                "Not detected"
            )
        )


    render_nav_buttons()


# ============================================================
# PAGE 3 — NEGOTIATION
# ============================================================

elif st.session_state.wizard_page == 3:

    st.header("🤝 Negotiation Room")


    render_walking_buyer(
        "The negotiation is live…"
    )


    col1, col2 = st.columns(2)


    with col1:

        start_button = st.button(
            "🚀 Start Negotiation",
            type="primary",
            use_container_width=True
        )


    with col2:

        reset_button = st.button(
            "🔄 Reset Negotiation",
            use_container_width=True
        )


    if reset_button:

        reset_application()

        st.rerun()


    if start_button:

        if inventory <= 0:

            reject_deal(
                "Product is currently out of stock."
            )


        elif (
            buyer_budget
            >= AUTO_ACCEPT_BUDGET_THRESHOLD
        ):

            fast_track_price = min(
                buyer_budget,
                selling_price
            )


            fast_track_price = max(
                fast_track_price,
                effective_minimum_price
            )


            st.session_state.negotiation_started = True
            st.session_state.round_number = 1


            st.session_state.conversation = [

                {
                    "speaker": "AI Buyer",
                    "message": (
                        f"My budget is ₹{buyer_budget:,.0f}. "
                        "Let's close this deal quickly."
                    )
                },

                {
                    "speaker": "DealMind",
                    "message": (
                        f"Deal accepted at "
                        f"₹{fast_track_price:,.0f}."
                    )
                }

            ]


            close_deal(
                fast_track_price,
                "Buyer qualified for fast-track acceptance."
            )


        else:

            st.session_state.negotiation_started = True

            st.session_state.round_number = 1

            st.session_state.conversation = []

            st.session_state.deal_status = "NEGOTIATING"

            st.session_state.final_price = None

            st.session_state.current_offer = buyer_budget


            st.session_state.conversation.append(
                {
                    "speaker": "AI Buyer",
                    "message": (
                        f"My maximum budget is "
                        f"₹{buyer_budget:,.0f}. "
                        "Can you give me a better deal?"
                    )
                }
            )


        st.rerun()


    if st.session_state.negotiation_started:

        st.divider()

        st.header("📍 Deal Status")


        status = st.session_state.deal_status


        if status == "NEGOTIATING":

            st.warning("🟡 NEGOTIATING")


        elif status == "ACCEPTED":

            st.success("🟢 DEAL ACCEPTED")


        elif status == "REJECTED":

            st.error("🔴 DEAL REJECTED")


    if (
        st.session_state.negotiation_started
        and st.session_state.deal_status == "NEGOTIATING"
    ):

        st.divider()

        st.header("🎯 Initial Deal Analysis")


        result = evaluate_deal(
            selling_price=selling_price,
            product_cost=product_cost,
            minimum_price=effective_minimum_price,
            buyer_budget=buyer_budget,
            inventory=inventory,
            buyer_intent=buyer_intent
        )


        decision = result["decision"]


        if decision == "ACCEPT":

            st.success(
                f"Deal can be accepted at "
                f"₹{result['offer_price']:,.0f}"
            )


        elif decision == "COUNTER":

            st.warning(
                f"Recommended counter offer: "
                f"₹{result['offer_price']:,.0f}"
            )


        else:

            st.error(
                "The buyer's initial offer does not "
                "satisfy merchant requirements."
            )


        st.write(
            f"**Reason:** {result['reason']}"
        )


        st.divider()

        st.header("💬 Live Negotiation")


        buyer_counter = st.number_input(
            (
                f"AI Buyer's Counter Offer — "
                f"Round {st.session_state.round_number} "
                f"of {max_rounds} (₹)"
            ),
            min_value=0.0,
            value=float(
                st.session_state.current_offer
                if st.session_state.current_offer
                else buyer_budget
            ),
            step=500.0
        )


        if st.button(
            "💬 Submit Buyer Offer",
            use_container_width=True
        ):

            result = negotiate_round(
                current_offer=st.session_state.current_offer,
                buyer_budget=buyer_counter,
                minimum_price=effective_minimum_price,
                product_cost=product_cost,
                buyer_intent=buyer_intent,
                inventory=inventory
            )


            if result["status"] == "ACCEPTED":

                final_price = result["offer"]


                close_deal(
                    final_price,
                    "Buyer and merchant reached a mutually acceptable price."
                )


            else:

                st.session_state.current_offer = (
                    result["offer"]
                )


                st.session_state.round_number += 1


            st.rerun()


        st.divider()

        st.header(
            "🤖 DealMind Autonomous Negotiation"
        )


        if st.button(
            "🚀 Run AI Negotiation",
            type="primary",
            use_container_width=True
        ):

            buyer = BuyerAgent(
                budget=buyer_budget,
                intent=buyer_intent
            )


            with st.spinner(
                "DealMind is calculating the optimal offer..."
            ):

                negotiation_result = (
                    buyer.recommend_merchant_offer(
                        buyer_message=buyer_message,
                        selling_price=selling_price,
                        product_cost=product_cost,
                        minimum_price=effective_minimum_price,
                        current_buyer_offer=buyer_budget,
                        strategy=negotiation_strategy
                    )
                )


            recommended_offer = float(
                negotiation_result.get(
                    "recommended_offer",
                    0
                )
            )


            decision = negotiation_result.get(
                "decision",
                "COUNTER"
            )


            reason = negotiation_result.get(
                "reason",
                "No explanation provided."
            )


            guardrail_passed = (

                recommended_offer
                >= effective_minimum_price

                and recommended_offer
                >= product_cost

                and recommended_offer
                <= selling_price

                and recommended_offer
                <= buyer_budget

            )


            if guardrail_passed:

                if decision == "ACCEPT":

                    close_deal(
                        recommended_offer,
                        "AI recommendation passed merchant safety constraints."
                    )


                else:

                    st.session_state.current_offer = (
                        recommended_offer
                    )

                    st.success(
                        f"Counter offer recommended: "
                        f"₹{recommended_offer:,.0f}"
                    )


            else:

                reject_deal(
                    "AI recommendation was blocked by merchant safety constraints."
                )


            st.rerun()


    negotiation_done = (
        st.session_state.deal_status
        in (
            "ACCEPTED",
            "REJECTED"
        )
    )


    render_nav_buttons(
        next_enabled=negotiation_done,
        next_label="Go to Payment →"
    )


# ============================================================
# PAGE 4 — PAYMENT
# ============================================================

elif st.session_state.wizard_page == 4:

    if st.session_state.deal_status == "ACCEPTED":

        st.header("🎉 Final Deal Summary")


        final_price = (
            st.session_state.final_price
        )


        final_profit = (
            final_price
            - product_cost
        )


        discount_amount = (
            selling_price
            - final_price
        )


        discount_percent = (
            discount_amount
            / selling_price
        ) * 100


        c1, c2, c3, c4 = st.columns(4)


        with c1:

            st.metric(
                "Final Deal Price",
                f"₹{final_price:,.0f}"
            )


        with c2:

            st.metric(
                "Merchant Profit",
                f"₹{final_profit:,.0f}"
            )


        with c3:

            st.metric(
                "Discount Given",
                f"{discount_percent:.1f}%"
            )


        with c4:

            st.metric(
                "Negotiation Rounds",
                st.session_state.round_number
            )


        st.divider()

        st.header("💳 Secure Payment")


        if (
            st.session_state.payment_status
            == "NOT_CREATED"
        ):

            if st.button(
                "💳 Create Razorpay Payment Order",
                type="primary",
                use_container_width=True
            ):

                receipt = (
                    f"dealmind_"
                    f"{uuid.uuid4().hex[:12]}"
                )


                with st.spinner(
                    "Creating secure payment order..."
                ):

                    payment_result = (
                        create_payment_order(
                            amount=final_price,
                            receipt=receipt
                        )
                    )


                if payment_result["success"]:

                    st.session_state.payment_order = (
                        payment_result
                    )

                    st.session_state.payment_status = (
                        "ORDER_CREATED"
                    )

                    st.rerun()


                else:

                    st.session_state.payment_status = (
                        "FAILED"
                    )

                    st.error(
                        payment_result["error"]
                    )


        elif (
            st.session_state.payment_status
            == "ORDER_CREATED"
        ):

            order = (
                st.session_state.payment_order
            )


            st.success(
                f"""
Payment order created successfully.

**Amount:** ₹{order['amount']:,.0f}

**Order ID:** `{order['order_id']}`
"""
            )


            show_razorpay_checkout(
                order_id=order["order_id"],
                amount=order["amount"],
                product_name=product_name
            )


            st.divider()

            st.subheader(
                "🔐 Payment Verification"
            )


            razorpay_payment_id = st.text_input(
                "Razorpay Payment ID"
            )


            razorpay_order_id = st.text_input(
                "Razorpay Order ID",
                value=order["order_id"]
            )


            razorpay_signature = st.text_input(
                "Razorpay Signature"
            )


            if st.button(
                "🔐 Verify Payment",
                type="primary",
                use_container_width=True
            ):

                if (
                    razorpay_payment_id
                    and razorpay_order_id
                    and razorpay_signature
                ):

                    verification_result = (
                        verify_payment_signature(
                            razorpay_order_id,
                            razorpay_payment_id,
                            razorpay_signature
                        )
                    )


                    if verification_result["success"]:

                        st.session_state.payment_status = (
                            "VERIFIED"
                        )

                        st.rerun()


                    else:

                        st.error(
                            "❌ Verification failed."
                        )


                else:

                    st.warning(
                        "Please enter all payment details."
                    )


        elif (
            st.session_state.payment_status
            == "VERIFIED"
        ):

            order = (
                st.session_state.payment_order
            )


            if (
                not st.session_state.success_voice_played
            ):

                speak_message(
                    "Payment successful. Your transaction "
                    "has been completed and verified successfully. "
                    "Thank you for choosing DealMind."
                )

                st.session_state.success_voice_played = True


            render_money_rain()


            st.success(
                f"""
🎉 Payment Verified Successfully!

Transaction Completed

Amount: ₹{order['amount']:,.0f}

🔒 Razorpay payment signature verified
🤝 Your DealMind transaction is complete
"""
            )


        elif (
            st.session_state.payment_status
            == "FAILED"
        ):

            if (
                not st.session_state.failure_voice_played
            ):

                speak_message(
                    "Sorry, your payment could not be completed. "
                    "Please check your payment details and try again."
                )

                st.session_state.failure_voice_played = True


            st.error(
                "🔴 Payment order creation failed. "
                "Please check your Razorpay configuration."
            )


    elif st.session_state.deal_status == "REJECTED":

        st.header("❌ Deal Summary")


        st.error(
            f"""
**Negotiation Failed**

**Reason:**

{st.session_state.final_reason}
"""
        )


    else:

        st.info(
            "Complete the negotiation on the previous step."
        )


    render_nav_buttons()


# ============================================================
# AI DOUBT CLARIFICATION CHATBOT
# ============================================================

def get_ai_answer(user_question):

    if not OPENROUTER_API_KEY:

        return (
            "⚠️ OpenRouter API key is missing. "
            "Please configure OPENROUTER_API_KEY."
        )


    try:

        client = OpenAI(
            base_url=(
                "https://openrouter.ai/api/v1"
            ),
            api_key=OPENROUTER_API_KEY
        )


        completion = (
            client.chat.completions.create(

                model="openrouter/free",

                messages=[

                    {
                        "role": "system",

                        "content": (
                            "You are DealMind AI Assistant. "
                            "You help users with DealMind, AI, "
                            "programming, negotiation, Razorpay, "
                            "payments and general questions."
                        )
                    },

                    {
                        "role": "user",
                        "content": user_question
                    }

                ]

            )
        )


        return (
            completion
            .choices[0]
            .message
            .content
        )


    except Exception as error:

        return (
            f"⚠️ AI Assistant error: {error}"
        )


# ============================================================
# AI CHAT INTERFACE
# ============================================================

st.divider()

st.markdown(
    "## 🤖 AI Doubt Clarification Assistant"
)


st.caption(
    "Ask any question about DealMind, AI, programming, "
    "negotiation, payments or any general doubt."
)


for message in st.session_state.ai_chat_history:

    with st.chat_message(message["role"]):

        st.write(
            message["content"]
        )


user_question = st.chat_input(
    "Ask your doubt here..."
)


if user_question:

    st.session_state.ai_chat_history.append(
        {
            "role": "user",
            "content": user_question
        }
    )


    with st.chat_message("user"):

        st.write(
            user_question
        )


    with st.chat_message("assistant"):

        with st.spinner(
            "🤖 DealMind AI is thinking..."
        ):

            ai_answer = get_ai_answer(
                user_question
            )

            st.write(
                ai_answer
            )


    st.session_state.ai_chat_history.append(
        {
            "role": "assistant",
            "content": ai_answer
        }
    )


if st.button("🗑️ Clear AI Chat"):

    st.session_state.ai_chat_history = []

    st.rerun()