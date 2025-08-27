import sqlite3
import os
from datetime import datetime, timedelta, timezone
import random
import string
import json
import uuid # Import uuid for generating unique IDs
import base64 # Needed for base64 decoding camera/voice note data
import re # Needed for process_mentions_and_links

# Removed: import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore, initialize_app # initialize_app is needed if credentials path exists

from flask import Flask, render_template, Blueprint, request, redirect, url_for, g, flash, session, abort, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash # Corrected: Removed extra 'werk'
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_moment import Moment
from functools import wraps # For admin_required decorator

import config # Your configuration file

app = Flask(__name__)

# Use environment variable for SECRET_KEY or fall back to config.py
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', config.SECRET_KEY)

# Database path
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'family_tree.db')

# Upload folders configuration
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads') # General upload folder
app.config['PROFILE_PHOTOS_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'profile_photos')
app.config['POST_MEDIA_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'post_media')
app.config['REEL_MEDIA_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'reel_media')
app.config['STORY_MEDIA_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'story_media')
app.config['VOICE_NOTES_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'voice_notes')
app.config['CHAT_MEDIA_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'chat_media')
app.config['CHAT_BACKGROUND_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'chat_backgrounds')

# Ensure upload directories exist
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

# Allowed extensions for uploads
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg'}

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect to login page if user is not authenticated

# Initialize Flask-Moment for date/time formatting
moment = Moment(app) # Use Moment object

# --- Firebase Admin SDK Initialization ---
# Only initialize if firebase_admin_key.json exists and is valid.
# No active Firestore/Storage operations are implemented in user-facing routes as per user's request.
db_firestore = None # Initialize to None by default
if config.FIREBASE_ADMIN_CREDENTIALS_PATH and os.path.exists(config.FIREBASE_ADMIN_CREDENTIALS_PATH):
    try:
        # Check if Firebase app is already initialized to prevent re-initialization
        if not firebase_admin._apps:
            cred = credentials.Certificate(config.FIREBASE_ADMIN_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred, {
                'projectId': config.FIREBASE_CLIENT_CONFIG['projectId'],
                'storageBucket': config.FIREBASE_CLIENT_CONFIG['storageBucket']
            })
            # db_firestore = firestore.client() # Firestore client not actively used for data ops
            app.logger.info("Firebase Admin SDK initialized successfully.")
        else:
            app.logger.info("Firebase Admin SDK already initialized.")
    except Exception as e:
        app.logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
else:
    app.logger.warning("Firebase Admin SDK credentials file not found or path not configured. Firebase Admin SDK not initialized.")

# --- Database Helper Functions ---
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row # Return rows as dict-like objects
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- User Loader for Flask-Login ---
class User(UserMixin):
    def __init__(self, id, username, email, is_admin=False):
        self.id = id
        self.username = username
        self.email = email
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    user = db.execute("SELECT id, username, email, is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
    if user:
        return User(user['id'], user['username'], user['email'], user['is_admin'])
    return None

# --- Helper Functions ---
def allowed_file(filename):
    allowed_extensions = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS | ALLOWED_AUDIO_EXTENSIONS
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_uploaded_file(file, upload_folder):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        return file_path
    return None

def get_member_profile_pic(user_id):
    db = get_db()
    member = db.execute("SELECT profilePhoto FROM members WHERE user_id = ?", (user_id,)).fetchone()
    return member['profilePhoto'] if member and member['profilePhoto'] else url_for('static', filename='img/default_profile.png')

def send_system_notification(user_id, message, link=None, type='system'):
    db = get_db()
    db.execute(
        "INSERT INTO notifications (user_id, message, link, type, timestamp) VALUES (?, ?, ?, ?, ?)",
        (user_id, message, link, type, datetime.now(timezone.utc))
    )
    db.commit()

def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()
    # Create admin user
    admin_password = generate_password_hash(config.ADMIN_PASSWORD)
    db.execute(
        "INSERT INTO users (username, email, password, is_admin, created_at) VALUES (?, ?, ?, ?, ?)",
        (config.ADMIN_USERNAME, config.ADMIN_EMAIL, admin_password, 1, datetime.now(timezone.utc))
    )
    db.execute(
        "INSERT INTO members (user_id, fullName, dateOfBirth, gender) VALUES ((SELECT id FROM users WHERE username = ?), ?, ?, ?)",
        (config.ADMIN_USERNAME, 'SociaFam Admin', '1970-01-01', 'Other')
    )
    db.commit()

# --- Admin Required Decorator ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@app.route('/')
def home():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    db = get_db()
    stories = db.execute("""
        SELECT s.*, u.username
        FROM stories s
        JOIN users u ON s.user_id = u.id
        WHERE s.expires_at > ? AND s.visibility = 'public'
        ORDER BY s.timestamp DESC
    """, (datetime.now(timezone.utc),)).fetchall()
    posts = db.execute("""
        SELECT p.*, m.fullName as user_real_name, m.profilePhoto as user_profile_photo, u.username
        FROM posts p
        JOIN members m ON p.user_id = m.user_id
        JOIN users u ON p.user_id = u.id
        WHERE p.visibility IN ('public', 'friends')
        ORDER BY p.timestamp DESC
        LIMIT 10
    """).fetchall()
    return render_template('index.html', stories=stories, posts=posts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user['password'], password):
            user_obj = User(user['id'], user['username'], user['email'], user['is_admin'])
            login_user(user_obj)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('fullName')
        date_of_birth = request.form.get('dateOfBirth')
        gender = request.form.get('gender')
        db = get_db()
        try:
            hashed_password = generate_password_hash(password)
            db.execute(
                "INSERT INTO users (username, email, password, created_at) VALUES (?, ?, ?, ?)",
                (username, email, hashed_password, datetime.now(timezone.utc))
            )
            user_id = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()['id']
            db.execute(
                "INSERT INTO members (user_id, fullName, dateOfBirth, gender) VALUES (?, ?, ?, ?)",
                (user_id, full_name, date_of_birth, gender)
            )
            db.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            db.rollback()
            flash('Username or email already exists.', 'danger')
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/profile/<username>')
@login_required
def profile(username):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('home'))
    member = db.execute("SELECT * FROM members WHERE user_id = ?", (user['id'],)).fetchone()
    posts = db.execute("SELECT * FROM posts WHERE user_id = ? AND visibility IN ('public', 'friends') ORDER BY timestamp DESC", (user['id'],)).fetchall()
    return render_template('profile.html', user=user, member=member, posts=posts)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    db = get_db()
    member = db.execute("SELECT * FROM members WHERE user_id = ?", (current_user.id,)).fetchone()
    if request.method == 'POST':
        full_name = request.form.get('fullName')
        date_of_birth = request.form.get('dateOfBirth')
        gender = request.form.get('gender')
        profile_photo = request.files.get('profilePhoto')
        try:
            profile_photo_path = None
            if profile_photo and allowed_file(profile_photo.filename):
                profile_photo_path = save_uploaded_file(profile_photo, app.config['PROFILE_PHOTOS_FOLDER'])
            db.execute(
                """
                UPDATE members
                SET fullName = ?, dateOfBirth = ?, gender = ?, profilePhoto = COALESCE(?, profilePhoto)
                WHERE user_id = ?
                """,
                (full_name, date_of_birth, gender, profile_photo_path, current_user.id)
            )
            db.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile', username=current_user.username))
        except Exception as e:
            db.rollback()
            flash(f'Failed to update profile: {e}', 'danger')
    return render_template('edit_profile.html', member=member)

@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        description = request.form.get('description')
        media_file = request.files.get('mediaFile')
        visibility = request.form.get('visibility', 'public')
        db = get_db()
        try:
            media_path = None
            media_type = None
            if media_file and allowed_file(media_file.filename):
                media_path = save_uploaded_file(media_file, app.config['POST_MEDIA_FOLDER'])
                if media_file.filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS:
                    media_type = 'image'
                elif media_file.filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS:
                    media_type = 'video'
            db.execute(
                """
                INSERT INTO posts (user_id, description, media_path, media_type, visibility, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (current_user.id, description, media_path, media_type, visibility, datetime.now(timezone.utc))
            )
            db.commit()
            flash('Post created successfully!', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            db.rollback()
            flash(f'Failed to create post: {e}', 'danger')
    return render_template('create_post.html')

@app.route('/create_story', methods=['GET', 'POST'])
@login_required
def create_story():
    if request.method == 'POST':
        media_file = request.files.get('mediaFile')
        description = request.form.get('description', '').strip()
        visibility = request.form.get('visibility', 'public')
        if not media_file or media_file.filename == '':
            flash('Media file is required for stories.', 'danger')
            return redirect(url_for('create_story'))
        media_path = save_uploaded_file(media_file, app.config['STORY_MEDIA_FOLDER'])
        if not media_path:
            flash('Invalid media file type.', 'danger')
            return redirect(url_for('create_story'))
        media_type = None
        if media_file.filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS:
            media_type = 'image'
        elif media_file.filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS:
            media_type = 'video'
        elif media_file.filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS:
            media_type = 'audio'
        else:
            flash('Unsupported media type.', 'danger')
            return redirect(url_for('create_story'))
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
            db.execute(
                """
                INSERT INTO stories (user_id, description, media_path, media_type, visibility, timestamp, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (current_user.id, description, media_path, media_type, visibility, datetime.now(timezone.utc), expires_at)
            )
            db.commit()
            flash('Story created successfully!', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            db.rollback()
            flash(f'Failed to create story: {e}', 'danger')
    return render_template('create_story.html')

@app.route('/friends')
@login_required
def friends():
    db = get_db()
    followers = db.execute("""
        SELECT u.id, u.username, m.fullName AS realName, m.profilePhoto, 
               (SELECT COUNT(*) FROM friendships f2 WHERE f2.user2_id = u.id AND f2.status = 'accepted' AND f2.user1_id IN 
                 (SELECT user2_id FROM friendships WHERE user1_id = ? AND status = 'accepted')) AS mutual_count
        FROM friendships f
        JOIN users u ON f.user1_id = u.id
        JOIN members m ON u.id = m.user_id
        WHERE f.user2_id = ? AND f.status = 'accepted'
    """, (current_user.id, current_user.id)).fetchall()
    following = db.execute("""
        SELECT u.id, u.username, m.fullName AS realName, m.profilePhoto,
               (SELECT COUNT(*) FROM friendships f2 WHERE f2.user2_id = u.id AND f2.status = 'accepted' AND f2.user1_id IN 
                 (SELECT user2_id FROM friendships WHERE user1_id = ? AND status = 'accepted')) AS mutual_count
        FROM friendships f
        JOIN users u ON f.user2_id = u.id
        JOIN members m ON u.id = m.user_id
        WHERE f.user1_id = ? AND f.status = 'accepted'
    """, (current_user.id, current_user.id)).fetchall()
    friend_requests = db.execute("""
        SELECT f.id, u.id AS sender_id, u.username AS sender_username, m.fullName AS sender_realName, m.profilePhoto AS sender_profilePhoto,
               (SELECT COUNT(*) FROM friendships f2 WHERE f2.user2_id = u.id AND f2.status = 'accepted' AND f2.user1_id IN 
                 (SELECT user2_id FROM friendships WHERE user1_id = ? AND status = 'accepted')) AS mutual_count
        FROM friendships f
        JOIN users u ON f.user1_id = u.id
        JOIN members m ON u.id = m.user_id
        WHERE f.user2_id = ? AND f.status = 'pending'
    """, (current_user.id, current_user.id)).fetchall()
    all_friends = db.execute("""
        SELECT u.id, u.username, m.fullName AS realName, m.profilePhoto,
               (SELECT COUNT(*) FROM friendships f2 WHERE f2.user2_id = u.id AND f2.status = 'accepted' AND f2.user1_id IN 
                 (SELECT user2_id FROM friendships WHERE user1_id = ? AND status = 'accepted')) AS mutual_count
        FROM friendships f
        JOIN users u ON (f.user1_id = u.id OR f.user2_id = u.id)
        JOIN members m ON u.id = m.user_id
        WHERE (f.user1_id = ? OR f.user2_id = ?) AND f.status = 'accepted' AND u.id != ?
    """, (current_user.id, current_user.id, current_user.id, current_user.id)).fetchall()
    suggested_users = db.execute("""
        SELECT u.id, u.username, m.fullName AS realName, m.profilePhoto,
               (SELECT COUNT(*) FROM friendships f2 WHERE f2.user2_id = u.id AND f2.status = 'accepted' AND f2.user1_id IN 
                 (SELECT user2_id FROM friendships WHERE user1_id = ? AND status = 'accepted')) AS mutual_count
        FROM users u
        JOIN members m ON u.id = m.user_id
        WHERE u.id != ? AND u.id NOT IN (
            SELECT user2_id FROM friendships WHERE user1_id = ? AND status = 'accepted'
            UNION
            SELECT user1_id FROM friendships WHERE user2_id = ? AND status = 'accepted'
            UNION
            SELECT user_id FROM blocked_users WHERE blocked_by = ?
        )
        ORDER BY mutual_count DESC
        LIMIT 10
    """, (current_user.id, current_user.id, current_user.id, current_user.id, current_user.id)).fetchall()
    return render_template('friends.html', followers=followers, following=following, friend_requests=friend_requests, all_friends=all_friends, suggested_users=suggested_users)

@app.route('/inbox')
@login_required
def inbox():
    db = get_db()
    chats = db.execute("""
        SELECT cr.id AS chat_room_id, u.id AS other_user_id, u.username AS other_user_username, m.fullName AS real_name, m.profilePhoto,
               (SELECT content FROM chat_messages cm WHERE cm.chat_room_id = cr.id ORDER BY cm.timestamp DESC LIMIT 1) AS latest_message_snippet,
               (SELECT timestamp FROM chat_messages cm WHERE cm.chat_room_id = cr.id ORDER BY cm.timestamp DESC LIMIT 1) AS timestamp,
               (SELECT COUNT(*) FROM chat_messages cm WHERE cm.chat_room_id = cr.id AND cm.sender_id != ? AND cm.is_read = 0) AS unread_count
        FROM chat_rooms cr
        JOIN users u ON (cr.user1_id = u.id OR cr.user2_id = u.id) AND u.id != ?
        JOIN members m ON u.id = m.user_id
        WHERE cr.group_id IS NULL AND (cr.user1_id = ? OR cr.user2_id = ?)
    """, (current_user.id, current_user.id, current_user.id, current_user.id)).fetchall()
    groups = db.execute("""
        SELECT g.id, g.name, g.profilePhoto,
               (SELECT content FROM chat_messages cm WHERE cm.chat_room_id = cr.id ORDER BY cm.timestamp DESC LIMIT 1) AS latest_message_snippet,
               (SELECT timestamp FROM chat_messages cm WHERE cm.chat_room_id = cr.id ORDER BY cm.timestamp DESC LIMIT 1) AS timestamp,
               (SELECT COUNT(*) FROM chat_messages cm WHERE cm.chat_room_id = cr.id AND cm.sender_id != ? AND cm.is_read = 0) AS unread_count
        FROM groups g
        JOIN group_members gm ON g.id = gm.group_id
        JOIN chat_rooms cr ON g.id = cr.group_id
        WHERE gm.user_id = ?
    """, (current_user.id, current_user.id)).fetchall()
    unread_chats_count = sum(1 for chat in chats if chat['unread_count'] > 0)
    unread_groups_count = sum(1 for group in groups if group['unread_count'] > 0)
    return render_template('inbox.html', chats=chats, groups=groups, unread_chats_count=unread_chats_count, unread_groups_count=unread_groups_count)

@app.route('/api/friend_request', methods=['POST'])
@login_required
def friend_request():
    data = request.json
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User ID required.'}), 400
    db = get_db()
    try:
        db.execute(
            "INSERT INTO friendships (user1_id, user2_id, status, timestamp) VALUES (?, ?, 'pending', ?)",
            (current_user.id, user_id, datetime.now(timezone.utc))
        )
        db.commit()
        send_system_notification(user_id, f"{current_user.username} sent you a friend request.", url_for('friends'))
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/accept_friend_request', methods=['POST'])
@login_required
def accept_friend_request():
    data = request.json
    request_id = data.get('request_id')
    if not request_id:
        return jsonify({'success': False, 'message': 'Request ID required.'}), 400
    db = get_db()
    try:
        friendship = db.execute("SELECT user1_id FROM friendships WHERE id = ? AND user2_id = ?", (request_id, current_user.id)).fetchone()
        if not friendship:
            return jsonify({'success': False, 'message': 'Friend request not found.'}), 404
        db.execute("UPDATE friendships SET status = 'accepted' WHERE id = ?", (request_id,))
        db.execute(
            "INSERT INTO friendships (user1_id, user2_id, status, timestamp) VALUES (?, ?, 'accepted', ?)",
            (current_user.id, friendship['user1_id'], datetime.now(timezone.utc))
        )
        db.commit()
        send_system_notification(friendship['user1_id'], f"{current_user.username} accepted your friend request.", url_for('friends'))
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/decline_friend_request', methods=['POST'])
@login_required
def decline_friend_request():
    data = request.json
    request_id = data.get('request_id')
    if not request_id:
        return jsonify({'success': False, 'message': 'Request ID required.'}), 400
    db = get_db()
    try:
        db.execute("DELETE FROM friendships WHERE id = ? AND user2_id = ?", (request_id, current_user.id))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/unfollow', methods=['POST'])
@login_required
def unfollow():
    data = request.json
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User ID required.'}), 400
    db = get_db()
    try:
        db.execute(
            "DELETE FROM friendships WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?) AND status = 'accepted'",
            (current_user.id, user_id, user_id, current_user.id)
        )
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/block_user', methods=['POST'])
@login_required
def block_user():
    data = request.json
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User ID required.'}), 400
    db = get_db()
    try:
        db.execute(
            "INSERT INTO blocked_users (user_id, blocked_by, timestamp) VALUES (?, ?, ?)",
            (user_id, current_user.id, datetime.now(timezone.utc))
        )
        db.execute(
            "DELETE FROM friendships WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)",
            (current_user.id, user_id, user_id, current_user.id)
        )
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/chat_room', methods=['GET', 'POST'])
@login_required
def chat_room():
    db = get_db()
    if request.method == 'POST':
        user_id = request.json.get('user_id')
        group_id = request.json.get('group_id')
        if not user_id and not group_id:
            return jsonify({'success': False, 'message': 'User ID or Group ID required.'}), 400
        try:
            if user_id:
                existing_room = db.execute(
                    "SELECT id FROM chat_rooms WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)",
                    (current_user.id, user_id, user_id, current_user.id)
                ).fetchone()
                if existing_room:
                    return jsonify({'success': True, 'chat_room_id': existing_room['id']})
                db.execute(
                    "INSERT INTO chat_rooms (user1_id, user2_id, created_at) VALUES (?, ?, ?)",
                    (current_user.id, user_id, datetime.now(timezone.utc))
                )
                chat_room_id = db.lastrowid
            elif group_id:
                existing_room = db.execute(
                    "SELECT id FROM chat_rooms WHERE group_id = ?",
                    (group_id,)
                ).fetchone()
                if existing_room:
                    return jsonify({'success': True, 'chat_room_id': existing_room['id']})
                db.execute(
                    "INSERT INTO chat_rooms (group_id, created_at) VALUES (?, ?)",
                    (group_id, datetime.now(timezone.utc))
                )
                chat_room_id = db.lastrowid
            db.commit()
            return jsonify({'success': True, 'chat_room_id': chat_room_id})
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
    else:
        user_id = request.args.get('user_id')
        group_id = request.args.get('group_id')
        if user_id:
            chat_room = db.execute(
                "SELECT id FROM chat_rooms WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)",
                (current_user.id, user_id, user_id, current_user.id)
            ).fetchone()
            if chat_room:
                return jsonify({'success': True, 'chat_room_id': chat_room['id']})
            return jsonify({'success': False, 'message': 'Chat room not found.'}), 404
        elif group_id:
            chat_room = db.execute(
                "SELECT id FROM chat_rooms WHERE group_id = ?",
                (group_id,)
            ).fetchone()
            if chat_room:
                return jsonify({'success': True, 'chat_room_id': chat_room['id']})
            return jsonify({'success': False, 'message': 'Group chat room not found.'}), 404
        return jsonify({'success': False, 'message': 'User ID or Group ID required.'}), 400

@app.route('/api/send_message', methods=['POST'])
@login_required
def send_message():
    data = request.json
    chat_room_id = data.get('chat_room_id')
    content = data.get('content')
    media_file = data.get('media_file')
    media_type = data.get('media_type')
    if not chat_room_id or (not content and not media_file):
        return jsonify({'success': False, 'message': 'Chat room ID and content or media required.'}), 400
    db = get_db()
    try:
        media_path = None
        if media_file:
            media_data = base64.b64decode(media_file.split(',')[1])
            filename = f"{uuid.uuid4().hex}.{media_type.split('/')[1]}"
            media_path = os.path.join(app.config['CHAT_MEDIA_FOLDER'], filename)
            with open(media_path, 'wb') as f:
                f.write(media_data)
        db.execute(
            """
            INSERT INTO chat_messages (chat_room_id, sender_id, content, media_path, media_type, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (chat_room_id, current_user.id, content, media_path, media_type, datetime.now(timezone.utc))
        )
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/post/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    db = get_db()
    try:
        existing_like = db.execute(
            "SELECT id FROM likes WHERE post_id = ? AND user_id = ?",
            (post_id, current_user.id)
        ).fetchone()
        if existing_like:
            db.execute("DELETE FROM likes WHERE id = ?", (existing_like['id'],))
            db.commit()
            return jsonify({'success': True, 'liked': False})
        db.execute(
            "INSERT INTO likes (post_id, user_id, timestamp) VALUES (?, ?, ?)",
            (post_id, current_user.id, datetime.now(timezone.utc))
        )
        db.commit()
        post_owner = db.execute("SELECT user_id FROM posts WHERE id = ?", (post_id,)).fetchone()
        if post_owner and post_owner['user_id'] != current_user.id:
            send_system_notification(post_owner['user_id'], f"{current_user.username} liked your post.", url_for('home'))
        return jsonify({'success': True, 'liked': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/post/<int:post_id>/comment', methods=['POST'])
@login_required
def comment_post(post_id):
    data = request.json
    content = data.get('content')
    if not content:
        return jsonify({'success': False, 'message': 'Comment content required.'}), 400
    db = get_db()
    try:
        db.execute(
            "INSERT INTO comments (post_id, user_id, content, timestamp) VALUES (?, ?, ?, ?)",
            (post_id, current_user.id, content, datetime.now(timezone.utc))
        )
        db.commit()
        post_owner = db.execute("SELECT user_id FROM posts WHERE id = ?", (post_id,)).fetchone()
        if post_owner and post_owner['user_id'] != current_user.id:
            send_system_notification(post_owner['user_id'], f"{current_user.username} commented on your post.", url_for('home'))
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/notifications')
@login_required
def notifications():
    db = get_db()
    notifications = db.execute(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY timestamp DESC",
        (current_user.id,)
    ).fetchall()
    db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (current_user.id,))
    db.commit()
    return render_template('notifications.html', notifications=notifications)

@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()
    users = db.execute("SELECT * FROM users WHERE is_admin = 0").fetchall()
    reported_content = db.execute("SELECT * FROM reports ORDER BY timestamp DESC").fetchall()
    return render_template('admin.html', users=users, reported_content=reported_content)

@app.route('/api/admin/ban_user/<int:user_id>', methods=['POST'])
@admin_required
def ban_user(user_id):
    db = get_db()
    try:
        db.execute("UPDATE users SET is_banned = 1 WHERE id = ?", (user_id,))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/delete_content/<string:content_type>/<int:content_id>', methods=['POST'])
@admin_required
def delete_content(content_type, content_id):
    db = get_db()
    try:
        if content_type == 'post':
            db.execute("DELETE FROM posts WHERE id = ?", (content_id,))
        elif content_type == 'comment':
            db.execute("DELETE FROM comments WHERE id = ?", (content_id,))
        elif content_type == 'story':
            db.execute("DELETE FROM stories WHERE id = ?", (content_id,))
        else:
            return jsonify({'success': False, 'message': 'Invalid content type.'}), 400
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/report/<string:content_type>/<int:content_id>', methods=['POST'])
@login_required
def report_content(content_type, content_id):
    db = get_db()
    reason = request.json.get('reason')
    if not reason:
        return jsonify({'success': False, 'message': 'Reason for report is required.'}), 400
    try:
        db.execute(
            """
            INSERT INTO reports (user_id, content_type, content_id, reason, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (current_user.id, content_type, content_id, reason, datetime.now(timezone.utc))
        )
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/broadcast_message', methods=['POST'])
@admin_required
def broadcast_message():
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

# --- New and Modified APIs for index.html, friends.html, and inbox.html ---
@app.route('/api/search_users', methods=['GET'])
@login_required
def api_search_users():
    query = request.args.get('term', '').strip()
    db = get_db()
    results = []
    if query:
        users = db.execute(
            """
            SELECT u.id, u.username, m.fullName AS real_name, m.profilePhoto
            FROM users u
            LEFT JOIN miembers m ON u.id = m.user_id
            WHERE m.fullName LIKE ? OR u.username LIKE ?
            ORDER BY 
                CASE 
                    WHEN m.fullName LIKE ? THEN 1
                    WHEN u.username LIKE ? THEN 2
                    ELSE 3
                END,
                m.fullName
            """,
            (f'{query}%', f'{query}%', f'{query}%', f'{query}%')
        ).fetchall()
        for user in users:
            user_dict = dict(user)
            user_dict['profilePhoto'] = user_dict['profilePhoto'] or url_for('static', filename='img/default_profile.png')
            is_following = db.execute(
                "SELECT 1 FROM friendships WHERE user1_id = ? AND user2_id = ? AND status = 'accepted'",
                (current_user.id, user['id'])
            ).fetchone() is not None
            user_dict['is_following'] = is_following
            results.append({'type': 'user', 'data': user_dict})
    return jsonify({'results': results})

@app.route('/api/search_inbox', methods=['GET'])
@login_required
def api_search_inbox():
    query = request.args.get('term', '').strip()
    db = get_db()
    results = []
    if query:
        users = db.execute(
            """
            SELECT u.id, u.username, m.fullName AS real_name, m.profilePhoto
            FROM users u
            JOIN members m ON u.id = m.user_id
            JOIN friendships f1 ON u.id = f1.user2_id AND f1.user1_id = ? AND f1.status = 'accepted'
            JOIN friendships f2 ON u.id = f2.user1_id AND f2.user2_id = ? AND f2.status = 'accepted'
            WHERE m.fullName LIKE ? OR u.username LIKE ?
            ORDER BY 
                CASE 
                    WHEN m.fullName LIKE ? THEN 1
                    WHEN u.username LIKE ? THEN 2
                    ELSE 3
                END,
                m.fullName
            """,
            (current_user.id, current_user.id, f'{query}%', f'{query}%', f'{query}%', f'{query}%')
        ).fetchall()
        for user in users:
            user_dict = dict(user)
            user_dict['profilePhoto'] = user_dict['profilePhoto'] or url_for('static', filename='img/default_profile.png')
            user_dict['is_following'] = True
            results.append({'type': 'user', 'data': user_dict})
        groups = db.execute(
            """
            SELECT g.id, g.name, g.description, g.profilePhoto
            FROM groups g
            JOIN group_members gm ON g.id = gm.group_id AND gm.user_id = ?
            WHERE g.name LIKE ? OR g.description LIKE ?
            ORDER BY g.name
            """,
            (current_user.id, f'{query}%', f'{query}%')
        ).fetchall()
        for group in groups:
            group_dict = dict(group)
            group_dict['profilePhoto'] = group_dict['profilePhoto'] or url_for('static', filename='img/default_group.png')
            group_dict['is_member'] = True
            results.append({'type': 'group', 'data': group_dict})
    return jsonify({'results': results})

@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('q', '').strip()
    db = get_db()
    search_results = []
    if query:
        users = db.execute(
            """
            SELECT u.id, u.username, m.fullName as originalName, m.profilePhoto
            FROM users u
            LEFT JOIN members m ON u.id = m.user_id
            WHERE u.username LIKE ? OR m.fullName LIKE ?
            ORDER BY m.fullName
            """,
            (f'%{query}%', f'%{query}%')
        ).fetchall()
        for user in users:
            user_dict = dict(user)
            user_dict['profilePhoto'] = get_member_profile_pic(user_dict['id'])
            search_results.append({'type': 'user', 'data': user_dict})
        groups = db.execute(
            """
            SELECT g.id, g.name, g.description, g.profilePhoto
            FROM groups g
            WHERE g.name LIKE ? OR g.description LIKE ?
            ORDER BY g.name
            """,
            (f'%{query}%', f'%{query}%')
        ).fetchall()
        for group in groups:
            group_dict = dict(group)
            group_dict['profilePhoto'] = group_dict['profilePhoto'] or url_for('static', filename='img/default_group.png')
            search_results.append({'type': 'group', 'data': group_dict})
    current_year = datetime.now(timezone.utc).year
    return render_template('search.html', query=query, search_results=search_results, current_year=current_year)

@app.route('/api/posts', methods=['GET'])
@login_required
def api_posts():
    page = int(request.args.get('page', 1))
    per_page = 10
    db = get_db()
    posts = db.execute(
        """
        SELECT p.*, m.fullName as user_real_name, m.profilePhoto as user_profile_photo, u.username
        FROM posts p
        JOIN members m ON p.user_id = m.user_id
        JOIN users u ON p.user_id = u.id
        WHERE p.visibility IN ('public', 'friends')
        ORDER BY p.timestamp DESC
        LIMIT ? OFFSET ?
        """,
        (per_page, (page-1)*per_page)
    ).fetchall()
    return jsonify({'posts': [dict(post) for post in posts]})

@app.route('/api/chat/<int:chat_id>', methods=['GET'])
@login_required
def api_chat(chat_id):
    db = get_db()
    user = db.execute(
        "SELECT u.username, m.fullName as real_name, m.profilePhoto FROM users u JOIN members m ON u.id = m.user_id WHERE u.id = ?",
        (chat_id,)
    ).fetchone()
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 404
    messages = db.execute(
        """
        SELECT cm.*, u.username as sender FROM chat_messages cm
        JOIN chat_rooms cr ON cm.chat_room_id = cr.id
        JOIN users u ON cm.sender_id = u.id
        WHERE cr.group_id IS NULL AND ((cr.user1_id = ? AND cr.user2_id = ?) OR (cr.user1_id = ? AND cr.user2_id = ?))
        ORDER BY cm.timestamp
        """,
        (current_user.id, chat_id, chat_id, current_user.id)
    ).fetchall()
    return jsonify({
        'success': True,
        'user': dict(user),
        'messages': [dict(msg) for msg in messages]
    })

@app.route('/api/group_chat/<int:group_id>', methods=['GET'])
@login_required
def api_group_chat(group_id):
    db = get_db()
    group = db.execute(
        "SELECT g.*, m.fullName as creator_name FROM groups g LEFT JOIN members m ON g.creator_id = m.user_id WHERE g.id = ?",
        (group_id,)
    ).fetchone()
    if not group:
        return jsonify({'success': False, 'message': 'Group not found.'}), 404
    messages = db.execute(
        """
        SELECT cm.*, u.username as sender FROM chat_messages cm
        JOIN chat_rooms cr ON cm.chat_room_id = cr.id
        JOIN users u ON cm.sender_id = u.id
        WHERE cr.group_id = ?
        ORDER BY cm.timestamp
        """,
        (group_id,)
    ).fetchall()
    return jsonify({
        'success': True,
        'group': dict(group),
        'messages': [dict(msg) for msg in messages]
    })

@app.route('/api/remove_suggested', methods=['POST'])
@login_required
def api_remove_suggested():
    data = request.json
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User ID required.'}), 400
    db = get_db()
    try:
        db.execute(
            "INSERT INTO blocked_users (user_id, blocked_by, timestamp) VALUES (?, ?, ?)",
            (user_id, current_user.id, datetime.now(timezone.utc))
        )
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/create_group', methods=['POST'])
@login_required
def create_group():
    name = request.form.get('groupName')
    photo = request.files.get('groupPhoto')
    db = get_db()
    try:
        db.execute(
            "INSERT INTO groups (name, creator_id, timestamp) VALUES (?, ?, ?)",
            (name, current_user.id, datetime.now(timezone.utc))
        )
        group_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute(
            "INSERT INTO group_members (group_id, user_id, joined_at) VALUES (?, ?, ?)",
            (group_id, current_user.id, datetime.now(timezone.utc))
        )
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(photo_path)
            db.execute(
                "UPDATE groups SET profilePhoto = ? WHERE id = ?",
                (photo_path, group_id)
            )
        db.commit()
        return redirect(url_for('inbox'))
    except Exception as e:
        db.rollback()
        flash(f'Failed to create group: {str(e)}', 'danger')
        return redirect(url_for('inbox'))

# --- Catch-all for undefined routes ---
@app.errorhandler(404)
def page_not_found(e):
    flash('The page you requested could not be found.', 'danger')
    return redirect(url_for('home'))

@app.errorhandler(403)
def forbidden(e):
    flash('You do not have permission to access this resource.', 'danger')
    return redirect(url_for('home'))

# Run the app
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
