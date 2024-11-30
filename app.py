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
from werkzeug.security import check_password_hash

app = Flask(__name__, static_folder='static', static_url_path='/')
app.config.from_object(Config)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "http://localhost:3000"}})

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
    global scraper
    if scraper and scraper.poll() is None:
        print("Stopping scraper process during cleanup...")
        scraper.terminate()
        scraper.wait(timeout=40)
        print("Scraper process stopped.")


# Register cleanup function
atexit.register(cleanup)


@app.route('/<path:path>')
def serve_static_file(path):
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')


@app.errorhandler(404)
def handle_404(e):
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
    if user and check_password_hash(user.password, password):
        login_user(user)
        print(f"[DEBUG] Session data: {session}")  # Debugging session creation
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
    print(f"[DEBUG] Cookies in request: {request.cookies}")
    print(f"[DEBUG] Current session: {session}")
    print(f"[DEBUG] Current user authenticated: {current_user.is_authenticated}")
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


@app.route('/scrape', methods=['POST'])
@login_required
def scrape():
    global scraper, cancel_event
    cancel_event.clear()
    data = request.json
    chat_names = data.get('chatNames', [])
    channel_username = data.get('channelUsername')
    # Adjust channel_username for private and public channels
    if channel_username:
        if channel_username.replace("/", "").isdigit():  # If it's only numbers, prepend '-100' for private channel IDs
            channel_username = f"-100{channel_username}"
        elif not channel_username.startswith('@'):  # Otherwise, ensure it starts with '@' for public usernames
            channel_username = f"@{channel_username}"
    try:
        results = []
        for chat_name in chat_names:
            print(f"Skipping scrape for chat: {chat_name}")
            # Commenting out the actual scraping logic
            try:
                # Call the function to start `run_scraper.py`
                start_scraper(current_user.id, chat_names, channel_username)

            except Exception as e:
                print(f"Error scraping chat '{chat_name}': {e}")

        # Return a placeholder response
        return jsonify({"message": "success", "results": results}), 200

    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500


@app.route('/cancel_scraping', methods=['POST'])
@login_required
def cancel_scraping():
    global cancel_event, scraper
    if scraper is not None:
        cancel_event.set()
        return jsonify({'message': 'Scraping process cancelled successfully!'}), 200
    return jsonify({'message': 'No scraping process is currently running.'}), 400


@app.route('/link_whatsapp', methods=['POST'])
@login_required
def link_whatsapp():
    try:
        user_id = current_user.id
        user_data_dir = f"chrome_user_data/user_{user_id}"
        os.makedirs(user_data_dir, exist_ok=True)
        whatsapp_login = WhatsAppLogin(user_data_dir=user_data_dir)
        threading.Thread(target=whatsapp_login.open_whatsapp_web, daemon=True).start()
        return jsonify({
            "message": "WhatsApp login initiated. Use the link to complete login.",
            "vnc_link": "http://34.132.58.174:8080/vnc.html"  # Replace with your actual server
        }), 200
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
