import os
import shutil
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


class WhatsAppLogin:
    def __init__(self, user_id, chrome_user_data_dir="chrome_user_data"):
        self.user_id = user_id
        self.chrome_user_data_dir = os.path.join(os.getcwd(), chrome_user_data_dir, f"user_{user_id}")
        self.driver = None
        os.system("pkill -f chrome")
        os.system("pkill -f chromedriver")
        # self.clear_user_data()

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
        options = uc.ChromeOptions()
        options.add_argument(f"--user-data-dir={self.chrome_user_data_dir}")  # Persist user data
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")  # Disable shared memory usage
        options.add_argument("--disable-gpu")  # Disable GPU rendering
        options.add_argument("--start-maximized")  # Start browser maximized
        options.add_argument("--disable-blink-features=AutomationControlled")  # Prevent automation detection
        options.add_argument("--window-size=1280,720")

        self.driver = uc.Chrome(options=options)  # Initialize undetected ChromeDriver
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
            # Wait until WhatsApp Web starts loading
            print("Waiting for WhatsApp Web to load...")
            WebDriverWait(self.driver, 600).until(
                EC.presence_of_element_located((By.XPATH, '//span[@data-icon="chats-filled"]'))
            )
            
            # Wait indefinitely for user to close the browser
            print("Waiting for the user to complete login and close the browser...")
            while True:
                try:
                    # Poll the browser to check if it is still open
                    if not self.driver.window_handles:
                        print("Browser closed by the user. Chrome user data saved successfully.")
                        break
                except Exception as e:
                    print(f"Browser state check failed: {e}")
                    break
                time.sleep(1)

        except Exception as e:
            print(f"Error during WhatsApp login: {e}")

        finally:
            # Ensure proper cleanup if the browser was closed
            self.close_driver()
            print("Browser session ended.")

    def close_driver(self):
        """
        Close the WebDriver instance.
        """
        if self.driver:
            self.driver.quit()
            print("Browser closed.")


# Example usage (if running independently)
if __name__ == "__main__":
    whatsapp_login = WhatsAppLogin(user_id=4)
    whatsapp_login.open_whatsapp_web()
