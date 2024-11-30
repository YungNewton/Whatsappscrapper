from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, init_db
from config import Config
import threading
import subprocess
import os
import time
from WhatsAppScraper import WhatsAppScraper
from TelegramPoster import TelegramPoster
from save_chrome_user_data import WhatsAppLogin
import atexit

app = Flask(__name__, static_folder='static', static_url_path='/')
app.config.from_object(Config)
CORS(app, supports_credentials=True)

# Initialize database and Flask-Login
init_db(app)
login_manager = LoginManager(app)
login_manager.login_view = '/login'

# Shared variables for scrapers
scraper = None
cancel_event = threading.Event()
scraper_lock = threading.Lock()
user_scraper_processes = {}

# SQLite user loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def start_scraper(user_id, chat_names, channel_username):
    """
    Starts a scraper process for a specific user.
    """
    global user_scraper_processes
    with scraper_lock:
        try:
            # Check if a scraper process is already running for this user
            if user_id in user_scraper_processes:
                existing_process = user_scraper_processes[user_id]
                if existing_process.poll() is None:
                    print(f"Stopping existing scraper process for user {user_id}...")
                    existing_process.terminate()
                    try:
                        existing_process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        print("Existing scraper process did not terminate gracefully. Forcing termination...")
                        existing_process.kill()
                    print("Existing scraper process stopped.")
                    time.sleep(5)

            # Prepare arguments for the new scraper process
            print(f"Starting a new scraper process for user {user_id}...")
            chat_names_str = ",".join(chat_names)  # Convert list to comma-separated string
            args = [
                "python3", "run_scraper.py",
                "--chatNames", chat_names_str,
                "--channelUsername", f'"{channel_username}"',
                "--userId", str(user_id)  # Pass user ID to the scraper
            ]

            # Start the new process
            new_process = subprocess.Popen(
                args, stdout=None, stderr=None, stdin=None, close_fds=True
            )
            user_scraper_processes[user_id] = new_process
            print(f"New scraper process started for user {user_id} with PID {new_process.pid}")

        except Exception as e:
            print(f"Error managing scraper process for user {user_id}: {e}")
            raise

def cleanup():
    global scraper_process
    if scraper_process and scraper_process.poll() is None:
        print("Stopping scraper process during cleanup...")
        scraper_process.terminate()
        scraper_process.wait(imeout=40)
        print("Scraper process stopped.")

# Register cleanup function
atexit.register(cleanup)

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

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if user and user.password == password:  # Replace with `check_password_hash` for hashed passwords
        login_user(user)
        return jsonify({'message': 'Login successful'}), 200
    return jsonify({'message': 'Invalid email or password'}), 401

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/is_logged_in', methods=['GET'])
def is_logged_in():
    if current_user.is_authenticated:
        return jsonify({'logged_in': True, 'email': current_user.email}), 200
    return jsonify({'logged_in': False}), 200

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'message': 'Email and password are required'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'User with this email already exists'}), 409

    try:
        new_user = User(email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'User registered successfully'}), 201
    except Exception as e:
        return jsonify({'message': 'An error occurred', 'error': str(e)}), 500

# Keep-alive endpoint
@app.route('/keep_alive', methods=['GET'])
def keep_alive():
    if 'user_id' in session:
        session.modified = True  # Refresh the session
        return jsonify({'message': 'Session kept alive'}), 200
    return jsonify({'message': 'No active session'}), 401

@login_required
@app.route('/scrape', methods=['POST', 'OPTIONS'])
def scrape():
    if request.method == 'OPTIONS':
        return jsonify({"message": "Preflight request handled"}), 200
    
    if 'user_id' not in session:
        return jsonify({"message": "Unauthorized"}), 401

    user_id = session['user_id']

    global scraper, cancel_event
    cancel_event.clear()

    data = request.json
    chat_names = data.get('chatNames', [])  # List of chat names
    date_limit = data.get('dateLimit')
    channel_username = data.get('channelUsername')
    scrape_all = data.get('scrapeAll', False)
    new_session = data.get('newWhatsAppSession', False)

    # Adjust channel_username for private and public channels
    if channel_username:
        if channel_username.replace("/", "").isdigit():  # If it's only numbers, prepend '-100' for private channel IDs
            channel_username = f"-100{channel_username}"
        elif not channel_username.startswith('@'):  # Otherwise, ensure it starts with '@' for public usernames
            channel_username = f"@{channel_username}"


    try:
        # Commenting out the TelegramPoster initialization
        telegram_poster = TelegramPoster(
            bot_token="7766870224:AAGwLCBlye9lPfxZeSWnJ9_Anji7LBmW_qs",
            channel_username=channel_username
        )
        print("TelegramPoster initialized")

        results = []
        for chat_name in chat_names:
            print(f"Skipping scrape for chat: {chat_name}")
            # Commenting out the actual scraping logic
            try:
                # Call the function to start `run_scraper.py`
                start_scraper(user_id, chat_names, channel_username)

                # Optionally, insert a record into the `scraping_sessions` table
                conn = sqlite3.connect('db.sqlite')
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO scraping_sessions (user_id, chat_names, channel_username, status) VALUES (?, ?, ?, ?)",
                    (user_id, ",".join(chat_names), channel_username, "running")
                )
                conn.commit()
                conn.close()

            except Exception as e:
                print(f"Error scraping chat '{chat_name}': {e}")

        # Return a placeholder response
        return jsonify({"message": "success", "results": results}), 200

    except Exception as e:
        print(f"Exception encountered: {e}")
        return jsonify({"message": f"Error: {str(e)}"}), 500

    finally:
        scraper = None

# Cancel scraping endpoint
@login_required        
@app.route('/cancel_scraping', methods=['POST'])
def cancel_scraping():
    global cancel_event, scraper
    if scraper is not None:
        cancel_event.set()  # Trigger the cancellation
        return jsonify({"message": "Scraping process cancelled successfully!"}), 200
    else:
        return jsonify({"message": "No scraping process is currently running."}), 400
    
@login_required
@app.route('/link_whatsapp', methods=['POST'])
def link_whatsapp():
    """
    Start a WhatsApp Web login session for a specific user.
    """
    if 'user_id' not in session:
        return jsonify({"message": "Unauthorized"}), 401

    user_id = session['user_id']

    try:
        print(f"[DEBUG] Received request to initiate WhatsApp login for user {user_id}.")

        # Define user-specific Chrome user data directory
        user_data_dir = f"chrome_user_data/user_{user_id}"
        os.makedirs(user_data_dir, exist_ok=True)

        # Initialize the WhatsAppLogin class with the user-specific directory
        whatsapp_login = WhatsAppLogin(user_data_dir=user_data_dir)

        # Verify that the VNC server is running
        vnc_server_check = subprocess.run(
            ["pgrep", "-x", "Xtigervnc"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if vnc_server_check.returncode != 0:
            error_msg = "[ERROR] VNC server is not running. Please ensure the VNC server is up and accessible."
            print(error_msg)
            return jsonify({"message": error_msg}), 500
        print("[DEBUG] VNC server is confirmed to be running.")

        # Start the WhatsApp login process in a new thread
        print(f"[DEBUG] Starting WhatsApp login process for user {user_id} in a new thread.")
        threading.Thread(target=whatsapp_login.open_whatsapp_web, daemon=True).start()

        # Prepare the VNC link for the user
        vnc_link = "http://34.132.58.174:8080/vnc.html"  # Update with your server IP or domain
        print(f"[DEBUG] Generated VNC link for user {user_id}: {vnc_link}")

        # Return the response with the VNC link
        return jsonify({
            "message": "WhatsApp login initiated. Use the link to complete login.",
            "vnc_link": vnc_link
        }), 200

    except Exception as e:
        # Log and return any exceptions
        error_message = f"[ERROR] Exception occurred while starting WhatsApp login for user {user_id}: {e}"
        print(error_message)
        return jsonify({"message": error_message}), 500

# Initialize the database
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000,debug=True)
