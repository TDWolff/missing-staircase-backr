
from flask import Blueprint, request, jsonify, make_response
import sqlcipher3.dbapi2 as sqlite3
from werkzeug.security import generate_password_hash, check_password_hash


import os
import secrets
import re
from flask import current_app
from functools import wraps

login_bp = Blueprint('login', __name__)


# Path to users.db in the volumes folder
DB_PATH = os.path.join(os.path.dirname(__file__), 'volumes', 'users.db')
DB_PASSWORD = os.getenv('DB_PASSWORD')

def get_db_connection():
    if not DB_PASSWORD:
        raise RuntimeError("DB_PASSWORD is not set in environment variables!")
    conn = sqlite3.connect(DB_PATH)
    conn.execute(f"PRAGMA key='{DB_PASSWORD}'")
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usr_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        user_id TEXT UNIQUE NOT NULL,
        role TEXT NOT NULL DEFAULT 'User'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
        session_token TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        expires_at INTEGER NOT NULL
    )''')
    conn.commit()
    conn.close()
import hashlib
import random
import string
def generate_user_id(username):
    # Use a hash of the username and some random salt to ensure uniqueness and randomness
    salt = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    base = username + salt
    hash_val = hashlib.sha256(base.encode()).hexdigest().upper()
    # Take 12 alphanumeric chars from the hash, format as xxxx-xxxx-xxxx
    user_id_raw = ''.join([c for c in hash_val if c.isalnum()])[:12]
    return f"{user_id_raw[:4]}-{user_id_raw[4:8]}-{user_id_raw[8:12]}"

# Ensure DB/table exists on import
init_db()




def is_valid_username(username):
    # Username: 3-32 chars, alphanumeric and underscores only
    return bool(re.fullmatch(r"[A-Za-z0-9_]{3,32}", username))

def is_strong_password(password):
    # Password: min 8 chars, at least 1 digit, 1 upper, 1 lower, 1 special
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[^A-Za-z0-9]", password):
        return False
    return True

@login_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Username Or Password Incorrect'}), 401
    # Check credentials
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT password_hash, user_id FROM usr_data WHERE username=?', (username,))
    row = c.fetchone()
    if row and check_password_hash(row[0], password):
        user_id = row[1]
        # Generate a secure session token
        session_token = secrets.token_urlsafe(64)
        # Set expiry (1 week from now)
        import time
        expires_at = int(time.time()) + 60*60*24*7
        # Store session in DB
        c.execute('INSERT INTO sessions (session_token, user_id, expires_at) VALUES (?, ?, ?)', (session_token, user_id, expires_at))
        conn.commit()
        conn.close()
        resp = make_response('', 202)
        resp.set_cookie(
            'session',
            session_token,
            httponly=True,
            secure=True,
            samesite='None',
            max_age=60*60*24*7
        )
        # Set a non-HttpOnly cookie for frontend JS to read login state
        resp.set_cookie(
            'loggedIn',
            'true',
            httponly=False,
            secure=True,
            samesite='None',
            max_age=60*60*24*7
        )
        return resp
    conn.close()
    # Always return generic error
    return jsonify({'error': 'Username Or Password Incorrect'}), 401
# Logout endpoint to clear the session cookie and remove session from DB
@login_bp.route('/logout', methods=['POST'])
def logout():
    session_token = request.cookies.get('session')
    if session_token:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('DELETE FROM sessions WHERE session_token=?', (session_token,))
        conn.commit()
        conn.close()
    resp = make_response('', 204)
    resp.set_cookie('session', '', expires=0, httponly=True, secure=True, samesite='None')
    # Set loggedIn to false and expire it
    resp.set_cookie('loggedIn', 'false', expires=0, httponly=False, secure=True, samesite='None')
    return resp
# Helper to get current user from session cookie
def get_current_user():
    session_token = request.cookies.get('session')
    if not session_token:
        return None
    import time
    now = int(time.time())
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT user_id, expires_at FROM sessions WHERE session_token=?', (session_token,))
    row = c.fetchone()
    conn.close()
    if row and row[1] > now:
        return row[0]  # user_id
    return None

@login_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json(silent=True) or {}
    username = data.get('username')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    # Input validation
    if not (username and password and confirm_password):
        return jsonify({'error': 'Invalid signup data'}), 400
    if not is_valid_username(username):
        return jsonify({'error': 'Invalid signup data'}), 400
    if not is_strong_password(password):
        return jsonify({'error': 'Invalid signup data'}), 400
    if password != confirm_password:
        return jsonify({'error': 'Invalid signup data'}), 400
    # Hash the password with explicit method
    password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
    # Generate unique user_id
    user_id = generate_user_id(username)
    # Insert user into DB
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('INSERT INTO usr_data (username, password_hash, user_id) VALUES (?, ?, ?)', (username, password_hash, user_id))
        conn.commit()
        conn.close()
        return '', 202  # Accepted
    except sqlite3.IntegrityError:
        # Always return generic error
        return jsonify({'error': 'Invalid signup data'}), 400

# Now using SQLCipher for encrypted DB access with password set above.
