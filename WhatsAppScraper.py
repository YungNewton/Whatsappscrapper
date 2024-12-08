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
from selenium.common.exceptions import StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc
import calendar
import threading
import re
import yagmail

# Email configuration
YAGMAIL_USER = "isaacnewtonahanmisi@gmail.com"
YAGMAIL_PASSWORD = "muid bjaw knqe adig"
NOTIFICATION_RECIPIENTS = ["isaacnewtonahanmisi@gmail.com", "coursechief5@gmail.com"]

def send_session_invalid_email(user_email):
    """
    Sends an email notification to the specific user when the WhatsApp session is no longer valid.
    """
    try:
        yag = yagmail.SMTP(YAGMAIL_USER, YAGMAIL_PASSWORD)
        subject = "WhatsApp Session Invalid"
        body = (
            "The WhatsApp session used by the scraper is no longer valid. "
            "Please log in again to continue scraping. "
            "If this was unexpected, please ensure your session has not been terminated by another device."
        )
        yag.send(to=user_email, subject=subject, contents=body)
        print(f"Session invalid email sent successfully to {user_email}.")
    except Exception as e:
        print(f"Failed to send session invalid email to {user_email}: {e}")

class WhatsAppScraper:
    def __init__(self, user_id, user_email, chat_names, date_limit=None, scrape_all=False, new_session=False, cancel_event=None, telegram_poster=None, headless=True):
        self.user_id = user_id  # Unique identifier for the user
        self.user_email = user_email  # User's email address for notifications
        self.chat_names = chat_names  # List of chat names
        self.date_limit = date_limit
        self.scrape_all = scrape_all
        self.original_user_data_dir = os.path.join(os.getcwd(), "chrome_user_data", f"user_{self.user_id}")
        self.user_data_dir = tempfile.mkdtemp()
        self.cancel_event = cancel_event or threading.Event()
        self.telegram_poster = telegram_poster
        self.headless = headless
        self.delete_preferences_file()
        self.setup_symlinks()
        self.driver = self.init_driver()

    def init_driver(self):
        """
        Initialize the WebDriver with the temporary user data directory.
        """
        options = uc.ChromeOptions()
        options.add_argument(f"--user-data-dir={self.user_data_dir}")
        options.add_argument("--disable-webrtc")
        options.add_argument("--disable-media-stream")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--start-maximized")
        options.add_argument("--window-size=1280,720")
        options.add_argument("--disable-web-security")  # Disable CORS restrictions
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-blink-features=AutomationControlled")  # Bypass detection
        options.add_argument("--disable-gpu")

        driver = uc.Chrome(options=options)
        driver.set_window_size(1280, 720)
        return driver

    def clear_tmp_directory(self):
        tmp_dir = "/tmp"
        try:
            # Iterate through all items in /tmp
            for item in os.listdir(tmp_dir):
                item_path = os.path.join(tmp_dir, item)
                # Remove directories and files
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path, ignore_errors=True)
                else:
                    os.remove(item_path)
            print(f"Cleared all contents of {tmp_dir}.")
        except Exception as e:
            print(f"Failed to clear {tmp_dir}: {e}")

    def delete_preferences_file(self):
        """
        Deletes the Preferences file if it exists in the Chrome user data directory.
        """
        preferences_path = os.path.join(self.original_user_data_dir, "Default", "Preferences")
        try:
            if os.path.exists(preferences_path):
                os.remove(preferences_path)
                print(f"Deleted Preferences file at: {preferences_path}")
            else:
                print(f"No Preferences file found at: {preferences_path}")
        except Exception as e:
            print(f"Error deleting Preferences file: {e}")

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

    def refresh_element(self, driver, locator):
        """
        Refreshes a WebDriver element reference by re-locating it.
        Args:
            driver: The WebDriver instance.
            locator: The locator tuple (By, value) for the element.
        Returns:
            A fresh WebDriver element.
        """
        try:
            return driver.find_element(*locator)
        except StaleElementReferenceException:
            print("Element went stale. Re-locating...")
            return WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(locator)
        )

    def login(self):
        if self.cancel_event.is_set():
            return
        self.driver.get("https://web.whatsapp.com")
        time.sleep(5)
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
            send_session_invalid_email(self.user_email)  # Trigger email notification
            return False

    def wait_for_login(self):
        WebDriverWait(self.driver, 600).until(
            EC.presence_of_element_located((By.XPATH, '//span[@data-icon="chats-filled"]'))
        )
        print("Login detected successfully.")

    def scrape_chats(self, time_start, time_end):
        """
        Scrapes messages for all chats in `self.chat_names`, prioritizing archived chats first,
        then normal chats for those not found in archived.
        """
        try:
            processed_chats = set()
            chats_not_found = set(self.chat_names)  # Track chats that are not found

            # Step 1: Scrape Archived Chats
            print("Scraping archived chats...")
            try:
                archived_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="Archived "]'))
                )
                archived_button.click()
                print("Navigated to Archived Chats section.")

                # Refresh the `pane-side` element to avoid stale references
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, 'pane-side'))
                )
                print("Refreshed chat list for archived chats.")
                

                for chat_name in self.chat_names:
                    if chat_name in processed_chats:
                        continue  # Skip already processed chats
                    try:
                        print(f"Attempting to find and scrape archived chat: {chat_name}")
                        self.open_chat(chat_name)
                        self.scroll_to_target_date(time_start=time_start, time_end=time_end)
                        self.extract_messages_with_images(time_start, time_end)
                        print(f"Scraping completed for archived chat: {chat_name}")
                        processed_chats.add(chat_name)  # Mark chat as processed
                    except Exception as e:
                        print(f"Error scraping archived chat '{chat_name}'")
                        chats_not_found.add(chat_name)  # Mark chat as not found

                # Navigate back to the main chat panel
                back_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//div[@aria-label="Back"]'))
                )
                back_button.click()
                print("Returned to the main chat panel after scraping archived chats.")
            except TimeoutException:
                print("Timeout: Could not locate Archived Chats button or navigation elements.")
            except Exception as e:
                print(f"Error while navigating or scraping archived chats: {e}")

            # Step 2: Scrape Normal Chats
            print("Scraping normal chats...")
            pane_side = self.driver.find_element(By.ID, 'pane-side')
            while chats_not_found:
                for chat_name in list(chats_not_found):
                    if chat_name in processed_chats:
                        continue  # Skip already processed chats
                    try:
                        print(f"Attempting to find and scrape normal chat: {chat_name}")
                        self.open_chat(chat_name)
                        self.scroll_to_target_date(time_start=time_start, time_end=time_end)
                        self.extract_messages_with_images(time_start, time_end)
                        print(f"Scraping completed for normal chat: {chat_name}")
                        processed_chats.add(chat_name)  # Mark chat as processed
                        chats_not_found.remove(chat_name)  # Remove from not found list
                    except Exception as e:
                        print(f"Error scraping normal chat '{chat_name}': {e}")

                # Scroll pane-side to load more chats
                last_scroll_position = self.driver.execute_script("return arguments[0].scrollTop", pane_side)
                self.driver.execute_script("arguments[0].scrollTop += 200", pane_side)
                time.sleep(2)  # Allow time for chats to load
                new_scroll_position = self.driver.execute_script("return arguments[0].scrollTop", pane_side)

                # Stop if no new chats are being loaded
                if last_scroll_position == new_scroll_position:
                    print("No more chats to load.")
                    break

            print("Scraping completed for all chats.")

        except Exception as e:
            print(f"Error while scraping chats: {e}")

    def open_chat(self, chat_name):
        """
        Open a specific chat by its name, scrolling if necessary.
        """
        pane_side = self.driver.find_element(By.ID, 'pane-side')

        def escape_xpath_string(s):
            if "'" in s and '"' in s:
                return "concat(" + ", ".join(f"'{part}'" for part in s.split("'")) + ")"
            if "'" in s:
                return f'"{s}"'
            return f"'{s}'"

        chat_list_xpath = f"//span[@title={escape_xpath_string(chat_name)}]"

        try:
            # Check if the chat is already visible before scrolling
            chat = pane_side.find_element(By.XPATH, chat_list_xpath)
            ActionChains(self.driver).move_to_element(chat).perform()
            print(f"Chat '{chat_name}' is already visible. Clicking on it.")
            chat.click()
            return
        except NoSuchElementException:
            print(f"Chat '{chat_name}' is not immediately visible. Scrolling to find it...")

        while True:
            try:
                chat = pane_side.find_element(By.XPATH, chat_list_xpath)
                ActionChains(self.driver).move_to_element(chat).perform()
                print(f"Chat '{chat_name}' is now visible. Clicking on it.")
                chat.click()
                return
            except NoSuchElementException:
                print(f"Chat '{chat_name}' not visible. Scrolling further...")
                self.driver.execute_script("arguments[0].scrollTop += 200", pane_side)
                time.sleep(2)  # Allow time for chats to load

                # Check if we've reached the bottom of the chat list
                last_scroll_position = self.driver.execute_script("return arguments[0].scrollTop", pane_side)
                self.driver.execute_script("arguments[0].scrollTop += 200", pane_side)
                new_scroll_position = self.driver.execute_script("return arguments[0].scrollTop", pane_side)
                if last_scroll_position == new_scroll_position:
                    raise Exception(f"Chat '{chat_name}' not found.")

    def scroll_to_target_date(self, target_date=None, time_start=None, time_end=None):
        """
        Scrolls up to the specified target date. If target_date is None, scrolls to the very top of the chat.
        Recognizes "TODAY" as the current date and handles day names within the current week.
        Stops scrolling when the message's timestamp or date is within the provided range.
        """
        try:
            # Parse target date and time range if provided
            if target_date:
                target_date = datetime.strptime(target_date, "%m/%d/%Y")
            time_start_dt = datetime.strptime(time_start, "%I:%M %p") if time_start else None
            time_end_dt = datetime.strptime(time_end, "%I:%M %p") if time_end else None

            # Check if the range crosses midnight
            range_crosses_midnight = time_start_dt and time_end_dt and time_end_dt < time_start_dt

            # Adjust time_end_dt for overnight ranges
            time_end_dt_adjusted = time_end_dt + timedelta(days=1) if range_crosses_midnight else time_end_dt

            # Locate the initial message container
            message_container_locator = (By.XPATH, '//div[contains(@class, "_amjv")]')
            message_container = self.refresh_element(self.driver, message_container_locator)
            previous_height = None

            while True:
                # Refresh message container to avoid stale element references
                message_container = self.refresh_element(self.driver, message_container_locator)

                # Check for and click the "load older messages" button, if present
                try:
                    load_more_button = self.driver.find_element(By.XPATH, '//button[contains(@class, "x14m1o6m x126m2zf")]')
                    load_more_button.click()
                    print("Clicked to load older messages.")
                    time.sleep(2)
                except NoSuchElementException:
                    pass

                # Perform scrolling to load more messages
                for _ in range(12):
                    try:
                        message_container.send_keys(Keys.PAGE_UP)
                        time.sleep(1)
                    except StaleElementReferenceException:
                        print("Container went stale during scroll. Refreshing...")
                        message_container = self.refresh_element(self.driver, message_container_locator)

                # Process date elements to locate the target date
                date_elements = message_container.find_elements(By.XPATH, '//div[@class="_amk4 _amkb"]/span[@class="_ao3e"]')
                for date_element in date_elements:
                    try:
                        date_text = date_element.text
                        message_date = self.parse_date_text(date_text)

                        if message_date:
                            # Stop scrolling if we've reached the target date
                            if target_date and message_date < target_date:
                                print("Reached messages older than the target date.")
                                return
                    except StaleElementReferenceException:
                        print("Date element went stale. Skipping...")
                    except ValueError:
                        print("Error parsing date:", date_element.text)

                # Check and process image messages for time range
                image_messages = message_container.find_elements(
                    By.XPATH,
                    '//div[contains(@class, "message-in") or contains(@class, "message-out")]'
                    '//div[contains(@role, "button") and contains(@aria-label, "Open picture")]'
                    '/ancestor::div[contains(@class, "message-in") or contains(@class, "message-out")]'
                )
                for message in image_messages:
                    try:
                        # Extract timestamp
                        try:
                            timestamp_element = message.find_element(By.XPATH, './/div[contains(@class, "copyable-text")]')
                            raw_timestamp_text = timestamp_element.get_attribute("data-pre-plain-text").rstrip("]").strip()
                        except NoSuchElementException:
                            raw_timestamp_text = ""
                        time_text = raw_timestamp_text.split(",")[0].strip()
                        time_text = time_text.lstrip("[").strip()
                        time_text = "".join(time_text.split())  # Remove all whitespace characters

                        # Skip processing if time_text is empty
                        if not time_text:
                            continue

                        # Parse the time into a datetime object
                        try:
                            # Attempt to parse the time in both 12-hour and 24-hour formats
                            try:
                                parsed_time = datetime.strptime(time_text, "%I:%M%p").time()  # 12-hour format
                            except ValueError:
                                parsed_time = datetime.strptime(time_text, "%H:%M").time()  # 24-hour format
                            
                            # Combine the parsed time with today's date
                            message_time = datetime.combine(datetime.today(), parsed_time)

                            # Adjust message time for overnight ranges
                            if range_crosses_midnight and message_time < time_start_dt:
                                message_time += timedelta(days=1)

                        except ValueError as ve:
                            print(f"ValueError: Could not parse timestamp. Cleaned: '{time_text}'. Exception: {ve}")
                            continue

                        # Stop scrolling if the message is outside the time range
                        if time_start_dt and message_time < time_start_dt:
                            print(f"Reached image message older than the start time: {time_start_dt.strftime('%I:%M %p')}.")
                            return
                        if time_end_dt_adjusted and message_time > time_end_dt_adjusted:
                            print(f"Reached image message newer than the end time: {time_end_dt_adjusted.strftime('%I:%M %p')}.")
                            return

                    except (StaleElementReferenceException, ValueError, AttributeError, NoSuchElementException):
                        print("Error processing image message, skipping.")

                # Check if we've reached the top of the chat by comparing scroll height
                current_height = self.driver.execute_script("return arguments[0].scrollHeight;", message_container)
                if previous_height == current_height:
                    print("Reached the top of the chat.")
                    break
                previous_height = current_height

        except Exception as e:
            print(f"Error during scrolling: {e}")


    def parse_time_string(time_string):
        """
        Parse a time string in either 12-hour (e.g., "10:47 PM") or 24-hour (e.g., "22:02") format.
        Returns a datetime.time object.
        """
        try:
            if "AM" in time_string.upper() or "PM" in time_string.upper():
                # Handle 12-hour format
                return datetime.strptime(time_string, "%I:%M %p").time()
            else:
                # Handle 24-hour format
                return datetime.strptime(time_string, "%H:%M").time()
        except ValueError as e:
            raise ValueError(f"Invalid time format: {time_string}. Error: {e}")

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
            
    def fetch_blob_with_retries(self, driver, blob_url, retries=3, delay=5):
        """
        Fetches a blob URL with retries if it fails.
        
        Args:
            driver: WebDriver instance.
            blob_url: The blob URL to fetch.
            retries: Number of retry attempts.
            delay: Delay in seconds between retries.

        Returns:
            The base64 data of the blob or None if all retries fail.
        """
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
        for attempt in range(1, retries + 1):
            try:
                base64_data = driver.execute_script(script, blob_url)
                if base64_data and base64_data.startswith("data:image"):
                    print(f"Successfully fetched blob URL on attempt {attempt}")
                    return base64_data
            except Exception as e:
                print(f"Attempt {attempt} failed to fetch blob URL: {e}")
                
                # Only sleep if there are retries remaining
                if attempt < retries:
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)

        print("All retry attempts failed.")
        return None

    def extract_messages_with_images(self, time_start=None, time_end=None):
        time_start_dt = datetime.strptime(time_start, "%I:%M %p") if time_start else None
        time_end_dt = datetime.strptime(time_end, "%I:%M %p") if time_end else None

        processed_blob_urls = set()

        range_crosses_midnight = time_start_dt and time_end_dt and time_start_dt > time_end_dt

        # Create a temporary directory to store images
        with tempfile.TemporaryDirectory() as temp_dir:
            messages_with_images = self.driver.find_elements(
                By.XPATH,
                '//div[contains(@class, "message-in") or contains(@class, "message-out")]'
                '//div[contains(@role, "button") and contains(@aria-label, "Open picture")]'
                '/ancestor::div[contains(@class, "message-in") or contains(@class, "message-out")]'
            )

            processed_messages = []

            for idx, message in enumerate(reversed(messages_with_images)):
                try:
                    # Retrieve the timestamp
                    try:
                        timestamp_element = message.find_element(By.XPATH, './/div[contains(@class, "copyable-text")]')
                        raw_timestamp = timestamp_element.get_attribute("data-pre-plain-text")
                        timestamp_text = raw_timestamp.rstrip("]").strip().split(",")[0].strip() if raw_timestamp else ""
                        timestamp_text = timestamp_text.lstrip("[")
                        try:
                            message_time = datetime.strptime(timestamp_text, "%I:%M %p")  # 12-hour format
                        except ValueError:
                            message_time = datetime.strptime(timestamp_text, "%H:%M")  # 24-hour format
                    except (NoSuchElementException, ValueError) as e:
                        print(f"Message {idx + 1}: Timestamp not found or invalid.")
                        try:
                            aria_label_text = message.get_attribute("aria-label")
                            if aria_label_text:
                                # Extract timestamp from aria-label, assuming it's the last part
                                timestamp_text = aria_label_text.split()[-2] + " " + aria_label_text.split()[-1]  # Example: "3:12 AM"
                                try:
                                    message_time = datetime.strptime(timestamp_text, "%I:%M %p")  # 12-hour format
                                except ValueError:
                                    message_time = datetime.strptime(timestamp_text, "%H:%M")  # 24-hour format
                                print(f"Fallback timestamp successfully extracted.")
                            else:
                                raise ValueError("aria-label is empty or does not contain timestamp.")
                        except (NoSuchElementException, ValueError) as fallback_error:
                            print(f"Fallback timestamp extraction also failed for message {idx + 1}: {fallback_error}.")
                            message_time = None

                    # Adjust for overnight ranges
                    time_end_dt_adjusted = time_end_dt + timedelta(days=1) if range_crosses_midnight else time_end_dt
                    if message_time:
                        if range_crosses_midnight and message_time < time_start_dt:
                            message_time += timedelta(days=1)
                        if time_start_dt and message_time < time_start_dt:
                            print(f"Message {idx + 1} stopped: Time {message_time.strftime('%I:%M %p')} is before the start range.")
                            break
                        if time_end_dt_adjusted and message_time > time_end_dt_adjusted:
                            print(f"Message {idx + 1} stopped: Time {message_time.strftime('%I:%M %p')} exceeds the end range.")
                            break

                    # Retrieve the image description
                    try:
                        description_element = message.find_elements(By.XPATH, './/span[@class="_ao3e selectable-text copyable-text"]/span')
                        if description_element:
                            description_html = description_element[0].get_attribute("outerHTML")
                            description = description_element[0].text
                        else:
                            print("Description element not found. Defaulting to 'No Description'.")
                            description = " "
                    except Exception as e:
                        print(f"Error extracting description for message {idx + 1}: {e}")
                        description = "Error Extracting Description"


                    # Retrieve image elements
                    image_elements = message.find_elements(By.XPATH, './/img')
                    blob_image = next((img for img in image_elements if img.get_attribute("src") and img.get_attribute("src").startswith("blob:")), None)
                    base64_image = next((img for img in image_elements if img.get_attribute("src") and img.get_attribute("src").startswith("data:image")), None)

                    temp_file_path = None

                    # Process blob image
                    if blob_image:
                        blob_url = blob_image.get_attribute("src")
                        print(f"Blob URL: {blob_url}")

                        # # Skip duplicate blob URLs
                        # if blob_url in processed_blob_urls:
                        #     print(f"Message {idx + 1}: Duplicate Blob URL detected. Skipping...")
                        #     continue
                        # processed_blob_urls.add(blob_url)

                        if not blob_url or not blob_url.startswith("blob:"):
                            print(f"Message {idx + 1}: Invalid blob URL, skipping.")
                            continue

                        try:
                            base64_data = self.fetch_blob_with_retries(self.driver, blob_url, retries=5, delay=3)  # Adjust retries and delay as needed
                            if base64_data:
                                base64_content = base64_data.split(",")[1]
                                temp_file_path = os.path.join(temp_dir, f"extracted_image_{idx + 1}.png")
                                with open(temp_file_path, "wb") as file:
                                    file.write(base64.b64decode(base64_content))
                                print(f"Message {idx + 1}: Blob image saved to {temp_file_path}.")
                            else:
                                print(f"Message {idx + 1}: Failed to fetch blob after retries.")
                        except Exception as e:
                            print(f"Message {idx + 1}: Error fetching blob URL. Error: {e}")
                            
                    # Process base64 image
                    elif base64_image:
                        image_src = base64_image.get_attribute("src")
                        print(f"Message {idx + 1}: Base64 image src - {image_src}")
                        try:
                            base64_content = image_src.split(",")[1]
                            temp_file_path = os.path.join(temp_dir, f"extracted_image_{idx + 1}.png")
                            with open(temp_file_path, "wb") as file:
                                file.write(base64.b64decode(base64_content))
                            print(f"Message {idx + 1}: Base64 image saved to {temp_file_path}.")
                        except Exception as e:
                            print(f"Message {idx + 1}: Error processing base64 image. Error: {e}")

                    # Fallback to screenshot
                    if not temp_file_path:
                        print(f"Message {idx + 1}: Fetching blob failed. Clicking the image to retry.")
                        try:
                            # Scroll the image into view and wait until it is visible
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", blob_image)

                            # Check for all overlapping blob images in the same container
                            image_elements = message.find_elements(By.XPATH, './/img[contains(@src, "blob:")]')

                            # Attempt to click each image in order
                            for img_idx, img in enumerate(image_elements):
                                try:
                                    print(f"Trying to click blob image {img_idx + 1}/{len(image_elements)}: {img.get_attribute('src')}")
                                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", img)
                                    WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(img))
                                    img.click()
                                    print(f"Successfully clicked blob image {img_idx + 1}.")
                                    break
                                except Exception as e:
                                    print(f"Blob image {img_idx + 1} click failed. Trying next image. Error: {e}")

                            # Wait for the viewer to load the image
                            blob_image_viewer = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.XPATH, '//img[contains(@src, "blob:")]'))
                            )

                            # Retry fetching the blob URL from the opened viewer
                            blob_url_retry = blob_image_viewer.get_attribute("src")
                            base64_data = self.fetch_blob_with_retries(self.driver, blob_url_retry, retries=3, delay=3)

                            if base64_data:
                                # Save the blob image after retry
                                base64_content = base64_data.split(",")[1]
                                temp_file_path = os.path.join(temp_dir, f"retried_image_{idx + 1}.png")
                                with open(temp_file_path, "wb") as file:
                                    file.write(base64.b64decode(base64_content))
                                print(f"Message {idx + 1}: Blob image saved to {temp_file_path} after retry.")
                            else:
                                print(f"Message {idx + 1}: Blob retry failed.")

                        except Exception as e:
                            print(f"Message {idx + 1}: Error handling fallback for blob fetch. Error: {e}")

                        # Always attempt fallback screenshot if blob fetch or retry fails
                        if not temp_file_path:
                            print(f"Message {idx + 1}: Fetching blob failed. Attempting to ensure image is open for fallback.")
                            try:
                                # Ensure the image is open before taking a screenshot
                                # try:
                                #     # Scroll the image into view
                                #     self.driver.execute_script("arguments[0].scrollIntoView(true);", blob_image)
                                #     print("scrolling")
                                #     time.sleep(1)  # Allow scrolling to complete
                                    
                                #     # Try clicking the image to open the viewer if it's not already open
                                #     if not self.driver.find_elements(By.XPATH, '//img[contains(@src, "blob:")]'):
                                #         WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, './/img[contains(@src, "blob:")]')))
                                #         blob_image.click()
                                #         time.sleep(2)  # Allow the viewer to load

                                # except Exception as e:
                                #     print(f"Message {idx + 1}: Could not open image viewer. Error: {e}")

                                # Now take a screenshot of the open viewer
                                blob_image_viewer = self.driver.find_element(By.XPATH, '//img[contains(@src, "blob:")]')
                                screenshot_path = os.path.join(temp_dir, f"screenshot_image_{idx + 1}.png")
                                blob_image_viewer.screenshot(screenshot_path)
                                print(f"Message {idx + 1}: Screenshot saved to {screenshot_path}.")
                                temp_file_path = screenshot_path

                            except Exception as e:
                                print(f"Message {idx + 1}: Error taking fallback screenshot. Error: {e}")

                        # Close the image viewer if it's still open
                        try:
                            close_button = self.driver.find_element(By.XPATH, '//div[@title="Close"]')
                            close_button.click()
                            time.sleep(1)
                        except Exception:
                            print(f"Message {idx + 1}: Could not find or click close button.")

                    # Append processed message
                    processed_messages.append({
                        "file_path": temp_file_path,
                        "caption": f"{description}"
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
                    try:
                        message_time = datetime.strptime(timestamp_text, "%I:%M %p")  # 12-hour format
                    except ValueError:
                        message_time = datetime.strptime(timestamp_text, "%H:%M")  # 24-hour format
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

    def take_screenshot(self, file_name="screenshot.png"):
        """
        Takes a screenshot of the current browser state.
        Args:
        - file_name: The name of the file to save the screenshot.
        """
        try:
            screenshot_path = os.path.join(os.getcwd(), file_name)
            self.driver.save_screenshot(screenshot_path)
            print(f"Screenshot saved at {screenshot_path}")
        except Exception as e:
            print(f"Failed to take screenshot: {e}")

# Usage example
# if __name__ == "__main__":
#     scraper = WhatsAppScraper(chat_name="Paul", date_limit="11/01/2024", scrape_all=False, new_session=True)
#     scraper.login()
#     # scraper.open_chat()
#     # scraper.scroll_to_target_date()
#     # scraper.extract_messages_with_images()
#     # scraper.extract_messages_with_videos()
#     scraper.close()

if __name__ == "__main__":
    # Define test inputs
    chat_names = ["Paul", "Duke Residency & Apartments"]  # Replace with real chat names
    time_start = "08:00 AM"
    time_end = "11:00 PM"
    
    # Initialize the scraper
    scraper = WhatsAppScraper(
        user_id= 1,
        user_email="admin@user.com",
        chat_names=chat_names,
        date_limit="11/01/2024",
        scrape_all=False,
        new_session=True,
        headless=True  # Set to False to see the browser
    )
    
    try:
        # Login to WhatsApp Web
        scraper.login()
        
        # Run the scraping logic
        scraper.scrape_chats(time_start=time_start, time_end=time_end)
    
    except Exception as e:
        print(f"An error occurred during testing: {e}")
    
    finally:
        # Ensure cleanup
        scraper.close()