import os
import sys
import requests
from anthropic import Anthropic, APIError

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Check if environment variables are loaded
if not ANTHROPIC_API_KEY:
    print("❌ ERROR: ANTHROPIC_API_KEY secret is missing or empty.")
    sys.exit(1)

def fetch_weather():
    """Fetch 7-day forecast for Sandviken / Högbo Bruk via Open-Meteo"""
    url = "https://api.open-meteo.com/v1/forecast?latitude=60.62&longitude=16.78&daily=snowfall_sum,temperature_2m_min,temperature_2m_max&timezone=Europe%2FStockholm"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def evaluate_with_claude(weather_data):
    """Pass weather data to Claude to evaluate skiing conditions"""
    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        
        prompt = f"""
        You are a cross-country skiing concierge.
        Analyze this weather forecast data for the Sandviken/Gävle region:
        {weather_data}

        Determine if an upcoming weekend will have good cross-country skiing conditions.
        Criteria:
        - Significant snowfall or sustained freezing temperatures.
        - Cold sub-zero temperatures to keep tracks stable.

        If conditions are favorable, specify the recommended check-in (Friday) and check-out (Monday) dates.
        Format your response cleanly for a Telegram message using Markdown.
        If conditions are poor, start your response with 'NO_TRIP'.
        """

        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except APIError as e:
        print(f"❌ Anthropic API Error: {e}")
        sys.exit(1)

def send_telegram_notification(message):
    """Send notification directly to your phone via Telegram API"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram credentials missing. Printing output instead:")
        print(message)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    res = requests.post(url, json=payload)
    if res.status_code != 200:
        print(f"⚠️ Telegram send failed: {res.text}")

def main():
    print("Fetching weather data...")
    weather_data = fetch_weather()
    print("Evaluating conditions with Claude...")
    claude_analysis = evaluate_with_claude(weather_data)

    if not claude_analysis.startswith("NO_TRIP"):
        airbnb_url = "https://www.airbnb.com/s/Hogbo-Bruk--Sweden/homes"
        full_message = f"{claude_analysis}\n\n🏡 *Browse Accommodation:*\n{airbnb_url}"
        send_telegram_notification(full_message)
    else:
        print("✅ Success: No trip recommended based on current forecast.")

if __name__ == "__main__":
    main()
