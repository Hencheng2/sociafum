-- schema.sql

-- Drop existing tables (order matters due to foreign key constraints)
-- Dropping tables in reverse order of creation to respect foreign key dependencies.
DROP TABLE IF EXISTS dismissed_suggestions;
DROP TABLE IF EXISTS blocked_users;
DROP TABLE IF EXISTS reports;
DROP TABLE IF EXISTS warnings;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS stories;
DROP TABLE IF EXISTS reels;
DROP TABLE IF EXISTS posts;
DROP TABLE IF EXISTS groups;
DROP TABLE IF EXISTS chat_messages;
DROP TABLE IF EXISTS chat_room_members;
DROP TABLE IF EXISTS chat_rooms;
DROP TABLE IF EXISTS friendships;
DROP TABLE IF EXISTS members;
DROP TABLE IF EXISTS users;

-- Table: users
-- Stores core user account information and general settings.
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    originalName TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin INTEGER DEFAULT 0,
    theme_preference TEXT DEFAULT 'light',
    chat_background_image_path TEXT,
    unique_key TEXT UNIQUE NOT NULL,
    password_reset_pending INTEGER DEFAULT 0,
    reset_request_timestamp TIMESTAMP,
    last_login_at TIMESTAMP,
    last_seen_at TIMESTAMP,
    language TEXT DEFAULT 'en',
    ban_status TEXT DEFAULT 'none',
    ban_reason TEXT,
    ban_starts_at TIMESTAMP,
    ban_ends_at TIMESTAMP,
    profile_locking INTEGER DEFAULT 0,
    posts_visibility TEXT DEFAULT 'public',
    allow_post_sharing INTEGER DEFAULT 1,
    allow_post_comments INTEGER DEFAULT 1,
    reels_visibility TEXT DEFAULT 'public',
    allow_reel_sharing INTEGER DEFAULT 1,
    allow_reel_comments INTEGER DEFAULT 1,
    notify_friend_requests INTEGER DEFAULT 1,
    notify_friend_acceptance INTEGER DEFAULT 1,
    notify_post_likes INTEGER DEFAULT 1,
    notify_new_messages INTEGER DEFAULT 1,
    notify_group_invites INTEGER DEFAULT 1,
    notify_comments INTEGER DEFAULT 1,
    notify_tags INTEGER DEFAULT 1
);

-- Table: members
-- Stores extended profile details, linked to a user.
CREATE TABLE members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    fullName TEXT NOT NULL,
    dateOfBirth TEXT,
    gender TEXT,
    contact TEXT,
    email TEXT UNIQUE,
    bio TEXT,
    profilePhoto TEXT,
    personalRelationshipDescription TEXT,
    maritalStatus TEXT,
    spouseNames TEXT,
    girlfriendNames TEXT,
    association TEXT,
    pronouns TEXT DEFAULT '',
    workInfo TEXT DEFAULT '',
    university TEXT DEFAULT '',
    secondary TEXT DEFAULT '',
    location TEXT DEFAULT '',
    socialLink TEXT DEFAULT '',
    websiteLink TEXT DEFAULT '',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Table: friendships
-- Manages friend requests and accepted friendships between users.
CREATE TABLE friendships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user1_id INTEGER NOT NULL,
    user2_id INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user1_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (user2_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user1_id, user2_id)
);

-- Table: chat_rooms
-- Represents a conversation, which can be a 1-on-1 chat or a group chat.
CREATE TABLE chat_rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    is_group INTEGER DEFAULT 0,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE NO ACTION
);

-- Table: chat_room_members
-- Junction table linking users to chat rooms, defining membership and roles.
CREATE TABLE chat_room_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_room_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_admin INTEGER DEFAULT 0,
    last_read_message_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chat_room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (chat_room_id, user_id)
);

-- Table: chat_messages
-- Stores individual messages sent within chat rooms.
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_room_id INTEGER NOT NULL,
    sender_id INTEGER NOT NULL,
    content TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    media_path TEXT,
    media_type TEXT,
    is_ai_message INTEGER DEFAULT 0,
    FOREIGN KEY (chat_room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Table: groups
-- Stores detailed information specifically for group chats.
CREATE TABLE groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    profilePhoto TEXT,
    created_by INTEGER NOT NULL,
    chat_room_id INTEGER UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ban_status TEXT DEFAULT 'none',
    ban_reason TEXT,
    ban_starts_at TIMESTAMP,
    ban_ends_at TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE NO ACTION,
    FOREIGN KEY (chat_room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE
);

-- Table: posts
-- Stores user-generated posts with text and optional media.
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    description TEXT,
    media_path TEXT,
    media_type TEXT,
    visibility TEXT DEFAULT 'public',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Table: reels
-- Stores user-generated short video/image reels.
CREATE TABLE reels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    description TEXT,
    media_path TEXT NOT NULL,
    media_type TEXT NOT NULL,
    audio_path TEXT,
    visibility TEXT DEFAULT 'public',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    views_count INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Table: stories
-- Stores temporary content (images, videos, voice notes) that expires.
CREATE TABLE stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    description TEXT,
    media_path TEXT NOT NULL,
    media_type TEXT NOT NULL,
    background_audio_path TEXT,
    visibility TEXT DEFAULT 'friends',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_sociafam_story INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Table: notifications
-- Stores all system and user-generated notifications for users.
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receiver_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    message TEXT NOT NULL,
    link TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_read INTEGER DEFAULT 0,
    FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Table: warnings
-- Stores warnings issued by administrators to users.
CREATE TABLE warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Table: reports
-- Stores reports made by users against other content (users, groups, posts, reels, stories).
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reported_by_user_id INTEGER NOT NULL,
    reported_item_type TEXT NOT NULL,
    reported_item_id INTEGER NOT NULL,
    reason TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',
    admin_notes TEXT,
    FOREIGN KEY (reported_by_user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Table: blocked_users
-- Records users who have been blocked by other users.
CREATE TABLE blocked_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blocker_id INTEGER NOT NULL,
    blocked_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (blocker_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (blocked_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (blocker_id, blocked_id)
);

-- Table: dismissed_suggestions
-- Records users dismissed from suggested users list by a user.
CREATE TABLE dismissed_suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    dismissed_user_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (dismissed_user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user_id, dismissed_user_id)
);
