import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    print("❌ OPENROUTER_API_KEY not found.")
    print("Check your .env file.")
    exit()

print("✅ OpenRouter API key found.")
print("🔄 Connecting to OpenRouter...")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)

try:
    response = client.chat.completions.create(
        model="openrouter/free",
        messages=[
            {
                "role": "user",
                "content": (
                    "You are testing an AI system. "
                    "Reply exactly with: "
                    "OpenRouter LLM connection successful"
                )
            }
        ]
    )

    answer = response.choices[0].message.content

    print("\n🤖 LLM Response:")
    print(answer)

    print("\n✅ REAL LLM TEST SUCCESSFUL!")

except Exception as e:

    print("\n❌ OpenRouter Error:")
    print(e)