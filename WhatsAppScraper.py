import os
import time
from io import BytesIO
import shutil
import tempfile
import requests
import base64
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from datetime import datetime, timedelta
from time import sleep
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import calendar
import threading
import re
import yagmail

# Email configuration
YAGMAIL_USER = "your_email@example.com"
YAGMAIL_PASSWORD = "your_app_specific_password"
NOTIFICATION_RECIPIENTS = ["coursechief5@gmail.com", "isaacnewtonahanmisi@gmail.com"]

def send_session_invalid_email():
    """
    Sends an email notification when the WhatsApp session is no longer valid.
    """
    try:
        yag = yagmail.SMTP(YAGMAIL_USER, YAGMAIL_PASSWORD)
        subject = "WhatsApp Session Invalid"
        body = (
            "The WhatsApp session used by the scraper is no longer valid. "
            "Please log in again to continue scraping. "
            "If this was unexpected, please ensure your session has not been terminated by another device."
        )
        yag.send(to=NOTIFICATION_RECIPIENTS, subject=subject, contents=body)
        print("Session invalid email sent successfully.")
    except Exception as e:
        print(f"Failed to send session invalid email: {e}")

class WhatsAppScraper:
    def __init__(self, chat_name, date_limit=None, scrape_all=False, new_session=False, cancel_event=None, telegram_poster=None, headless=True):
        self.chat_name = chat_name
        self.date_limit = date_limit
        self.scrape_all = scrape_all
        self.original_user_data_dir = os.path.join(os.getcwd(), "chrome_user_data")
        self.user_data_dir = tempfile.mkdtemp()
        self.cancel_event = cancel_event or threading.Event()
        self.telegram_poster = telegram_poster
        self.headless = headless
        self.setup_symlinks()
        self.driver = self.init_driver()

    def init_driver(self):
        """
        Initialize the WebDriver with the temporary user data directory.
        """
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={self.user_data_dir}")
        chrome_options.add_argument("--disable-webrtc")
        chrome_options.add_argument("--disable-media-stream")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")

        if self.headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1280,720")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        return driver

    def setup_symlinks(self):
        """
        Create symlinks for files and directories in the original user data directory.
        """
        try:
            if os.path.exists(self.original_user_data_dir):
                for item in os.listdir(self.original_user_data_dir):
                    src = os.path.join(self.original_user_data_dir, item)
                    dest = os.path.join(self.user_data_dir, item)
                    # Symlink instead of copying
                    if not os.path.exists(dest):
                        os.symlink(src, dest)
                print(f"Symlinks created for user data in: {self.user_data_dir}")
            else:
                print(f"Original user data directory not found: {self.original_user_data_dir}")
        except Exception as e:
            print(f"Error setting up symlinks: {e}")

    def login(self):
        if self.cancel_event.is_set():
            return
        self.driver.get("https://web.whatsapp.com")
        time.sleep(2)
        if not self.is_session_valid():
            print("Session invalid. Please log in manually.")
            self.wait_for_login()

    def is_session_valid(self):
        """
        Checks if the WhatsApp session is still valid.
        If not, sends an email notification.
        """
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//span[@data-icon="chats-filled"]'))
            )
            return True
        except:
            print("WhatsApp session is no longer valid.")
            send_session_invalid_email()  # Trigger email notification
            return False

    def wait_for_login(self):
        WebDriverWait(self.driver, 600).until(
            EC.presence_of_element_located((By.XPATH, '//span[@data-icon="chats-filled"]'))
        )
        print("Login detected successfully.")

    def open_chat(self):
        if self.cancel_event.is_set():
            return

        pane_side = self.driver.find_element(By.ID, 'pane-side')

        def escape_xpath_string(s):
            if "'" in s and '"' in s:
                return "concat(" + ", ".join(f"'{part}'" for part in s.split("'")) + ")"
            if "'" in s:
                return f'"{s}"'
            return f"'{s}'"

        chat_list_xpath = f"//span[@title={escape_xpath_string(self.chat_name)}]"
        
        try:
            # Check if the chat is already visible before scrolling
            chat = pane_side.find_element(By.XPATH, chat_list_xpath)
            ActionChains(self.driver).move_to_element(chat).perform()
            print(f"Chat '{self.chat_name}' is already visible. Clicking on it.")
            chat.click()
            return
        except NoSuchElementException:
            print(f"Chat '{self.chat_name}' is not immediately visible. Scrolling to find it...")

        while True:
            try:
                chat = pane_side.find_element(By.XPATH, chat_list_xpath)
                ActionChains(self.driver).move_to_element(chat).perform()
                print(f"Chat '{self.chat_name}' is now visible. Clicking on it.")
                chat.click()
                return
            except NoSuchElementException:
                print(f"Chat '{self.chat_name}' not immediately visible. Scrolling to find it...")
                self.driver.execute_script("arguments[0].scrollTop += 200", pane_side)
                time.sleep(2)  # Allow time for chats to load

                # Check if we've reached the bottom of the chat list
                last_scroll_position = self.driver.execute_script("return arguments[0].scrollTop", pane_side)
                self.driver.execute_script("arguments[0].scrollTop += 200", pane_side)
                new_scroll_position = self.driver.execute_script("return arguments[0].scrollTop", pane_side)
                if last_scroll_position == new_scroll_position:
                    raise Exception(f"Chat '{self.chat_name}' not found.")

    def scroll_to_target_date(self, target_date=None, time_start=None, time_end=None):
        """
        Scrolls up to the specified target date. If target_date is None, scrolls to the very top of the chat.
        Recognizes "TODAY" as the current date and handles day names within the current week.
        Stops scrolling when the message's timestamp or date is within the provided range.
        """
        try:
            if target_date:
                target_date = datetime.strptime(target_date, "%m/%d/%Y")
            time_start_dt = datetime.strptime(time_start, "%I:%M %p") if time_start else None
            time_end_dt = datetime.strptime(time_end, "%I:%M %p") if time_end else None

            message_container = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "_amjv")]'))
            )
            previous_height = None

            while True:
                # Check for "load older messages" button and click it
                try:
                    load_more_button = self.driver.find_element(By.XPATH, '//button[contains(@class, "x14m1o6m x126m2zf x1b9z3ur x9f619 x1rg5ohu x1okw0bk x193iq5w x123j3cw xn6708d x10b6aqq x1ye3gou x13a8xbf xdod15v x2b8uid x1lq5wgf xgqcy7u x30kzoy x9jhf4c")]')
                    load_more_button.click()
                    print("Clicked to load older messages.")
                    time.sleep(2)
                except NoSuchElementException:
                    pass

                # Send multiple Page Up keystrokes to scroll continuously
                for _ in range(12):
                    message_container.send_keys(Keys.PAGE_UP)
                    time.sleep(1)

                # Process messages to find the earliest visible message
                date_elements = self.driver.find_elements(By.XPATH, '//div[@class="_amk4 _amkb"]/span[@class="_ao3e"]')
                for date_element in date_elements:
                    try:
                        date_text = date_element.text
                        message_date = self.parse_date_text(date_text)

                        if message_date:
                            # Stop scrolling if we've reached the target date
                            if target_date and message_date < target_date:
                                print("Reached messages older than the target date.")
                                return

                    except ValueError:
                        print("Error parsing date:", date_element.text)

                # Check for time filtering
                # Process image messages
                image_messages = self.driver.find_elements(
                    By.XPATH,
                    '//div[contains(@class, "message-in") or contains(@class, "message-out")]'
                    '//div[contains(@role, "button") and contains(@aria-label, "Open picture")]'
                    '/ancestor::div[contains(@class, "message-in") or contains(@class, "message-out")]'
                )
                for message in image_messages:
                    try:
                        # Retrieve timestamp for image messages only
                        try:
                            timestamp_element = message.find_element(By.XPATH, './/div[contains(@class, "copyable-text")]')
                            raw_timestamp_text = timestamp_element.get_attribute("data-pre-plain-text").rstrip("]").strip()
                        except NoSuchElementException:
                            raw_timestamp_text = "" 
                        time_text = raw_timestamp_text.split(",")[0].strip()
                        time_text = time_text.lstrip("[").strip()
                        time_text = "".join(time_text.split())  # Remove all whitespace characters (including invisible ones)

                        # Skip processing if time_text is empty
                        if not time_text:
                            continue

                        # Parse time_text into a datetime object with today's date
                        try:
                            parsed_time = datetime.strptime(time_text, "%I:%M%p").time()
                            message_time = datetime.combine(datetime.today(), parsed_time)  # Attach today's date
                        except ValueError as ve:
                            print(f"ValueError: Could not parse timestamp. Cleaned: '{time_text}'. Exception: {ve}")
                            continue

                        # Stop scrolling if the message is outside the time range
                        if time_start_dt and message_time < time_start_dt:
                            print(f"Reached image message older than the start time: {time_start_dt.strftime('%I:%M %p')}.")
                            return
                        if time_end_dt and message_time > time_end_dt:
                            print(f"Reached image message newer than the end time: {time_end_dt.strftime('%I:%M %p')}.")
                            return

                    except (ValueError, AttributeError, NoSuchElementException):
                        print(f"Error parsing timestamp for image message, skipping.")

                # Check if we've reached the top by comparing heights
                current_height = self.driver.execute_script("return arguments[0].scrollHeight;", message_container)
                if previous_height == current_height:
                    print("Reached the top of the chat.")
                    break
                previous_height = current_height

        except Exception as e:
            print(f"Error during scrolling: {e}")

    def parse_date_text(self, date_text):
        """
        Parses a date from text that may say "TODAY," "YESTERDAY," a weekday name, or an actual date.
        Returns a datetime object or None if the date cannot be parsed.
        """
        today = datetime.today()

        if date_text == "TODAY":
            return today
        elif date_text == "YESTERDAY":
            return today - timedelta(days=1)
        elif date_text in calendar.day_name:
            weekday_index = list(calendar.day_name).index(date_text)
            days_difference = weekday_index - today.weekday()
            if days_difference > 0:
                days_difference -= 7
            return today + timedelta(days=days_difference)
        else:
            try:
                return datetime.strptime(date_text, "%m/%d/%Y")
            except ValueError:
                return None

    def extract_messages_with_images(self, time_start=None, time_end=None):

        time_start_dt = datetime.strptime(time_start, "%I:%M %p") if time_start else None
        time_end_dt = datetime.strptime(time_end, "%I:%M %p") if time_end else None

        # Create a temporary directory to store images
        with tempfile.TemporaryDirectory() as temp_dir:
            messages_with_images = self.driver.find_elements(
                By.XPATH, 
                '//div[contains(@class, "message-in") or contains(@class, "message-out")]'
                '//div[contains(@role, "button") and contains(@aria-label, "Open picture")]'
                '/ancestor::div[contains(@class, "message-in") or contains(@class, "message-out")]'
            )

            # Collect processed data for all messages
            processed_messages = []

            for idx, message in enumerate(reversed(messages_with_images)):
                try:
                    # Retrieve the timestamp
                    try:
                        timestamp_element = message.find_element(By.XPATH, './/div[contains(@class, "copyable-text")]').get_attribute("data-pre-plain-text").rstrip("]").strip()
                        timestamp_text = timestamp_element.split(",")[0].strip()  # Extract "5:54 PM"
                        timestamp_text = timestamp_text.lstrip("[").strip()
                        message_time = datetime.strptime(timestamp_text, "%I:%M %p")  # Convert to datetime object
                    except NoSuchElementException:
                        timestamp_element = " "
                        message_time = None

                    if message_time:
                        if time_start_dt and message_time < time_start_dt:
                            print(f"Message {idx + 1} stopped: Time {message_time.strftime('%I:%M %p')} is before the start range.")
                            break  # Stop processing entirely when the message is too old
                        if time_end_dt and message_time > time_end_dt:
                            print(f"Message {idx + 1} stopped: Time {message_time.strftime('%I:%M %p')} exceeds the end range.")
                            break

                    # Retrieve the image description
                    description_element = message.find_elements(By.XPATH, './/img[@alt]')
                    description = (
                        description_element[0].get_attribute("alt")
                        if description_element else " "
                    )

                    # Locate image elements and check for blob or base64
                    image_elements = message.find_elements(By.XPATH, './/img')
                    blob_image = next((img for img in image_elements if img.get_attribute("src").startswith("blob:")), None)
                    base64_image = next((img for img in image_elements if img.get_attribute("src").startswith("data:image")), None)

                    if blob_image:
                        # Handle blob URLs using JavaScript injection
                        blob_url = blob_image.get_attribute("src")
                        script = """
                            let blobUrl = arguments[0];
                            return fetch(blobUrl)
                                .then(response => response.blob())
                                .then(blob => new Promise((resolve, reject) => {
                                    let reader = new FileReader();
                                    reader.onloadend = () => resolve(reader.result);
                                    reader.onerror = reject;
                                    reader.readAsDataURL(blob);
                                }));
                        """
                        base64_data = self.driver.execute_script(script, blob_url)

                        # Decode and save the blob data
                        if base64_data.startswith("data:image"):
                            base64_content = base64_data.split(",")[1]
                            temp_file_path = os.path.join(temp_dir, f"extracted_image_{idx + 1}.png")
                            with open(temp_file_path, "wb") as file:
                                file.write(base64.b64decode(base64_content))
                            print(f"Blob image {idx + 1} saved to {temp_file_path}.")
                        else:
                            print(f"Unable to process blob image {idx + 1}, skipping.")
                            continue

                    elif base64_image:
                        # Handle Base64-encoded image directly
                        image_src = base64_image.get_attribute("src")
                        base64_data = image_src.split(",")[1]
                        temp_file_path = os.path.join(temp_dir, f"extracted_image_{idx + 1}.png")
                        with open(temp_file_path, "wb") as file:
                            file.write(base64.b64decode(base64_data))
                        print(f"Base64 image {idx + 1} saved to {temp_file_path}.")

                    else:
                        print(f"No valid image found for message {idx + 1}, skipping.")
                        continue


                    processed_messages.append({
                        "file_path": temp_file_path,
                        "caption": f"{timestamp_element} - {description}"
                    })

                except Exception as e:
                    print(f"Error processing message with image: {e}")

            print(f"Finished extracting {len(messages_with_images)} messages with images.")
            # Reverse and post processed messages
            for idx, message_data in enumerate(reversed(processed_messages)):
                try:
                    file_path = message_data["file_path"]
                    caption = message_data["caption"]
                    print(f"Posting message {idx + 1} to Telegram with caption: {caption}")
                    self.telegram_poster.post_image(file_path, caption)
                except Exception as e:
                    print(f"Error posting message {idx + 1}: {e}")


    def extract_messages_with_videos(self, time_start=None, time_end=None):
        """
        Extracts a fixed thumbnail image, descriptions, and timestamps from video messages
        and posts them to Telegram if enabled, using a temporary directory for storage.
        """

        time_start_dt = datetime.strptime(time_start, "%I:%M %p") if time_start else None
        time_end_dt = datetime.strptime(time_end, "%I:%M %p") if time_end else None

        # Fixed thumbnail URL (Replace this with any generic thumbnail URL or dynamic fetching logic if required)
        fixed_thumbnail_url = "https://cdn.dribbble.com/userupload/10666002/file/original-010e2a5e01e574df4d8894d857aba26b.png?resize=752x"

        # Locate all video messages
        video_messages = self.driver.find_elements(
            By.XPATH,
            '//div[contains(@class, "message-in") or contains(@class, "message-out")]'
            '[.//span[@data-icon="msg-video" and not(ancestor::div[contains(@class, "text")])]]'
        )


        print(f"Found {len(video_messages)} video messages.")

        # Use a temporary directory for storing thumbnails
        with tempfile.TemporaryDirectory() as temp_dir:
            for idx, message in enumerate(reversed(video_messages)):
                try:
                    # Bring the message into view
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", message)

                    # Retrieve the timestamp
                    timestamp_element = message.find_element(By.XPATH, './/div[contains(@class, "copyable-text")]').get_attribute("data-pre-plain-text").rstrip("]").strip()
                    timestamp_text = timestamp_element.split(",")[0].strip()  # Extract "5:54 PM"
                    timestamp_text = timestamp_text.lstrip("[").strip()
                    message_time = datetime.strptime(timestamp_text, "%I:%M %p")  # Convert to datetime object
                    timestamp = timestamp_element if timestamp_element else " "

                    if message_time:
                        if time_start_dt and message_time < time_start_dt:
                            print(f"Message {idx + 1} stopped: Time {message_time.strftime('%I:%M %p')} is before the start range.")
                            break  # Stop processing entirely when the message is too old
                        if time_end_dt and message_time > time_end_dt:
                            print(f"Message {idx + 1} stopped: Time {message_time.strftime('%I:%M %p')} exceeds the end range.")
                            break

                    # Extract description (if available)
                    description_element = message.find_elements(By.XPATH, './/span[@class="_ao3e selectable-text copyable-text"]/span')
                    description = description_element[0].text if description_element else " "

                    # Use the fixed thumbnail
                    save_path = os.path.join(temp_dir, f"video_thumbnail_{idx + 1}.png")
                    response = requests.get(fixed_thumbnail_url)
                    if response.status_code == 200:
                        with open(save_path, "wb") as file:
                            file.write(response.content)
                        print(f"Saved fixed thumbnail for video message {idx + 1} to temporary directory.")
                    else:
                        print(f"Failed to download fixed thumbnail for video message {idx + 1}.")
                        continue  # Skip posting if thumbnail couldn't be downloaded

                    # Post the video thumbnail to Telegram
                    if self.telegram_poster:
                        caption = f"Timestamp: {timestamp}\nDescription: {description}"
                        print(f"Posting video thumbnail {idx + 1} to Telegram with caption: {caption}")
                        self.telegram_poster.post_image(save_path, caption)

                    # Print extracted details
                    print(f"Video Message {idx + 1}:\nTimestamp: {timestamp}\nDescription: {description}\n")

                except Exception as e:
                    print(f"Error processing video message {idx + 1}: {e}")

            print(f"Finished processing {len(video_messages)} video messages.")

    def close(self):
        """
        Clean up the WebDriver and the temporary user data directory.
        """
        try:
            if self.driver:
                self.driver.quit()
            if os.path.exists(self.user_data_dir):
                shutil.rmtree(self.user_data_dir, ignore_errors=True)
                print(f"Temporary user data directory deleted: {self.user_data_dir}")
        except Exception as e:
            print(f"Error during cleanup: {e}")

# Usage example
if __name__ == "__main__":
    scraper = WhatsAppScraper(chat_name="Paul", date_limit="11/01/2024", scrape_all=False, new_session=True)
    scraper.login()
    # scraper.open_chat()
    # scraper.scroll_to_target_date()
    # scraper.extract_messages_with_images()
    # scraper.extract_messages_with_videos()
    scraper.close()
