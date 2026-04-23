
from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash
import re
from login import get_current_user, get_db_connection

profile_bp = Blueprint('profile', __name__)

# Change password endpoint
@profile_bp.route('/change-password', methods=['POST', 'OPTIONS'])
def change_password():
    if request.method == 'OPTIONS':
        return '', 204
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    data = None
    try:
        data = (request.get_json(silent=True) or {})
    except Exception:
        return jsonify({'error': 'Invalid request'}), 400
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    if not old_password or not new_password:
        return jsonify({'error': 'Missing password fields'}), 400
    # Check new password strength (reuse login.py logic if possible)
    def is_strong_password(password):
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
    if not is_strong_password(new_password):
        return jsonify({'error': 'New password is not strong enough'}), 400
    # Fetch user and check old password
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT password_hash FROM usr_data WHERE user_id=?', (user_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    if not check_password_hash(row[0], old_password):
        conn.close()
        return jsonify({'error': 'Old password is incorrect'}), 401
    # Update password
    new_hash = generate_password_hash(new_password, method='pbkdf2:sha256', salt_length=16)
    c.execute('UPDATE usr_data SET password_hash=? WHERE user_id=?', (new_hash, user_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Password changed successfully'}), 200


@profile_bp.route('/profile', methods=['GET', 'OPTIONS'])
def profile():
    if request.method == 'OPTIONS':
        return '', 204
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT username, role FROM usr_data WHERE user_id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'User not found'}), 404
    username, role = row
    return jsonify({'username': username, 'role': role}), 200
