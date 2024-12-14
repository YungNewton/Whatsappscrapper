import requests
import json
from io import BytesIO
import time

class TelegramPoster:
    def __init__(self, bot_token, channel_username):
        """
        Initializes the TelegramPoster with a bot token and a destination (chat ID or username).

        Args:
            bot_token (str): Bot token for accessing Telegram's API.
            destination (str): Destination in the format 'chat_id/message_thread_id' or 'chat_id' or '@username'.
        """
        self.bot_token = bot_token
        self.destination = channel_username
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    def parse_destination(self):
        """
        Parses the destination to extract chat_id and optional message_thread_id.

        Returns:
            chat_id (str): The chat ID (with '-100' prefix for private groups).
            message_thread_id (int or None): The message thread ID if provided, otherwise None.
        """
        if '/' in self.destination:
            chat_id, thread_id = self.destination.split('/', 1)
            chat_id = chat_id.strip('"').strip("'")  # Remove any surrounding quotes
            thread_id = thread_id.strip('"').strip("'")  # Remove any surrounding quotes
            if not chat_id.startswith('-100') and chat_id.isdigit():  # Ensure private group IDs have '-100'
                chat_id = f"-100{chat_id}"
            print(f"Parsed chat_id: {chat_id}, message_thread_id: {thread_id}")  # Debug
            return chat_id, int(thread_id)  # Ensure thread ID is an integer
        print(f"Parsed chat_id: {self.destination}, no thread_id")  # Debug
        return self.destination.strip('"').strip("'"), None

    def post_image(self, image_data, caption):
        """
        Posts an image to Telegram with rate-limit handling and optional topic ID support.

        Args:
            image_data (str or BytesIO): The image data (file path or BytesIO object).
            caption (str): The caption to include with the image.
        """
        # Ensure caption fits within Telegram's 1024-character limit
        max_caption_length = 1024
        if len(caption) > max_caption_length:
            caption = caption[:max_caption_length - 3] + "..."  # Truncate with ellipsis if too long

        # Parse the destination to handle optional message_thread_id
        chat_id, thread_id = self.parse_destination()
        url = f"{self.api_url}/sendPhoto"

        def prepare_payload():
            """
            Prepares the payload for sending the image.

            Returns:
                files (dict): File payload.
                data (dict): Data payload.
                file (file or None): File object to close later.
            """
            if isinstance(image_data, str):  # Image data is a file path
                file = open(image_data, "rb")  # Open file outside the `with` block
                files = {'photo': file}
                data = {'chat_id': chat_id, 'caption': caption}
                if thread_id:
                    data['message_thread_id'] = thread_id
                return files, data, file
            elif isinstance(image_data, BytesIO):  # Image data is a BytesIO object
                image_data.seek(0)  # Ensure we're reading from the beginning
                files = {'photo': ('image.png', image_data, 'image/png')}
                data = {'chat_id': chat_id, 'caption': caption}
                if thread_id:
                    data['message_thread_id'] = thread_id
                return files, data, None
            else:
                raise ValueError("Unsupported image data type.")

        # Retry logic for handling rate limits
        while True:
            try:
                files, data, file = prepare_payload()  # Prepare the payload
                print(f"Sending payload: {data}")  # Debug
                response = requests.post(url, data=data, files=files)
                if response.status_code == 200:
                    print("Image posted successfully!")
                    if file:
                        file.close()  # Close the file after the request
                    return  # Exit once successful
                elif response.status_code == 429:  # Too Many Requests
                    retry_after = response.json().get("parameters", {}).get("retry_after", 60)
                    print(f"Rate limit hit. Retrying after {retry_after} seconds...")
                    time.sleep(retry_after)
                else:
                    print(f"Failed to post image: {response.text}")
                    break  # Exit on non-rate-limit errors
            except ValueError as ve:
                print(f"Error: {ve}")
                break  # Exit for unsupported image data type
            except Exception as e:
                print(f"Unexpected error: {e}")
                break  # Exit for unexpected errors
            finally:
                if file:
                    file.close()  # Ensure file is closed even on exceptions
        
    def post_images(self, image_list, caption):
        """
        Posts multiple images as a single media group with the same caption.

        Args:
            image_list (list): A list of image file paths or BytesIO objects.
            caption (str): The caption to include with the media group.
        """
        max_caption_length = 1024
        if len(caption) > max_caption_length:
            caption = caption[:max_caption_length - 3] + "..."  # Truncate with ellipsis if too long

        chat_id, thread_id = self.parse_destination()
        url = f"{self.api_url}/sendMediaGroup"

        media_group = []
        files = {}
        for idx, image_data in enumerate(image_list):
            file_key = f"photo{idx}"
            if isinstance(image_data, str):
                files[file_key] = open(image_data, "rb")
            elif isinstance(image_data, BytesIO):
                image_data.seek(0)
                files[file_key] = ("image.png", image_data, "image/png")
            else:
                print(f"Unsupported image type at index {idx}. Skipping...")
                continue

            media_group.append({
                "type": "photo",
                "media": f"attach://{file_key}",
                "caption": caption if idx == 0 else ""  # Caption only for the first image
            })

        data = {
            "chat_id": chat_id,
            "media": json.dumps(media_group)  # Properly serialize the media group
        }
        if thread_id:
            data["message_thread_id"] = thread_id

        try:
            response = requests.post(url, data=data, files=files)
        finally:
            for file in files.values():
                if hasattr(file, "close"):
                    file.close()
