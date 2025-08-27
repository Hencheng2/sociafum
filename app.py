import sqlite3
import os
from datetime import datetime, timedelta, timezone
import random
import string
import json
import uuid
import base64
import re

from flask import Flask, render_template, Blueprint, request, redirect, url_for, g, flash, session, abort, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_moment import Moment
from functools import wraps

import config

app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', config.SECRET_KEY)
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'family_tree.db')

app.config['UPLOAD_FOLDER'] = os.path.join('static', 'Uploads')
app.config['PROFILE_PHOTOS_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'profile_photos')
app.config['POST_MEDIA_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'post_media')
app.config['REEL_MEDIA_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'reel_media')
app.config['STORY_MEDIA_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'story_media')
app.config['VOICE_NOTES_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'voice_notes')
app.config['CHAT_MEDIA_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'chat_media')
app.config['CHAT_BACKGROUND_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'chat_backgrounds')

for folder in [
    app.config['PROFILE_PHOTOS_FOLDER'],
    app.config['POST_MEDIA_FOLDER'],
    app.config['REEL_MEDIA_FOLDER'],
    app.config['STORY_MEDIA_FOLDER'],
    app.config['VOICE_NOTES_FOLDER'],
    app.config['CHAT_MEDIA_FOLDER'],
    app.config['CHAT_BACKGROUND_FOLDER']
]:
    os.makedirs(folder, exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg'}

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

moment = Moment(app)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def generate_unique_key():
    letters = random.choices(string.ascii_uppercase, k=2)
    numbers = random.choices(string.digits, k=2)
    key_chars = letters + numbers
    random.shuffle(key_chars)
    return "".join(key_chars)

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.executescript(f.read())
        
        cursor = db.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (config.ADMIN_USERNAME,))
        admin_exists = cursor.fetchone()

        if not admin_exists:
            admin_unique_key = generate_unique_key()
            hashed_admin_password = generate_password_hash(config.ADMIN_PASSWORD_RAW)
            cursor.execute(
                """
                INSERT INTO users (username, originalName, password_hash, unique_key, is_admin)
                VALUES (?, ?, ?, ?, ?)
                """,
                (config.ADMIN_USERNAME, "SociaFam Admin", hashed_admin_password, admin_unique_key, 1)
            )
            admin_user_id = cursor.lastrowid
            db.execute(
                """
                INSERT INTO members (user_id, fullName, gender)
                VALUES (?, ?, ?)
                """,
                (admin_user_id, "SociaFam Admin", "Prefer not to say")
            )
            app.logger.info(f"Admin user '{config.ADMIN_USERNAME}' created with unique key '{admin_unique_key}'.")
        else:
            app.logger.info(f"Admin user '{config.ADMIN_USERNAME}' already exists.")
        db.commit()
    app.logger.info("Database initialized/updated from schema.sql.")

app.teardown_appcontext(close_db)

with app.app_context():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
    if not cursor.fetchone():
        init_db()
    else:
        cursor.execute("SELECT id FROM users WHERE username = ?", (config.ADMIN_USERNAME,))
        if not cursor.fetchone():
            init_db()
    db.close()

class User(UserMixin):
    def __init__(self, id, username, password_hash, is_admin=0, theme_preference='light', chat_background_image_path=None, unique_key=None, password_reset_pending=0, reset_request_timestamp=None, last_login_at=None, last_seen_at=None, original_name=None, email=None):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.is_admin = bool(is_admin)
        self.theme_preference = theme_preference
        self.chat_background_image_path = chat_background_image_path
        self.unique_key = unique_key
        self.password_reset_pending = bool(password_reset_pending)
        self.reset_request_timestamp = reset_request_timestamp
        self.last_login_at = last_login_at
        self.last_seen_at = last_seen_at
        self.original_name = original_name
        self.email = email

    def get_id(self):
        return str(self.id)

    def get_member_profile(self):
        db = get_db()
        member_profile = db.execute('SELECT * FROM members WHERE user_id = ?', (self.id,)).fetchone()
        return member_profile

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    user_data = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if user_data:
        member_data = db.execute('SELECT email FROM members WHERE user_id = ?', (user_id,)).fetchone()
        email = member_data['email'] if member_data else None
        return User(
            id=user_data['id'],
            username=user_data['username'],
            password_hash=user_data['password_hash'],
            is_admin=user_data['is_admin'],
            theme_preference=user_data['theme_preference'],
            chat_background_image_path=user_data['chat_background_image_path'],
            unique_key=user_data['unique_key'],
            password_reset_pending=user_data['password_reset_pending'],
            reset_request_timestamp=user_data['reset_request_timestamp'],
            last_login_at=user_data['last_login_at'],
            last_seen_at=user_data['last_seen_at'],
            original_name=user_data['originalName'],
            email=email
        )
    return None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have administrative privileges to access this page.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_uploaded_file(file, upload_folder):
    if file and allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS.union(ALLOWED_VIDEO_EXTENSIONS).union(ALLOWED_AUDIO_EXTENSIONS)):
        filename = secure_filename(file.filename)
        unique_filename = str(uuid.uuid4()) + '_' + filename
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        return os.path.join('static', 'Uploads', os.path.basename(upload_folder), unique_filename)
    return None

def get_member_profile_pic(user_id):
    db = get_db()
    member = db.execute("SELECT profilePhoto FROM members WHERE user_id = ?", (user_id,)).fetchone()
    if member and member['profilePhoto']:
        if member['profilePhoto'].startswith('static/'):
            return url_for('static', filename=member['profilePhoto'][len('static/'):])
        return url_for('static', filename=member['profilePhoto'])
    return url_for('static', filename='img/default_profile.png')

def get_member_from_user_id(user_id):
    db = get_db()
    member = db.execute('SELECT * FROM members WHERE user_id = ?', (user_id,)).fetchone()
    return member

def get_user_from_member_id(member_id):
    db = get_db()
    user_id_row = db.execute('SELECT user_id FROM members WHERE id = ?', (member_id,)).fetchone()
    if user_id_row:
        return load_user(user_id_row['user_id'])
    return None

def process_mentions_and_links(text):
    db = get_db()
    def replace_mention(match):
        username = match.group(1)
        user = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if user:
            return f'<a href="{url_for("profile", username=username)}">@{username}</a>'
        return match.group(0)
    processed_text = re.sub(r'@([a-zA-Z0-9_]+)', replace_mention, text)
    url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
    def replace_url(match):
        url = match.group(0)
        if not url.startswith('http'):
            url = 'http://' + url
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{url}</a>'
    processed_text = re.sub(url_pattern, replace_url, processed_text)
    return processed_text

def get_relationship_status(current_id, other_id):
    db = get_db()
    friendship = db.execute(
        """
        SELECT status, user1_id FROM friendships
        WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
        """,
        (current_id, other_id, other_id, current_id)
    ).fetchone()
    if friendship:
        if friendship['status'] == 'accepted':
            return 'friend'
        elif friendship['status'] == 'pending':
            if friendship['user1_id'] == current_id:
                return 'pending_sent'
            else:
                return 'pending_received'
        else:
            return 'none'
    return 'none'

def is_blocked(blocker_id, blocked_id):
    db = get_db()
    blocked = db.execute(
        "SELECT id FROM blocked_users WHERE blocker_id = ? AND blocked_id = ?",
        (blocker_id, blocked_id)
    ).fetchone()
    return bool(blocked)

def get_mutual_friends_count(user1_id, user2_id):
    db = get_db()
    query = """
        SELECT COUNT(*) FROM (
            SELECT CASE WHEN user1_id = ? THEN user2_id ELSE user1_id END AS friend_id
            FROM friendships WHERE (user1_id = ? OR user2_id = ?) AND status = 'accepted'
            INTERSECT
            SELECT CASE WHEN user1_id = ? THEN user2_id ELSE user1_id END AS friend_id
            FROM friendships WHERE (user1_id = ? OR user2_id = ?) AND status = 'accepted'
        )
    """
    count = db.execute(query, (user1_id, user1_id, user1_id, user2_id, user2_id, user2_id)).fetchone()[0]
    return count

def send_system_notification(receiver_id, message, link=None, type='info'):
    db = get_db()
    try:
        db.execute(
            """
            INSERT INTO notifications (receiver_id, type, message, link, timestamp, is_read)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (receiver_id, type, message, link, datetime.now(timezone.utc))
        )
        db.commit()
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error sending notification to user {receiver_id}: {e}")

@app.route('/friends')
@login_required
def friends():
    db = get_db()

    all_friends_raw = db.execute(
        """
        SELECT u.id, m.fullName AS realName, u.username, m.profilePhoto
        FROM friendships f
        JOIN users u ON (f.user1_id = u.id OR f.user2_id = u.id)
        JOIN members m ON m.user_id = u.id
        WHERE (f.user1_id = ? OR f.user2_id = ?) AND f.status = 'accepted' AND u.id != ?
            AND u.id NOT IN (SELECT blocked_id FROM blocked_users WHERE blocker_id = ?)
        """,
        (current_user.id, current_user.id, current_user.id, current_user.id)
    ).fetchall()

    all_friends = []
    for friend in all_friends_raw:
        mutual_count = get_mutual_friends_count(current_user.id, friend['id'])
        all_friends.append(dict(friend, mutual_count=mutual_count, profilePhoto=get_member_profile_pic(friend['id'])))

    following_raw = db.execute(
        """
        SELECT u.id, m.fullName AS realName, u.username, m.profilePhoto
        FROM friendships f
        JOIN users u ON f.user2_id = u.id
        JOIN members m ON m.user_id = u.id
        WHERE f.user1_id = ? AND f.status = 'accepted'
            AND u.id NOT IN (SELECT blocked_id FROM blocked_users WHERE blocker_id = ?)
        """,
        (current_user.id, current_user.id)
    ).fetchall()

    following = []
    for user in following_raw:
        mutual_count = get_mutual_friends_count(current_user.id, user['id'])
        following.append(dict(user, mutual_count=mutual_count, profilePhoto=get_member_profile_pic(user['id'])))

    followers_raw = db.execute(
        """
        SELECT u.id, m.fullName AS realName, u.username, m.profilePhoto
        FROM friendships f
        JOIN users u ON f.user1_id = u.id
        JOIN members m ON m.user_id = u.id
        WHERE f.user2_id = ? AND f.status = 'accepted'
            AND u.id NOT IN (SELECT blocked_id FROM blocked_users WHERE blocker_id = ?)
        """,
        (current_user.id, current_user.id)
    ).fetchall()

    followers = []
    for user in followers_raw:
        mutual_count = get_mutual_friends_count(current_user.id, user['id'])
        followers.append(dict(user, mutual_count=mutual_count, profilePhoto=get_member_profile_pic(user['id'])))

    friend_requests_raw = db.execute(
        """
        SELECT f.id AS friendship_id, u.id AS sender_id, m.fullName AS sender_realName, u.username AS sender_username, m.profilePhoto
        FROM friendships f
        JOIN users u ON f.user1_id = u.id
        JOIN members m ON m.user_id = u.id
        WHERE f.user2_id = ? AND f.status = 'pending'
            AND u.id NOT IN (SELECT blocked_id FROM blocked_users WHERE blocker_id = ?)
        """,
        (current_user.id, current_user.id)
    ).fetchall()

    friend_requests = []
    for request in friend_requests_raw:
        mutual_count = get_mutual_friends_count(current_user.id, request['sender_id'])
        friend_requests.append(dict(request, mutual_count=mutual_count, profilePhoto=get_member_profile_pic(request['sender_id'])))

    suggested_users_raw = db.execute(
        """
        SELECT u.id, m.fullName AS realName, u.username, m.profilePhoto, COUNT(DISTINCT my_friend.id) AS mutual_count
        FROM users u
        JOIN members m ON m.user_id = u.id
        JOIN friendships f1 ON (f1.user1_id = ? OR f1.user2_id = ?) AND f1.status = 'accepted'
        JOIN users my_friend ON my_friend.id = CASE WHEN f1.user1_id = ? THEN f1.user2_id ELSE f1.user1_id END
        JOIN friendships f2 ON (f2.user1_id = my_friend.id OR f2.user2_id = my_friend.id) AND f2.status = 'accepted'
        WHERE u.id = CASE WHEN f2.user1_id = my_friend.id THEN f2.user2_id ELSE f2.user1_id END
            AND u.id != ?
            AND u.id NOT IN (
                SELECT CASE WHEN f.user1_id = ? THEN f.user2_id ELSE f.user1_id END
                FROM friendships f
                WHERE (f.user1_id = ? OR f.user2_id = ?) AND f.status IN ('accepted', 'pending')
            )
            AND u.id NOT IN (SELECT blocked_id FROM blocked_users WHERE blocker_id = ?)
            AND u.id NOT IN (SELECT dismissed_user_id FROM dismissed_suggestions WHERE user_id = ?)
        GROUP BY u.id
        HAVING mutual_count > 0
        ORDER BY mutual_count DESC
        LIMIT 10
        """,
        (current_user.id, current_user.id, current_user.id, current_user.id, current_user.id, current_user.id, current_user.id, current_user.id, current_user.id)
    ).fetchall()

    suggested_users = [dict(user, profilePhoto=get_member_profile_pic(user['id'])) for user in suggested_users_raw]

    return render_template(
        'friends.html',
        all_friends=all_friends,
        following=following,
        followers=followers,
        friend_requests=friend_requests,
        suggested_users=suggested_users
    )

@app.route('/api/search_users')
@login_required
def api_search_users():
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify([])

    db = get_db()
    users_raw = db.execute(
        """
        SELECT u.id, m.fullName AS realName, u.username, m.profilePhoto,
        CASE WHEN LOWER(m.fullName) LIKE ? THEN 0 ELSE 1 END AS sort_order
        FROM users u
        JOIN members m ON m.user_id = u.id
        WHERE (LOWER(m.fullName) LIKE ? OR LOWER(u.username) LIKE ?) AND u.id != ?
            AND u.id NOT IN (SELECT blocked_id FROM blocked_users WHERE blocker_id = ?)
        ORDER BY sort_order, LOWER(m.fullName), LOWER(u.username)
        """,
        (query + '%', query + '%', query + '%', current_user.id, current_user.id)
    ).fetchall()

    users = []
    for user in users_raw:
        mutual_count = get_mutual_friends_count(current_user.id, user['id'])
        status = get_relationship_status(current_user.id, user['id'])
        users.append({
            'id': user['id'],
            'realName': user['realName'],
            'username': user['username'],
            'profilePhoto': get_member_profile_pic(user['id']),
            'mutual_count': mutual_count,
            'status': status
        })

    return jsonify(users)

@app.route('/api/start_chat', methods=['POST'])
@login_required
def api_start_chat():
    user_id = request.json.get('user_id')
    if not user_id or user_id == current_user.id:
        return jsonify({'success': False, 'message': 'Invalid user to chat with.'}), 400

    db = get_db()
    try:
        # Check if user is blocked
        if is_blocked(current_user.id, user_id) or is_blocked(user_id, current_user.id):
            return jsonify({'success': False, 'message': 'Cannot start chat with this user.'}), 400

        # Check if a chat room already exists
        chat_room = db.execute(
            """
            SELECT cr.id
            FROM chat_rooms cr
            JOIN chat_room_members crm1 ON cr.id = crm1.chat_room_id
            JOIN chat_room_members crm2 ON cr.id = crm2.chat_room_id
            WHERE cr.is_group = 0
                AND crm1.user_id = ? AND crm2.user_id = ?
            """,
            (current_user.id, user_id)
        ).fetchone()

        if chat_room:
            return jsonify({'success': True, 'chat_url': url_for('messages', chat_room_id=chat_room['id'])})

        # Create a new chat room
        db.execute(
            "INSERT INTO chat_rooms (is_group, created_by, created_at) VALUES (?, ?, ?)",
            (0, current_user.id, datetime.now(timezone.utc))
        )
        chat_room_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Add both users to the chat room
        db.execute(
            "INSERT INTO chat_room_members (chat_room_id, user_id, joined_at) VALUES (?, ?, ?)",
            (chat_room_id, current_user.id, datetime.now(timezone.utc))
        )
        db.execute(
            "INSERT INTO chat_room_members (chat_room_id, user_id, joined_at) VALUES (?, ?, ?)",
            (chat_room_id, user_id, datetime.now(timezone.utc))
        )
        db.commit()
        return jsonify({'success': True, 'chat_url': url_for('messages', chat_room_id=chat_room_id)})
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error starting chat with user {user_id}: {e}")
        return jsonify({'success': False, 'message': 'Failed to start chat.'}), 500

@app.route('/api/block_user', methods=['POST'])
@login_required
def api_block_user():
    blocked_id = request.json.get('blocked_id')
    if not blocked_id or blocked_id == current_user.id:
        return jsonify({'success': False, 'message': 'Invalid user to block.'}), 400
    db = get_db()
    try:
        if not is_blocked(current_user.id, blocked_id):
            db.execute(
                "INSERT INTO blocked_users (blocker_id, blocked_id, timestamp) VALUES (?, ?, ?)",
                (current_user.id, blocked_id, datetime.now(timezone.utc))
            )
            # Remove any existing friendship
            db.execute(
                """
                DELETE FROM friendships
                WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
                """,
                (current_user.id, blocked_id, blocked_id, current_user.id)
            )
            db.commit()
            return jsonify({'success': True, 'message': 'User blocked.'})
        return jsonify({'success': False, 'message': 'User already blocked.'}), 400
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error blocking user: {e}")
        return jsonify({'success': False, 'message': 'Failed to block user.'}), 500

@app.route('/api/unfollow_user', methods=['POST'])
@login_required
def api_unfollow_user():
    user_id = request.json.get('user_id')
    if not user_id or user_id == current_user.id:
        return jsonify({'success': False, 'message': 'Invalid user to unfollow.'}), 400
    db = get_db()
    try:
        db.execute(
            """
            DELETE FROM friendships
            WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
                AND status = 'accepted'
            """,
            (current_user.id, user_id, user_id, current_user.id)
        )
        db.commit()
        return jsonify({'success': True, 'message': 'User unfollowed.'})
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error unfollowing user: {e}")
        return jsonify({'success': False, 'message': 'Failed to unfollow user.'}), 500

@app.route('/api/accept_friend_request', methods=['POST'])
@login_required
def api_accept_friend_request():
    friendship_id = request.json.get('friendship_id')
    if not friendship_id:
        return jsonify({'success': False, 'message': 'Invalid friend request.'}), 400
    db = get_db()
    try:
        friendship = db.execute(
            "SELECT user1_id, user2_id FROM friendships WHERE id = ? AND status = 'pending' AND user2_id = ?",
            (friendship_id, current_user.id)
        ).fetchone()
        if not friendship:
            return jsonify({'success': False, 'message': 'Friend request not found or not for you.'}), 404
        db.execute(
            "UPDATE friendships SET status = 'accepted', timestamp = ? WHERE id = ?",
            (datetime.now(timezone.utc), friendship_id)
        )
        sender = db.execute("SELECT username FROM users WHERE id = ?", (friendship['user1_id'],)).fetchone()
        send_system_notification(
            friendship['user1_id'],
            f"Your friend request to {current_user.username} was accepted.",
            url_for('profile', username=current_user.username),
            'friend_acceptance'
        )
        db.commit()
        return jsonify({'success': True, 'message': 'Friend request accepted.'})
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error accepting friend request: {e}")
        return jsonify({'success': False, 'message': 'Failed to accept friend request.'}), 500

@app.route('/api/decline_friend_request', methods=['POST'])
@login_required
def api_decline_friend_request():
    friendship_id = request.json.get('friendship_id')
    if not friendship_id:
        return jsonify({'success': False, 'message': 'Invalid friend request.'}), 400
    db = get_db()
    try:
        friendship = db.execute(
            "SELECT user1_id FROM friendships WHERE id = ? AND status = 'pending' AND user2_id = ?",
            (friendship_id, current_user.id)
        ).fetchone()
        if not friendship:
            return jsonify({'success': False, 'message': 'Friend request not found or not for you.'}), 404
        db.execute("DELETE FROM friendships WHERE id = ?", (friendship_id,))
        db.commit()
        return jsonify({'success': True, 'message': 'Friend request declined.'})
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error declining friend request: {e}")
        return jsonify({'success': False, 'message': 'Failed to decline friend request.'}), 500

@app.route('/api/follow_user', methods=['POST'])
@login_required
def api_follow_user():
    user_id = request.json.get('user_id')
    if not user_id or user_id == current_user.id:
        return jsonify({'success': False, 'message': 'Invalid user to follow.'}), 400
    db = get_db()
    try:
        if is_blocked(current_user.id, user_id) or is_blocked(user_id, current_user.id):
            return jsonify({'success': False, 'message': 'Cannot follow this user.'}), 400
        existing = db.execute(
            """
            SELECT id FROM friendships
            WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
            """,
            (current_user.id, user_id, user_id, current_user.id)
        ).fetchone()
        if existing:
            return jsonify({'success': False, 'message': 'Friend request already exists or user is already followed.'}), 400
        db.execute(
            "INSERT INTO friendships (user1_id, user2_id, status, timestamp) VALUES (?, ?, 'pending', ?)",
            (current_user.id, user_id, datetime.now(timezone.utc))
        )
        receiver = db.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
        send_system_notification(
            user_id,
            f"{current_user.username} sent you a friend request.",
            url_for('profile', username=current_user.username),
            'friend_request'
        )
        db.commit()
        return jsonify({'success': True, 'message': 'Friend request sent.'})
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error following user: {e}")
        return jsonify({'success': False, 'message': 'Failed to follow user.'}), 500

@app.route('/api/remove_suggested_user', methods=['POST'])
@login_required
def api_remove_suggested_user():
    dismissed_user_id = request.json.get('dismissed_user_id')
    if not dismissed_user_id or dismissed_user_id == current_user.id:
        return jsonify({'success': False, 'message': 'Invalid user to remove.'}), 400
    db = get_db()
    try:
        existing = db.execute(
            "SELECT id FROM dismissed_suggestions WHERE user_id = ? AND dismissed_user_id = ?",
            (current_user.id, dismissed_user_id)
        ).fetchone()
        if existing:
            return jsonify({'success': False, 'message': 'User already removed from suggestions.'}), 400
        db.execute(
            "INSERT INTO dismissed_suggestions (user_id, dismissed_user_id, timestamp) VALUES (?, ?, ?)",
            (current_user.id, dismissed_user_id, datetime.now(timezone.utc))
        )
        db.commit()
        return jsonify({'success': True, 'message': 'User removed from suggestions.'})
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error removing suggested user: {e}")
        return jsonify({'success': False, 'message': 'Failed to remove suggested user.'}), 500

@app.route('/api/admin/ban_user/<int:user_id>', methods=['POST'])
@admin_required
def api_admin_ban_user(user_id):
    db = get_db()
    reason = request.json.get('reason', 'Violation of community guidelines.')
    duration = request.json.get('duration', 'permanent')
    ban_ends_at = None
    ban_status = duration
    if duration == 'temporary':
        days = request.json.get('days', 7)
        if not isinstance(days, int) or days < 1:
            return jsonify({'success': False, 'message': 'Valid number of days is required for temporary ban.'}), 400
        ban_ends_at = datetime.now(timezone.utc) + timedelta(days=days)
    try:
        db.execute(
            "UPDATE users SET ban_status = ?, ban_reason = ?, ban_starts_at = ?, ban_ends_at = ? WHERE id = ?",
            (ban_status, reason, datetime.now(timezone.utc), ban_ends_at, user_id)
        )
        db.commit()
        send_system_notification(
            user_id,
            f'Your account has been {ban_status}ly banned. Reason: {reason}.',
            link=url_for('account_status'),
            type='danger'
        )
        return jsonify({'success': True, 'message': 'User banned successfully.'})
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error banning user: {e}")
        return jsonify({'success': False, 'message': 'Failed to ban user.'}), 500

@app.route('/api/admin/unban_user/<int:user_id>', methods=['POST'])
@admin_required
def api_admin_unban_user(user_id):
    db = get_db()
    try:
        db.execute(
            "UPDATE users SET ban_status = 'none', ban_reason = NULL, ban_starts_at = NULL, ban_ends_at = NULL WHERE id = ?",
            (user_id,)
        )
        db.commit()
        send_system_notification(
            user_id,
            'Your account ban has been lifted. You can now access all features.',
            link=url_for('home'),
            type='info'
        )
        return jsonify({'success': True, 'message': 'User unbanned successfully.'})
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error unbanning user: {e}")
        return jsonify({'success': False, 'message': 'Failed to unban user.'}), 500

@app.route('/api/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def api_admin_delete_user(user_id):
    db = get_db()
    try:
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()
        return jsonify({'success': True, 'message': 'User account and all associated data deleted permanently.'})
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error deleting user {user_id}: {e}")
        return jsonify({'success': False, 'message': 'Failed to delete user.'}), 500

@app.route('/api/admin/ban_group/<int:group_id>', methods=['POST'])
@admin_required
def api_admin_ban_group(group_id):
    db = get_db()
    reason = request.json.get('reason', 'Violation of community guidelines.')
    duration = request.json.get('duration', 'permanent')
    ban_ends_at = None
    ban_status = duration
    if duration == 'temporary':
        days = request.json.get('days', 7)
        if not isinstance(days, int) or days < 1:
            return jsonify({'success': False, 'message': 'Valid number of days is required for temporary ban.'}), 400
        ban_ends_at = datetime.now(timezone.utc) + timedelta(days=days)
    try:
        db.execute(
            "UPDATE groups SET ban_status = ?, ban_reason = ?, ban_starts_at = ?, ban_ends_at = ? WHERE id = ?",
            (ban_status, reason, datetime.now(timezone.utc), ban_ends_at, group_id)
        )
        db.commit()
        group = db.execute("SELECT name, chat_room_id FROM groups WHERE id = ?", (group_id,)).fetchone()
        if group:
            members = db.execute("SELECT user_id FROM chat_room_members WHERE chat_room_id = ?", (group['chat_room_id'],)).fetchall()
            for member in members:
                message = f'The group "<strong>{group["name"]}</strong>" has been {ban_status}ly banned. Reason: {reason}.'
                send_system_notification(
                    member['user_id'],
                    message,
                    link=url_for('home'),
                    type='danger'
                )
        return jsonify({'success': True, 'message': 'Group banned successfully.'})
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error banning group: {e}")
        return jsonify({'success': False, 'message': 'Failed to ban group.'}), 500

@app.route('/api/admin/unban_group/<int:group_id>', methods=['POST'])
@admin_required
def api_admin_unban_group(group_id):
    db = get_db()
    try:
        db.execute(
            "UPDATE groups SET ban_status = 'none', ban_reason = NULL, ban_starts_at = NULL, ban_ends_at = NULL WHERE id = ?",
            (group_id,)
        )
        db.commit()
        group = db.execute("SELECT name, chat_room_id FROM groups WHERE id = ?", (group_id,)).fetchone()
        if group:
            members = db.execute("SELECT user_id FROM chat_room_members WHERE chat_room_id = ?", (group['chat_room_id'],)).fetchall()
            for member in members:
                message = f'The ban on group "<strong>{group["name"]}</strong>" has been lifted. You can now access it.'
                send_system_notification(
                    member['user_id'],
                    message,
                    link=url_for('view_group_profile', group_id=group_id),
                    type='info'
                )
        return jsonify({'success': True, 'message': 'Group unbanned successfully.'})
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error unbanning group: {e}")
        return jsonify({'success': False, 'message': 'Failed to unban group.'}), 500

@app.route('/api/admin/delete_group/<int:group_id>', methods=['POST'])
@admin_required
def api_admin_delete_group(group_id):
    db = get_db()
    try:
        group_chat_room_id = db.execute("SELECT chat_room_id FROM groups WHERE id = ?", (group_id,)).fetchone()
        if not group_chat_room_id:
            return jsonify({'success': False, 'message': 'Group not found.'}), 404
        db.execute("DELETE FROM groups WHERE id = ?", (group_id,))
        db.execute("DELETE FROM chat_rooms WHERE id = ?", (group_chat_room_id['chat_room_id'],))
        db.commit()
        return jsonify({'success': True, 'message': 'Group and all associated data deleted permanently.'})
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error deleting group {group_id}: {e}")
        return jsonify({'success': False, 'message': 'Failed to delete group.'}), 500

@app.route('/api/admin/handle_report/<int:report_id>/<action>', methods=['POST'])
@admin_required
def api_admin_handle_report(report_id, action):
    db = get_db()
    report = db.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    if not report:
        return jsonify({'success': False, 'message': 'Report not found.'}), 404

    reported_item_id = report['reported_item_id']
    reported_item_type = report['reported_item_type']
    report_reason = report['reason']

    try:
        if action == 'warn':
            if reported_item_type == 'user':
                db.execute(
                    "INSERT INTO warnings (user_id, title, description, timestamp, status) VALUES (?, ?, ?, ?, 'active')",
                    (reported_item_id, 'Reported Content Violation', f'User reported for: {report_reason}', datetime.now(timezone.utc))
                )
                send_system_notification(
                    reported_item_id,
                    f'You received a warning due to a report: {report_reason[:50]}...',
                    link=url_for('account_status'),
                    type='warning'
                )
            db.execute("UPDATE reports SET status = 'handled', admin_notes = ? WHERE id = ?", ('Warned user/item.', report_id))
            db.commit()
            return jsonify({'success': True, 'message': 'Report handled: item warned.'})

        elif action == 'ban':
            if reported_item_type == 'user':
                db.execute(
                    "UPDATE users SET ban_status = 'permanent', ban_reason = ?, ban_starts_at = ? WHERE id = ?",
                    (f'Banned due to report: {report_reason}', datetime.now(timezone.utc), reported_item_id)
                )
                send_system_notification(
                    reported_item_id,
                    f'Your account has been permanently banned due to a report: {report_reason[:50]}...',
                    link=url_for('account_status'),
                    type='danger'
                )
            elif reported_item_type == 'group':
                db.execute(
                    "UPDATE groups SET ban_status = 'permanent', ban_reason = ?, ban_starts_at = ? WHERE id = ?",
                    (f'Banned due to report: {report_reason}', datetime.now(timezone.utc), reported_item_id)
                )
                group = db.execute("SELECT name, chat_room_id FROM groups WHERE id = ?", (reported_item_id,)).fetchone()
                if group:
                    members = db.execute("SELECT user_id FROM chat_room_members WHERE chat_room_id = ?", (group['chat_room_id'],)).fetchall()
                    for member in members:
                        message = f'The group "<strong>{group["name"]}</strong>" has been permanently banned due to a report.'
                        send_system_notification(member['user_id'], message, link=url_for('home'), type='danger')
            db.execute("UPDATE reports SET status = 'handled', admin_notes = ? WHERE id = ?", ('Banned user/item.', report_id))
            db.commit()
            return jsonify({'success': True, 'message': 'Report handled: item banned.'})

        elif action == 'ignore':
            db.execute("UPDATE reports SET status = 'ignored', admin_notes = ? WHERE id = ?", ('No action taken.', report_id))
            db.commit()
            return jsonify({'success': True, 'message': 'Report ignored.'})

        else:
            return jsonify({'success': False, 'message': 'Invalid action for report handling.'}), 400

    except Exception as e:
        db.rollback()
        app.logger.error(f"Error handling report {report_id} with action {action}: {e}")
        return jsonify({'success': False, 'message': 'Failed to handle report.'}), 500

@app.route('/api/admin/broadcast_message', methods=['POST'])
@admin_required
def api_admin_broadcast_message():
    db = get_db()
    message_content = request.json.get('message')
    if not message_content:
        return jsonify({'success': False, 'message': 'Broadcast message cannot be empty.'}), 400
    try:
        all_users = db.execute("SELECT id FROM users WHERE is_admin = 0").fetchall()
        for user in all_users:
            send_system_notification(
                user['id'],
                f'<strong>SociaFam Update:</strong> {message_content}',
                link=url_for('notifications'),
                type='system_message'
            )
        db.commit()
        return jsonify({'success': True, 'message': 'Broadcast message sent to all users.'})
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error broadcasting message: {e}")
        return jsonify({'success': False, 'message': 'Failed to send broadcast message.'}), 500

@app.route('/api/admin/post_sociafam_story', methods=['POST'])
@admin_required
def api_admin_post_sociafam_story():
    db = get_db()
    media_file = request.files.get('mediaFile')
    description = request.form.get('description', '').strip()
    if not media_file or media_file.filename == '':
        return jsonify({'success': False, 'message': 'Media file is required for SociaFam Story.'}), 400
    media_path = save_uploaded_file(media_file, app.config['STORY_MEDIA_FOLDER'])
    if not media_path:
        return jsonify({'success': False, 'message': 'Invalid media file type for SociaFam Story.'}), 400
    media_type = None
    if media_file.filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS:
        media_type = 'image'
    elif media_file.filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS:
        media_type = 'video'
    else:
        return jsonify({'success': False, 'message': 'Unsupported media type.'}), 400
    try:
        admin_user = db.execute("SELECT id FROM users WHERE username = ?", (config.ADMIN_USERNAME,)).fetchone()
        if not admin_user:
            return jsonify({'success': False, 'message': 'Admin user for story posting not found.'}), 500
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        db.execute(
            """
            INSERT INTO stories (user_id, description, media_path, media_type, visibility, timestamp, expires_at, is_sociafam_story)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (admin_user['id'], description, media_path, media_type, 'public', datetime.now(timezone.utc), expires_at, 1)
        )
        db.commit()
        return jsonify({'success': True, 'message': 'SociaFam Story posted successfully!'})
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error posting SociaFam Story: {e}")
        return jsonify({'success': False, 'message': 'Failed to post SociaFam Story.'}), 500

@app.errorhandler(404)
def page_not_found(e):
    flash('The page you requested could not be found.', 'danger')
    return redirect(url_for('home'))

@app.errorhandler(403)
def forbidden(e):
    flash('You do not have permission to access this resource.', 'danger')
    return redirect(url_for('home'))

if __name__ == '__main__':
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        if not cursor.fetchone():
            init_db()
        else:
            cursor.execute("SELECT id FROM users WHERE username = ?", (config.ADMIN_USERNAME,))
            if not cursor.fetchone():
                init_db()
        db.close()
    app.run(debug=True)
