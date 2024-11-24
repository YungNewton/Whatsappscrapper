from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from datetime import timedelta
import threading
from WhatsAppScraper import WhatsAppScraper  # Assuming this is the scraper class
from TelegramPoster import TelegramPoster
import sqlite3
import subprocess
import os

app = Flask(__name__, static_folder='build', static_url_path='/')
app.secret_key = 'super_secret_key'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # 30 minutes timeout
CORS(app, supports_credentials=True)  # Allow cookies in cross-origin requests

# Shared variables for managing scraper instance and cancellation
scraper = None
cancel_event = threading.Event()
scraper_process = None

# Initialize database with a single admin user
def init_db():
    conn = sqlite3.connect('db.sqlite')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT, password TEXT)''')
    conn.commit()

    # Add default admin user if not already in the database
    cursor.execute("SELECT * FROM users WHERE email='admin@user.com'")
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", ('admin@user.com', 'adminpassword'))
        conn.commit()
    conn.close()

def start_scraper(chat_names, channel_username):
    """
    Starts the `run_scraper.py` script with the given chat names and channel username.
    """
    try:
        if scraper_process and scraper_process.poll() is None:  # Check if the process is running
            print("Stopping the existing scraper process...")
            scraper_process.terminate()  # Send SIGTERM
            scraper_process.wait()  # Wait for it to stop
            print("Existing scraper process stopped.")
            
        # Prepare the arguments for the run_scraper.py script
        chat_names_str = ",".join(chat_names)  # Convert list to comma-separated string
        args = [
            "python3", "run_scraper.py",
            "--chatNames", chat_names_str,
            "--channelUsername", channel_username
        ]

        # Run the process in detached mode
        subprocess.Popen(
            args, stdout=None, stderr=None, stdin=None, close_fds=True
        )
    except Exception as e:
        print(f"Error starting run_scraper.py: {e}")
        raise

# Static file serving
@app.route('/<path:path>')
def serve_static_file(path):
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

@app.errorhandler(404)
def handle_404(e):
    # Catch-all route for unknown paths
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

# Login endpoint
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    # Verify user credentials
    conn = sqlite3.connect('db.sqlite')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        session['user'] = email
        session.permanent = True  # Enable session timeout
        return jsonify({'message': 'Login successful'}), 200
    else:
        return jsonify({'message': 'Invalid email or password'}), 401

# Logout endpoint
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({'message': 'Logged out successfully'}), 200

# Protected bot access route
@app.route('/bot_access', methods=['GET'])
def bot_access():
    if 'user' in session:
        return jsonify({'message': 'Access granted to bot interface'}), 200
    else:
        return jsonify({'message': 'Unauthorized access'}), 401

# Keep-alive endpoint
@app.route('/keep_alive', methods=['GET'])
def keep_alive():
    if 'user' in session:
        session.modified = True  # Refresh the session
        return jsonify({'message': 'Session kept alive'}), 200
    return jsonify({'message': 'No active session'}), 401

@app.route('/scrape', methods=['POST', 'OPTIONS'])
def scrape():
    if request.method == 'OPTIONS':
        return jsonify({"message": "Preflight request handled"}), 200

    global scraper, cancel_event
    cancel_event.clear()

    data = request.json
    chat_names = data.get('chatNames', [])  # List of chat names
    date_limit = data.get('dateLimit')
    channel_username = data.get('channelUsername')
    scrape_all = data.get('scrapeAll', False)
    new_session = data.get('newWhatsAppSession', False)

    # Add '@' if missing
    if channel_username and not channel_username.startswith('@'):
        channel_username = f"@{channel_username}"

    try:
        # Commenting out the TelegramPoster initialization
        telegram_poster = TelegramPoster(
            bot_token="7766870224:AAGwLCBlye9lPfxZeSWnJ9_Anji7LBmW_qs",
            channel_username=channel_username
        )
        print("TelegramPoster initialized")

        # Commenting out the WhatsAppScraper initialization
        # scraper = WhatsAppScraper(
        #     chat_name=None,  # Chat name will be set dynamically
        #     date_limit=date_limit,
        #     scrape_all=scrape_all,
        #     new_session=new_session,
        #     cancel_event=cancel_event,
        #     telegram_poster=telegram_poster
        # )
        # scraper.login()

        results = []
        for chat_name in chat_names:
            print(f"Skipping scrape for chat: {chat_name}")
            # Commenting out the actual scraping logic
            try:
            #     scraper.chat_name = chat_name
            #     # scraper.open_chat()
            #     # scraper.scroll_to_target_date()
            #     # scraper.extract_messages_with_images()
            #     # scraper.extract_messages_with_videos()
            #     # Call the function to start `run_scraper.py`
                start_scraper(chat_names, channel_username)
            #     results.append({"chatName": chat_name, "status": "Completed"})
            except Exception as e:
                print(f"Error scraping chat '{chat_name}': {e}")
            #     results.append({"chatName": chat_name, "status": f"Error: {e}"})

        # Return a placeholder response
        return jsonify({"message": "success", "results": results}), 200

    except Exception as e:
        print(f"Exception encountered: {e}")
        return jsonify({"message": f"Error: {str(e)}"}), 500

    finally:
        # Commenting out the scraper cleanup
        # if scraper is not None:
        #     try:
        #         scraper.close()
        #         print("Scraper closed successfully")
        #     except Exception as e:
        #         print(f"Error while closing scraper: {e}")
        scraper = None

# Cancel scraping endpoint
@app.route('/cancel_scraping', methods=['POST'])
def cancel_scraping():
    global cancel_event, scraper
    if scraper is not None:
        cancel_event.set()  # Trigger the cancellation
        return jsonify({"message": "Scraping process cancelled successfully!"}), 200
    else:
        return jsonify({"message": "No scraping process is currently running."}), 400
    

# Initialize the database
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000,debug=True)
