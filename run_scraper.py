import time
import threading
import argparse
from datetime import datetime, timedelta
from WhatsAppScraper import WhatsAppScraper  # Import your scraper class
from TelegramPoster import TelegramPoster  # Import your TelegramPoster class
import re

# Global Configuration
CHAT_NAMES = []  # Will be dynamically updated
CHANNEL_USERNAME = ""  # Will be dynamically updated
BOT_TOKEN = "8027226040:AAHwIVqA-bB-F7g01djdw93Ti4SuSk-mM4o"  # Replace with your bot token

# Event and thread for managing scraper
stop_event = threading.Event()
scraper_thread = None  # Declare and initialize here globally

# Global variable to track the last end time
last_end_time = None

def parse_arguments():
    """
    Parse command-line arguments for user_id, chat names, and channel username.
    """
    parser = argparse.ArgumentParser(description="Run WhatsApp Scraper.")
    parser.add_argument("--userId", required=True, help="Unique user ID")
    parser.add_argument("--userEmail", required=True, help="Email of the user for notifications")
    parser.add_argument("--groupMappings", required=True, help="Groups and channels in the format '(Group1, Group2), Group3 : channel1, channel2'")
    
    args = parser.parse_args()

    # Update global configuration
    global USER_ID, USER_EMAIL, GROUP_CHANNEL_MAPPING
    USER_ID = args.userId
    USER_EMAIL = args.userEmail
    GROUP_CHANNEL_MAPPING = parse_group_mappings(args.groupMappings)  # Parse mappings


def parse_group_mappings(mappings_str):
    """
    Parses the group-channel mapping string and returns a dictionary mapping channels to groups.
    Example input: '{Group1, Group2}, {Group3, Group4} : channel1, channel2'

    Args:
        mappings_str (str): The input string containing groups and channels.

    Returns:
        dict: A dictionary where keys are channels, and values are lists of groups.
    """
    # Split the string into groups and channels part
    try:
        groups_part, channels_part = mappings_str.split(":")
    except ValueError:
        raise ValueError("Invalid format. Use '{Group1, Group2}, {Group3} : channel1, channel2'")
    
    # Extract groups within curly braces
    group_pattern = re.compile(r"\{([^}]+)\}")
    groups = []
    for match in group_pattern.findall(groups_part):
        # Split groups within each set by commas
        group_list = [g.strip() for g in match.split(",")]
        groups.append(group_list)
    
    # Extract channels
    channels = [c.strip() for c in channels_part.split(",") if c.strip()]

    # Map groups to channels
    mapping = {}
    for i, group in enumerate(groups):
        if i < len(channels):  # Map group to a channel
            mapping[channels[i]] = group
        else:
            print(f"Group {group} has no associated channel and will be ignored.")
    
    return mapping


def scrape_last_10_minutes():
    """
    Runs the WhatsApp scraper to scrape messages from the last 10 minutes for all mapped channels and groups.
    """
    global last_end_time

    # Initialize last_end_time if not already set
    if last_end_time is None:
        last_end_time = datetime.now() - timedelta(minutes=15)

    # Calculate start and end times for the scraping session
    start_time = last_end_time + timedelta(minutes=1)
    end_time = last_end_time + timedelta(minutes=15)

    # Format times for scraping
    time_start = start_time.strftime("%I:%M %p")
    time_end = end_time.strftime("%I:%M %p")

    print(f"Starting scrape for messages between {time_start} and {time_end}")

    # Update last_end_time to the new end_time
    last_end_time = end_time

    for channel, groups in GROUP_CHANNEL_MAPPING.items():
        print(f"Processing groups {groups} for channel {channel}")

        telegram_poster = TelegramPoster(bot_token=BOT_TOKEN, channel_username=channel)

        scraper = WhatsAppScraper(
            user_id=USER_ID,
            user_email=USER_EMAIL,
            chat_names=groups,
            telegram_poster=telegram_poster,
            headless=True
        )

        try:
            scraper.login()
            scraper.scrape_chats(time_start, time_end)  # Process all chats
        except Exception as e:
            print(f"Error processing channel {channel}: {e}")
        finally:
            scraper.close()


def run_scraper_periodically():
    """
    Runs the scraper periodically based on last_end_time + 1 minute.
    """
    global last_end_time

    while not stop_event.is_set():
        if last_end_time is None:
            # Initialize the last_end_time if it's the first run
            last_end_time = datetime.now() - timedelta(minutes=15)

        # Calculate the time to wait until the next scrape
        next_start_time = last_end_time + timedelta(minutes=1)
        current_time = datetime.now()

        # Wait only if the current time is earlier than the next start time
        wait_time = (next_start_time - current_time).total_seconds()
        if wait_time > 0:
            print(f"Waiting {wait_time:.2f} seconds until the next scrape...")
            if stop_event.wait(wait_time):
                break  # Exit if stop_event is set

        print(f"Starting scraper at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        scrape_last_10_minutes()


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