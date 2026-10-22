import os
import sys
import requests
from anthropic import Anthropic, APIError

# Retrieve keys safely from GitHub Secrets
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not ANTHROPIC_API_KEY:
    print("❌ ERROR: ANTHROPIC_API_KEY secret is missing or empty.")
    sys.exit(1)

# Target ski destinations with coordinates
DESTINATIONS = {
    "Högbo Bruk / Sandviken": {"lat": 60.62, "lon": 16.78, "airbnb_loc": "Hogbo-Bruk--Sweden"},
    "Hemlingby / Gävle": {"lat": 60.65, "lon": 17.16, "airbnb_loc": "Gavle--Sweden"},
    "Lugnet / Falun": {"lat": 60.61, "lon": 15.65, "airbnb_loc": "Falun--Sweden"},
    "Harsa / Järvsö": {"lat": 61.58, "lon": 16.14, "airbnb_loc": "Jarvso--Sweden"},
    "Säfsen / Fredriksberg": {"lat": 60.14, "lon": 14.42, "airbnb_loc": "Safsen--Sweden"}
}

def fetch_weather_for_destinations():
    """Fetch 7-day weather forecast for all tracked skiing spots"""
    weather_summary = {}
    for name, coords in DESTINATIONS.items():
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={coords['lat']}&longitude={coords['lon']}"
            f"&daily=snowfall_sum,temperature_2m_min,temperature_2m_max,precipitation_sum"
            f"&timezone=Europe%2FStockholm"
        )
        response = requests.get(url)
        response.raise_for_status()
        weather_summary[name] = response.json()
    return weather_summary

def evaluate_with_claude(weather_data):
    """Pass weather data to Claude to select the best spot and draft a family pitch"""
    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        
        prompt = f"""
        You are a cross-country skiing concierge and family trip strategist.
        Analyze this 7-day weather forecast for multiple Swedish skiing spots:
        {weather_data}

        Task:
        1. Evaluate conditions across all spots:
           - Look for fresh snowfall (>5-10cm) OR sustained sub-zero temperatures to preserve snow.
           - Ensure temperatures remain freezing (sub-zero) to prevent slush.
        
        2. Select the single BEST destination for an upcoming long weekend trip (Friday to Monday).

        3. Response Format:
           If NO spot has good cross-country conditions, respond starting ONLY with 'NO_TRIP'.

           If a spot IS recommended, format the response in clean Telegram Markdown with two distinct parts:
           
           PART 1: ⛷️ *TECH & SKI REPORT FOR YOU*
           - Best Location Name
           - Recommended Dates (Friday-Monday)
           - Weather Summary (Snowfall, temps, stability)
           - Skiing condition rating (e.g., 8/10)

           PART 2: 💬 *THE PITCH FOR CAROLINE (Ready to copy & paste)*
           - A warm, fun, and persuasive message highlighting family benefits (cozy cabin vibes, outdoor snow play for kids, hot drinks, good weather window).
        """

        response = client.messages.create(
            model="claude-haiku-5-5",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except APIError as e:
        print(f"❌ Anthropic API Error: {e}")
        sys.exit(1)

def send_telegram_notification(message):
    """Send notification directly to phone via Telegram API"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram credentials missing or unconfigured. Printing output:")
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
    print("Fetching weather for all target skiing spots...")
    weather_data = fetch_weather_for_destinations()
    
    print("Evaluating top spot with Claude...")
    claude_analysis = evaluate_with_claude(weather_data)

    if not claude_analysis.startswith("NO_TRIP"):
        airbnb_url = "https://www.airbnb.com/s/Sweden/homes"
        full_message = f"{claude_analysis}\n\n🏡 *Browse Accommodations:*\n{airbnb_url}"
        send_telegram_notification(full_message)
    else:
        print("✅ Finished: No trip recommended based on current forecasts.")

if __name__ == "__main__":
    main()
