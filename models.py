from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    email = db.Column(db.String(120), unique=True, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    real_name = db.Column(db.String(100))
    profile_pic = db.Column(db.LargeBinary)
    profile_pic_filename = db.Column(db.String(200))
    bio = db.Column(db.Text)
    unique_key = db.Column(db.String(4), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Profile details
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(20))
    pronouns = db.Column(db.String(20))
    work = db.Column(db.String(200))
    university = db.Column(db.String(200))
    secondary_school = db.Column(db.String(200))
    location = db.Column(db.String(200))
    phone_number = db.Column(db.String(20))
    website = db.Column(db.String(200))
    relationship_status = db.Column(db.String(50))
    spouse = db.Column(db.String(100))
    
    # Privacy settings
    profile_locked = db.Column(db.Boolean, default=False)
    post_privacy = db.Column(db.String(20), default='public')  # public, friends, only_me
    
    # Notification settings
    email_notifications = db.Column(db.Boolean, default=True)
    push_notifications = db.Column(db.Boolean, default=True)
    like_notifications = db.Column(db.Boolean, default=True)
    comment_notifications = db.Column(db.Boolean, default=True)
    follow_notifications = db.Column(db.Boolean, default=True)
    message_notifications = db.Column(db.Boolean, default=True)
    
    # Theme preference
    theme = db.Column(db.String(10), default='light')  # 'light' or 'dark'
    
    # Relationships
    posts = db.relationship('Post', backref='author', lazy='dynamic', foreign_keys='Post.user_id')
    stories = db.relationship('Story', backref='author', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    likes = db.relationship('Like', backref='user', lazy='dynamic')
    sent_messages = db.relationship('Message', backref='sender', lazy='dynamic', foreign_keys='Message.sender_id')
    received_messages = db.relationship('Message', backref='receiver', lazy='dynamic', foreign_keys='Message.receiver_id')
    followers = db.relationship('Follow', foreign_keys='Follow.followed_id', backref='followed', lazy='dynamic')
    following = db.relationship('Follow', foreign_keys='Follow.follower_id', backref='follower', lazy='dynamic')
    blocked_users = db.relationship('BlockedUser', foreign_keys='BlockedUser.user_id', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_unique_key(self):
        import random
        import string
        numbers = ''.join(random.choices(string.digits, k=2))
        letters = ''.join(random.choices(string.ascii_uppercase, k=2))
        self.unique_key = numbers + letters
    
    def is_following(self, user):
        return self.following.filter_by(followed_id=user.id).first() is not None
    
    def follow(self, user):
        if not self.is_following(user):
            follow = Follow(follower_id=self.id, followed_id=user.id)
            db.session.add(follow)
    
    def unfollow(self, user):
        follow = self.following.filter_by(followed_id=user.id).first()
        if follow:
            db.session.delete(follow)
    
    def is_blocked(self, user):
        return self.blocked_users.filter_by(blocked_user_id=user.id).first() is not None
    
    def block(self, user):
        if not self.is_blocked(user):
            blocked = BlockedUser(user_id=self.id, blocked_user_id=user.id)
            db.session.add(blocked)
            
            # Unfollow if following
            if self.is_following(user):
                self.unfollow(user)
            if user.is_following(self):
                user.unfollow(self)
    
    def unblock(self, user):
        blocked = self.blocked_users.filter_by(blocked_user_id=user.id).first()
        if blocked:
            db.session.delete(blocked)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Post(db.Model):
    __tablename__ = 'posts'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    image = db.Column(db.LargeBinary)
    image_filename = db.Column(db.String(200))
    video = db.Column(db.LargeBinary)
    video_filename = db.Column(db.String(200))
    is_reel = db.Column(db.Boolean, default=False)
    is_private = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    views = db.Column(db.Integer, default=0)
    
    # Relationships
    comments = db.relationship('Comment', backref='post', lazy='dynamic')
    likes = db.relationship('Like', backref='post', lazy='dynamic')
    saves = db.relationship('Save', backref='post', lazy='dynamic')
    reposts = db.relationship('Repost', backref='post', lazy='dynamic')
    
    def __repr__(self):
        return f'<Post {self.id}>'

class Story(db.Model):
    __tablename__ = 'stories'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    image = db.Column(db.LargeBinary)
    image_filename = db.Column(db.String(200))
    video = db.Column(db.LargeBinary)
    video_filename = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=24))
    
    def __repr__(self):
        return f'<Story {self.id}>'

class Comment(db.Model):
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Comment {self.id}>'

class Like(db.Model):
    __tablename__ = 'likes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Like {self.id}>'

class Save(db.Model):
    __tablename__ = 'saves'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Save {self.id}>'

class Repost(db.Model):
    __tablename__ = 'reposts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Repost {self.id}>'

class Follow(db.Model):
    __tablename__ = 'follows'
    
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Follow {self.follower_id} to {self.followed_id}>'

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Message {self.id}>'

class Group(db.Model):
    __tablename__ = 'groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    profile_pic = db.Column(db.LargeBinary)
    profile_pic_filename = db.Column(db.String(200))
    unique_link = db.Column(db.String(50), unique=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Group settings
    allow_send_messages = db.Column(db.Boolean, default=True)
    allow_add_members = db.Column(db.Boolean, default=True)
    approve_new_members = db.Column(db.Boolean, default=False)
    
    # Relationships
    members = db.relationship('GroupMember', backref='group', lazy='dynamic')
    messages = db.relationship('GroupMessage', backref='group', lazy='dynamic')
    
    def generate_unique_link(self):
        import random
        import string
        self.unique_link = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
    
    def __repr__(self):
        return f'<Group {self.name}>'

class GroupMember(db.Model):
    __tablename__ = 'group_members'
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<GroupMember {self.group_id} - {self.user_id}>'

class GroupMessage(db.Model):
    __tablename__ = 'group_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<GroupMessage {self.id}>'

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    type = db.Column(db.String(50))
    related_id = db.Column(db.Integer)
    
    def __repr__(self):
        return f'<Notification {self.id}>'

class BlockedUser(db.Model):
    __tablename__ = 'blocked_users'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    blocked_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<BlockedUser {self.user_id} blocked {self.blocked_user_id}>'
