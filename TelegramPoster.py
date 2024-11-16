import requests
from io import BytesIO

class TelegramPoster:
    def __init__(self, bot_token, channel_username):
        self.bot_token = bot_token
        self.channel_username = channel_username
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"

    def post_image(self, image_data, caption):
        # Ensure caption fits within Telegram's 1024-character limit
        max_caption_length = 1024
        if len(caption) > max_caption_length:
            caption = caption[:max_caption_length - 3] + "..."  # Truncate with ellipsis if too long

        # Prepare the payload based on image_data type
        if isinstance(image_data, str):  # image_data is a file path
            with open(image_data, "rb") as file:
                files = {'photo': file}
                data = {'chat_id': self.channel_username, 'caption': caption}
                response = requests.post(self.api_url, data=data, files=files)
        elif isinstance(image_data, BytesIO):  # image_data is a BytesIO object
            image_data.seek(0)  # Ensure we're reading from the beginning
            files = {'photo': ('image.png', image_data, 'image/png')}
            data = {'chat_id': self.channel_username, 'caption': caption}
            response = requests.post(self.api_url, data=data, files=files)
        else:
            print("Error: Unsupported image data type.")
            return

        # Check the response status
        if response.status_code == 200:
            print("Image posted successfully!")
        else:
            print(f"Failed to post image: {response.text}")
