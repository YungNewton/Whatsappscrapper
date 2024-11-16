import time
import threading
from datetime import datetime, timedelta
from flask import Flask
from WhatsAppScraper import WhatsAppScraper  # Import your scraper class
from TelegramPoster import TelegramPoster  # Import your TelegramPoster class
import os

# Configuration
CHAT_NAMES = ["Bobo and daughter's pi group😌.", "Duke Residency & Apartments", "Emmy"]  # Replace with your chat names
CHANNEL_USERNAME = "@newton_dev2"  # Replace with your Telegram channel username
BOT_TOKEN = "7766870224:AAGwLCBlye9lPfxZeSWnJ9_Anji7LBmW_qs"  # Replace with your bot token

app = Flask(__name__)  # Flask application

# Start the scraper in a separate thread
def start_scraper_thread():
    scraper_thread = threading.Thread(target=run_scraper_periodically, daemon=True)
    scraper_thread.start()

def scrape_last_10_minutes():
    """
    Runs the WhatsApp scraper to scrape messages from the last 10 minutes.
    """
    try:
        # Calculate the start and end time for scraping
        current_time = datetime.now()
        start_time = current_time - timedelta(minutes=10)
        time_start = start_time.strftime("%I:%M %p")  # Format: 12-hour time (e.g., "05:54 PM")
        time_end = current_time.strftime("%I:%M %p")

        print(f"Starting scrape for messages between {time_start} and {time_end}")

        # Initialize TelegramPoster
        telegram_poster = TelegramPoster(
            bot_token=BOT_TOKEN,
            channel_username=CHANNEL_USERNAME
        )
        print("TelegramPoster initialized")

        # Initialize WhatsAppScraper in headless mode
        scraper = WhatsAppScraper(
            chat_name=None,  # Chat name will be set dynamically
            date_limit=None,  # No date limit since we're scraping by time
            scrape_all=False,
            new_session=False,  # Use existing session
            cancel_event=None,
            telegram_poster=telegram_poster,
            headless=True  # Run in headless mode
        )

        scraper.login()

        # Scrape each chat
        for chat_name in CHAT_NAMES:
            print(f"Scraping chat: {chat_name}")
            try:
                scraper.chat_name = chat_name
                scraper.open_chat()
                scraper.scroll_to_target_date(time_start=time_start, time_end=time_end)  # Pass time range
                scraper.extract_messages_with_images(time_start, time_end)
                print(f"Scraping completed for chat: {chat_name}")
            except Exception as e:
                print(f"Error scraping chat '{chat_name}': {e}")

        scraper.close()
        print("Scraping completed for all chats.")

    except Exception as e:
        print(f"Error during scraping: {e}")

def run_scraper_periodically():
    """
    Runs the scraper every 10 minutes in a loop.
    """
    while True:
        print(f"Starting scraper at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        scrape_last_10_minutes()
        print("Waiting for the next run...")
        time.sleep(600)  # Wait 10 minutes (600 seconds) before running again

# Flask routes
@app.route("/")
def home():
    return "WhatsApp scraper is running!"

# Start the scraper thread before the app starts
start_scraper_thread()  # Ensure this runs immediately when the app starts

if __name__ == "__main__":
    # Get the port from the environment variable or default to 5000
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
