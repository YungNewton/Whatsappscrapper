import requests

url = "https://api.telegram.org/bot7766870224:AAGwLCBlye9lPfxZeSWnJ9_Anji7LBmW_qs/sendMessage"
payload = {
    "chat_id": "-1002302681316",  # Replace with your chat_id
    "message_thread_id":139,    # Replace with your message_thread_id
    "text": "Test"
}
response = requests.post(url, data=payload)
print(response.json())
