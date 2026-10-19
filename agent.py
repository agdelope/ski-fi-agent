import os
import requests
from anthropic import Anthropic

# Retrieve keys safely from environment variables (GitHub Secrets)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def fetch_weather():
    """Fetch 7-day forecast for Sandviken / Högbo Bruk via Open-Meteo"""
    url = "https://api.open-meteo.com/v1/forecast?latitude=60.62&longitude=16.78&daily=snowfall_sum,temperature_2m_min,temperature_2m_max&timezone=Europe%2FStockholm"
    response = requests.get(url)
    return response.json()

def evaluate_with_claude(weather_data):
    """Pass weather data to Claude to evaluate skiing conditions"""
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

def send_telegram_notification(message):
    """Send notification directly to your phone via Telegram API"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

def main():
    weather_data = fetch_weather()
    claude_analysis = evaluate_with_claude(weather_data)

    if not claude_analysis.startswith("NO_TRIP"):
        # Construct search link for Sandviken/Högbo area
        airbnb_url = "https://www.airbnb.com/s/Hogbo-Bruk--Sweden/homes"
        full_message = f"{claude_analysis}\n\n🏡 *Browse Accommodation:*\n{airbnb_url}"
        send_telegram_notification(full_message)
    else:
        print("No trip recommended based on current forecast.")

if __name__ == "__main__":
    main()
