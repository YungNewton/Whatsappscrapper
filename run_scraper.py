import time
import threading
import argparse
from datetime import datetime, timedelta
from WhatsAppScraper import WhatsAppScraper  # Import your scraper class
from TelegramPoster import TelegramPoster  # Import your TelegramPoster class

# Global Configuration
CHAT_NAMES = []  # Will be dynamically updated
CHANNEL_USERNAME = ""  # Will be dynamically updated
BOT_TOKEN = "7766870224:AAGwLCBlye9lPfxZeSWnJ9_Anji7LBmW_qs"  # Replace with your bot token

# Event and thread for managing scraper
stop_event = threading.Event()
scraper_thread = None  # Declare and initialize here globally


def parse_arguments():
    """
    Parse command-line arguments for chat names and channel username.
    """
    parser = argparse.ArgumentParser(description="Run WhatsApp Scraper.")
    parser.add_argument("--chatNames", required=True, help="Comma-separated list of chat names to scrape")
    parser.add_argument("--channelUsername", required=True, help="Telegram channel username for posting")

    args = parser.parse_args()

    # Update global configuration
    global CHAT_NAMES, CHANNEL_USERNAME
    CHAT_NAMES = args.chatNames.split(",")  # Convert comma-separated string to list
    CHANNEL_USERNAME = args.channelUsername


def scrape_last_10_minutes():
    """
    Runs the WhatsApp scraper to scrape messages from the last 10 minutes.
    """
    try:
        # Calculate the start and end time for scraping
        current_time = datetime.now()
        start_time = current_time - timedelta(minutes=5)
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
    while not stop_event.is_set():
        print(f"Starting scraper at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        scrape_last_10_minutes()
        print("Waiting to begin the next run...")
        if not stop_event.wait(300):  # Wait 10 minutes or exit if stopped
            continue


if __name__ == "__main__":
    # Parse arguments first
    parse_arguments()

    # Check if a scraper thread already exists and is running
    if scraper_thread is not None and scraper_thread.is_alive():
        print("Stopping existing scraper...")
        stop_event.set()  # Signal the thread to stop
        scraper_thread.join()  # Wait for the thread to finish

    # Clear the stop event and start a new thread
    stop_event.clear()
    scraper_thread = threading.Thread(target=run_scraper_periodically, daemon=True)
    scraper_thread.start()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping scraper manually...")
        stop_event.set()  # Signal the thread to stop
        if scraper_thread:
            scraper_thread.join()  # Ensure the thread has stopped
