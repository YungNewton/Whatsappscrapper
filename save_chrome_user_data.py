import os
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


class WhatsAppLogin:
    def __init__(self, user_id, chrome_user_data_dir="chrome_user_data"):
        self.user_id = user_id
        self.chrome_user_data_dir = os.path.join(os.getcwd(), chrome_user_data_dir, f"user_{user_id}")
        self.driver = None
        self.clear_user_data()

    def clear_user_data(self):
        """
        Delete the user-specific chrome_user_data directory to start fresh.
        """
        if os.path.exists(self.chrome_user_data_dir):
            print(f"Deleting existing user data directory for user {self.user_id}: {self.chrome_user_data_dir}")
            shutil.rmtree(self.chrome_user_data_dir)
        else:
            print(f"No existing user data directory found for user {self.user_id}.")

    def init_driver(self):
        """
        Initialize the Chrome WebDriver with the necessary options.
        """
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={self.chrome_user_data_dir}")  # Persist user data
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--window-size=1280,720")

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.driver.set_window_size(1280, 720)

    def open_whatsapp_web(self):
        """
        Open WhatsApp Web and wait for the user to log in.
        """
        if self.driver is None:
            self.init_driver()

        print("Opening WhatsApp Web...")
        self.driver.get("https://web.whatsapp.com")

        try:
            # Wait until login is detected
            print("Waiting for login...")
            WebDriverWait(self.driver, 600).until(
                EC.presence_of_element_located((By.XPATH, '//span[@data-icon="chats-filled"]'))
            )
            print("Login detected. Chrome user data saved successfully.")
        except Exception as e:
            print(f"Error during WhatsApp login: {e}")
        finally:
            # Keep the browser open for the user to close manually
            print("Login completed. Please close the browser window manually when done.")
            try:
                self.driver.current_url  # Keep the browser open by checking its state
            except Exception:
                print("Browser closed by user.")


    def close_driver(self):
        """
        Close the WebDriver instance.
        """
        if self.driver:
            self.driver.quit()
            print("Browser closed.")


# Example usage (if running independently)
if __name__ == "__main__":
    whatsapp_login = WhatsAppLogin()
    whatsapp_login.open_whatsapp_web()
