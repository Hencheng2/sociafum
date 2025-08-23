from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from models import db, User, Post, Story, Comment, Like, Follow, Message, Group, Notification, BlockedUser
from config import Config
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import uuid
import base64
from io import BytesIO

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()
    # Create admin user if not exists
    admin = User.query.filter_by(username=app.config['ADMIN_USERNAME']).first()
    if not admin:
        admin = User(
            username=app.config['ADMIN_USERNAME'],
            real_name="SociaFam Admin",
            is_admin=True
        )
        admin.set_password(app.config['ADMIN_PASS'])
        admin.generate_unique_key()
        db.session.add(admin)
        db.session.commit()

# Utility functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}

def save_file_to_db(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_data = file.read()
        return filename, file_data
    return None, None

# Route to serve images from database
@app.route('/image/<int:user_id>')
def get_profile_image(user_id):
    user = User.query.get_or_404(user_id)
    if not user.profile_pic:
        return redirect(url_for('static', filename='images/default-profile.png'))
    
    return Response(user.profile_pic, mimetype='image/jpeg')

# Route to serve post images from database
@app.route('/post-image/<int:post_id>')
def get_post_image(post_id):
    post = Post.query.get_or_404(post_id)
    if not post.image:
        return redirect(url_for('static', filename='images/default-post.png'))
    
    return Response(post.image, mimetype='image/jpeg')

# Route to serve post videos from database
@app.route('/post-video/<int:post_id>')
def get_post_video(post_id):
    post = Post.query.get_or_404(post_id)
    if not post.video:
        return Response(status=404)
    
    return Response(post.video, mimetype='video/mp4')

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        # Get stories from friends
        following_ids = [f.followed_id for f in current_user.following.all()]
        stories = Story.query.filter(Story.user_id.in_(following_ids)).filter(Story.expires_at > datetime.utcnow()).all()
        
        # Get posts
        posts = Post.query.filter_by(is_private=False).order_by(Post.created_at.desc()).limit(20).all()
        
        return render_template('index.html', stories=stories, posts=posts)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        # Check if trying to register as admin
        if username == app.config['ADMIN_USERNAME']:
            flash('Cannot register with this username', 'error')
            return render_template('register.html')
        
        # Create new user
        user = User(username=username)
        user.set_password(password)
        user.generate_unique_key()
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    
    # Check if profile is locked and user is not following
    if user.profile_locked and not current_user.is_following(user) and current_user.id != user.id:
        return render_template('profile.html', user=user, locked=True)
    
    posts = user.posts.filter_by(is_private=False).order_by(Post.created_at.desc()).all()
    
    # Get mutual friends count
    mutual_friends = 0
    if current_user.id != user.id:
        current_following = {f.followed_id for f in current_user.following.all()}
        user_followers = {f.follower_id for f in user.followers.all()}
        mutual_friends = len(current_following.intersection(user_followers))
    
    return render_template('profile.html', user=user, posts=posts, mutual_friends=mutual_friends)

@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.real_name = request.form.get('real_name')
        current_user.bio = request.form.get('bio')
        current_user.work = request.form.get('work')
        current_user.university = request.form.get('university')
        current_user.location = request.form.get('location')
        current_user.website = request.form.get('website')
        current_user.phone_number = request.form.get('phone_number')
        
        # Handle profile picture upload
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename != '':
                filename, file_data = save_file_to_db(file)
                if filename and file_data:
                    current_user.profile_pic = file_data
                    current_user.profile_pic_filename = filename
        
        db.session.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('profile', username=current_user.username))
    
    return render_template('edit-profile.html')

@app.route('/add-post', methods=['GET', 'POST'])
@login_required
def add_post():
    if request.method == 'POST':
        content = request.form.get('content')
        post_type = request.form.get('type')
        
        if post_type == 'story':
            # Handle story creation
            story = Story(content=content, user_id=current_user.id)
            
            if 'media' in request.files:
                file = request.files['media']
                if file and file.filename != '':
                    filename, file_data = save_file_to_db(file)
                    if filename and file_data:
                        if file.content_type.startswith('video'):
                            story.video = file_data
                            story.video_filename = filename
                        else:
                            story.image = file_data
                            story.image_filename = filename
            
            db.session.add(story)
            db.session.commit()
            flash('Story added successfully', 'success')
            return redirect(url_for('index'))
        else:
            # Handle post/reel creation
            post = Post(content=content, user_id=current_user.id)
            
            if post_type == 'reel':
                post.is_reel = True
            
            # Handle media upload for post/reel
            if 'media' in request.files:
                file = request.files['media']
                if file and file.filename != '':
                    filename, file_data = save_file_to_db(file)
                    if filename and file_data:
                        if file.content_type.startswith('video'):
                            post.video = file_data
                            post.video_filename = filename
                        else:
                            post.image = file_data
                            post.image_filename = filename
            
            db.session.add(post)
            db.session.commit()
            flash('Post added successfully', 'success')
            return redirect(url_for('index'))
    
    return render_template('add-content.html')

@app.route('/like-post/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Check if user already liked this post
    existing_like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    
    if existing_like:
        db.session.delete(existing_like)
        liked = False
    else:
        like = Like(user_id=current_user.id, post_id=post_id)
        db.session.add(like)
        
        # Create notification for post owner
        if post.author.id != current_user.id:
            notification = Notification(
                user_id=post.author.id,
                content=f"{current_user.username} liked your post",
                type='like',
                related_id=post_id
            )
            db.session.add(notification)
        
        liked = True
    
    db.session.commit()
    return jsonify({'liked': liked, 'likes_count': post.likes.count()})

@app.route('/follow-user/<int:user_id>', methods=['POST'])
@login_required
def follow_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if current_user.is_following(user):
        current_user.unfollow(user)
        followed = False
    else:
        current_user.follow(user)
        
        # Create notification
        notification = Notification(
            user_id=user_id,
            content=f"{current_user.username} started following you",
            type='follow',
            related_id=current_user.id
        )
        db.session.add(notification)
        
        followed = True
    
    db.session.commit()
    return jsonify({'followed': followed, 'followers_count': user.followers.count()})

@app.route('/reels')
@login_required
def reels():
    reels = Post.query.filter_by(is_reel=True).order_by(Post.created_at.desc()).all()
    return render_template('reels.html', reels=reels)

@app.route('/friends')
@login_required
def friends():
    tab = request.args.get('tab', 'followers')
    
    followers = current_user.followers.all()
    following = current_user.following.all()
    
    # Find mutual follows (friends)
    follower_ids = {f.follower_id for f in followers}
    following_ids = {f.followed_id for f in following}
    friend_ids = follower_ids.intersection(following_ids)
    friends = User.query.filter(User.id.in_(friend_ids)).all()
    
    # Get friend requests (users who follow you but you don't follow back)
    request_ids = follower_ids - following_ids
    friend_requests = User.query.filter(User.id.in_(request_ids)).all()
    
    # Get suggested friends (friends of friends)
    suggested_friends = User.query.filter(
        User.id != current_user.id,
        User.id.not_in(follower_ids.union(following_ids))
    ).limit(10).all()
    
    return render_template('friends.html', 
                         tab=tab,
                         followers=followers,
                         following=following,
                         friends=friends,
                         friend_requests=friend_requests,
                         suggested_friends=suggested_friends)

@app.route('/inbox')
@login_required
def inbox():
    tab = request.args.get('tab', 'chats')
    
    # Get recent chats
    sent_messages = current_user.sent_messages.order_by(Message.created_at.desc()).all()
    received_messages = current_user.received_messages.order_by(Message.created_at.desc()).all()
    
    # Combine and get unique users
    all_messages = sent_messages + received_messages
    chat_users = {}
    
    for msg in all_messages:
        other_user = msg.sender if msg.sender_id != current_user.id else msg.receiver
        if other_user.id not in chat_users or msg.created_at > chat_users[other_user.id]['last_message'].created_at:
            unread_count = Message.query.filter_by(
                sender_id=other_user.id, 
                receiver_id=current_user.id,
                is_read=False
            ).count() if other_user.id != current_user.id else 0
            
            chat_users[other_user.id] = {
                'user': other_user,
                'last_message': msg,
                'unread_count': unread_count
            }
    
    chats = sorted(chat_users.values(), key=lambda x: x['last_message'].created_at, reverse=True)
    
    # Get groups user is member of
    groups = Group.query.join(Group.members).filter(
        GroupMember.user_id == current_user.id
    ).all()
    
    return render_template('inbox.html', tab=tab, chats=chats, groups=groups)

@app.route('/chat/<int:user_id>')
@login_required
def chat(user_id):
    user = User.query.get_or_404(user_id)
    
    # Mark messages as read
    Message.query.filter_by(sender_id=user_id, receiver_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    
    # Get message history
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at.asc()).all()
    
    return render_template('chat.html', user=user, messages=messages)

@app.route('/send-message', methods=['POST'])
@login_required
def send_message():
    receiver_id = request.form.get('receiver_id')
    content = request.form.get('content')
    
    if not content.strip():
        return jsonify({'success': False, 'error': 'Message cannot be empty'})
    
    message = Message(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        content=content
    )
    
    db.session.add(message)
    db.session.commit()
    
    # Create notification
    notification = Notification(
        user_id=receiver_id,
        content=f"{current_user.username} sent you a message",
        type='message',
        related_id=message.id
    )
    db.session.add(notification)
    db.session.commit()
    
    return jsonify({'success': True, 'message_id': message.id})

@app.route('/notifications')
@login_required
def notifications():
    notifications = current_user.notifications.order_by(Notification.created_at.desc()).all()
    
    # Mark as read
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    
    return render_template('notifications.html', notifications=notifications)

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    
    if query:
        # Search users
        users = User.query.filter(
            (User.username.ilike(f'%{query}%')) | 
            (User.real_name.ilike(f'%{query}%'))
        ).all()
        
        # Search posts
        posts = Post.query.filter(
            Post.content.ilike(f'%{query}%')
        ).all()
        
        # Search groups
        groups = Group.query.filter(
            Group.name.ilike(f'%{query}%')
        ).all()
    else:
        users = []
        posts = []
        groups = []
    
    return render_template('search.html', query=query, users=users, posts=posts, groups=groups)

@app.route('/menu')
@login_required
def menu():
    return render_template('menu.html')

@app.route('/settings')
@login_required
def settings():
    blocked_users = current_user.blocked_users.all()
    blocked_users_info = []
    
    for blocked in blocked_users:
        user = User.query.get(blocked.blocked_user_id)
        if user:
            blocked_users_info.append(user)
    
    return render_template('settings.html', blocked_users=blocked_users_info)

@app.route('/save-settings', methods=['POST'])
@login_required
def save_settings():
    tab = request.form.get('tab', 'privacy')
    
    if tab == 'privacy':
        # Update privacy settings
        current_user.profile_locked = bool(request.form.get('profile_locked'))
        current_user.post_privacy = request.form.get('post_privacy', 'public')
        
        db.session.commit()
        flash('Privacy settings updated successfully', 'success')
    
    elif tab == 'notifications':
        # Update notification settings
        current_user.email_notifications = bool(request.form.get('email_notifications'))
        current_user.push_notifications = bool(request.form.get('push_notifications'))
        current_user.like_notifications = bool(request.form.get('like_notifications'))
        current_user.comment_notifications = bool(request.form.get('comment_notifications'))
        current_user.follow_notifications = bool(request.form.get('follow_notifications'))
        current_user.message_notifications = bool(request.form.get('message_notifications'))
        
        db.session.commit()
        flash('Notification settings updated successfully', 'success')
    
    elif tab == 'password':
        # Change password
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_user.check_password(current_password):
            flash('Current password is incorrect', 'error')
            return redirect(url_for('settings') + '?tab=password')
        
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return redirect(url_for('settings') + '?tab=password')
        
        # Validate password strength
        if len(new_password) < 6 or not any(char.isdigit() for char in new_password) or not any(char in '!@#$%^&*()_+-=[]{}|;:,.<>?`~' for char in new_password):
            flash('Password must be at least 6 characters with numbers and special characters', 'error')
            return redirect(url_for('settings') + '?tab=password')
        
        current_user.set_password(new_password)
        db.session.commit()
        
        flash('Password changed successfully', 'success')
    
    elif tab == 'theme':
        # Toggle theme
        current_user.theme = 'dark' if current_user.theme == 'light' else 'light'
        db.session.commit()
        flash('Theme updated successfully', 'success')
    
    return redirect(url_for('settings') + f'?tab={tab}')

@app.route('/block-user/<int:user_id>', methods=['POST'])
@login_required
def block_user(user_id):
    user_to_block = User.query.get_or_404(user_id)
    
    if current_user.id == user_id:
        return jsonify({'success': False, 'message': 'You cannot block yourself'})
    
    if current_user.is_blocked(user_to_block):
        return jsonify({'success': False, 'message': 'User already blocked'})
    
    current_user.block(user_to_block)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'User blocked successfully'})

@app.route('/unblock-user/<int:user_id>', methods=['POST'])
@login_required
def unblock_user(user_id):
    user_to_unblock = User.query.get_or_404(user_id)
    
    if not current_user.is_blocked(user_to_unblock):
        return jsonify({'success': False, 'message': 'User is not blocked'})
    
    current_user.unblock(user_to_unblock)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'User unblocked successfully'})

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    users = User.query.all()
    posts = Post.query.all()
    groups = Group.query.all()
    
    return render_template('admin-dashboard.html', users=users, posts=posts, groups=groups)

# API routes for infinite scroll
@app.route('/api/posts')
@login_required
def api_posts():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    posts = Post.query.filter_by(is_private=False).order_by(Post.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    posts_data = []
    for post in posts.items:
        posts_data.append({
            'id': post.id,
            'content': post.content,
            'image': post.image is not None,
            'video': post.video is not None,
            'author': {
                'username': post.author.username,
                'real_name': post.author.real_name,
                'profile_pic': post.author.profile_pic is not None
            },
            'created_at': post.created_at.isoformat(),
            'likes_count': post.likes.count(),
            'comments_count': post.comments.count(),
            'is_liked': current_user.is_authenticated and 
                       Like.query.filter_by(user_id=current_user.id, post_id=post.id).first() is not None
        })
    
    return jsonify({
        'posts': posts_data,
        'has_next': posts.has_next,
        'next_page': posts.next_num if posts.has_next else None
    })

if __name__ == '__main__':
    app.run(debug=True)
