-- schema.sql

-- Drop existing tables (order matters due to foreign keys)
DROP TABLE IF EXISTS game_invitations;
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


-- Create users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    originalName TEXT NOT NULL, -- Real name of the user, for display
    password_hash TEXT NOT NULL,
    is_admin INTEGER DEFAULT 0, -- 0 for regular user, 1 for admin
    theme_preference TEXT DEFAULT 'light', -- 'light' or 'dark'
    chat_background_image_path TEXT, -- Path to custom chat background for user
    unique_key TEXT UNIQUE NOT NULL, -- For password recovery (4 chars: 2 letters, 2 numbers)
    password_reset_pending INTEGER DEFAULT 0, -- 1 if admin/user initiated reset, 0 otherwise
    reset_request_timestamp TIMESTAMP, -- Timestamp of user's reset request (for auto-initiation)
    last_login_at TIMESTAMP, -- Timestamp of last successful login
    last_seen_at TIMESTAMP, -- Timestamp of last activity/seen
    language TEXT DEFAULT 'en', -- User's preferred language

    -- Ban related fields for users
    ban_status TEXT DEFAULT 'none', -- 'none', 'temporary', 'permanent'
    ban_reason TEXT,
    ban_starts_at TIMESTAMP,
    ban_ends_at TIMESTAMP,

    -- Privacy and Notification Settings (from settings.html)
    profile_locking INTEGER DEFAULT 0, -- 0 for public, 1 for private/friends-only
    posts_visibility TEXT DEFAULT 'public', -- 'public', 'friends', 'private'
    allow_post_sharing INTEGER DEFAULT 1, -- 0 for false, 1 for true
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

-- Create members table (for extended profile details, linked to users)
CREATE TABLE members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE, -- Foreign key to users table, can be NULL initially if added by another member
    fullName TEXT NOT NULL,
    dateOfBirth TEXT,
    gender TEXT,
    contact TEXT,
    email TEXT UNIQUE, -- Allow for login with email too
    bio TEXT,
    profilePhoto TEXT, -- Path to profile photo
    personalRelationshipDescription TEXT,
    maritalStatus TEXT, -- e.g., 'Single', 'Married', 'Engaged', 'Divorced', 'Widowed'
    spouseNames TEXT, -- For Married/Divorced/Widowed
    girlfriendNames TEXT, -- For Engaged (or partner names)
    association TEXT, -- e.g., 'Mother', 'Father', 'Brother', 'Sister', 'Friend' (for relationships within the family tree)
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create friendships table
CREATE TABLE friendships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user1_id INTEGER NOT NULL,
    user2_id INTEGER NOT NULL,
    status TEXT DEFAULT 'pending', -- 'pending', 'accepted', 'declined'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user1_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (user2_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user1_id, user2_id) -- Ensures only one unique friendship entry
);

-- Create chat_rooms table (can be 1-on-1 or group chats)
CREATE TABLE chat_rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    is_group INTEGER DEFAULT 0, -- 0 for 1-on-1, 1 for group chat
    created_by INTEGER NOT NULL, -- The user who initiated the chat/created the group
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE NO ACTION -- Don't delete user if they created a group/chat
);

-- Create chat_room_members table (junction table for chat rooms and users)
CREATE TABLE chat_room_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_room_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_admin INTEGER DEFAULT 0, -- 1 if user is admin of this specific chat room (only relevant for groups)
    last_read_message_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- To track unread messages
    FOREIGN KEY (chat_room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (chat_room_id, user_id) -- Ensures a user can only be in a room once
);

-- Create chat_messages table
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_room_id INTEGER NOT NULL,
    sender_id INTEGER NOT NULL,
    content TEXT, -- Message text (can be NULL if only media)
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    media_path TEXT, -- Path to media file (NULL if no media)
    media_type TEXT, -- 'image', 'video', 'audio' (NULL if no media)
    is_ai_message INTEGER DEFAULT 0, -- 1 if message is from AI, 0 otherwise (useful for support chat)
    FOREIGN KEY (chat_room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create groups table (for detailed group info, linked to a chat_room)
CREATE TABLE groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    profilePhoto TEXT, -- Path to group profile photo
    created_by INTEGER NOT NULL, -- User who created the group
    chat_room_id INTEGER UNIQUE NOT NULL, -- One-to-one relationship with a chat_room
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Ban related fields for groups
    ban_status TEXT DEFAULT 'none', -- 'none', 'temporary', 'permanent'
    ban_reason TEXT,
    ban_starts_at TIMESTAMP,
    ban_ends_at TIMESTAMP,

    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE NO ACTION,
    FOREIGN KEY (chat_room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE
);

-- Create posts table
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    description TEXT,
    media_path TEXT, -- Path to image/video
    media_type TEXT, -- 'image' or 'video'
    visibility TEXT DEFAULT 'public', -- 'public', 'friends', 'private'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create reels table
CREATE TABLE reels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    description TEXT,
    media_path TEXT NOT NULL, -- Path to video/image reel content
    media_type TEXT NOT NULL, -- 'video' or 'image'
    audio_path TEXT, -- Optional: path to background audio for image reels/silent videos
    visibility TEXT DEFAULT 'public', -- Reels are typically public
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    views_count INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create stories table (temporary content, expires after 24 hours)
CREATE TABLE stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    description TEXT,
    media_path TEXT NOT NULL, -- Path to image, video, or voice note
    media_type TEXT NOT NULL, -- 'image', 'video', 'audio' (for voice notes)
    background_audio_path TEXT, -- Optional background audio for images/videos
    visibility TEXT DEFAULT 'friends', -- Stories are typically visible to friends
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL, -- Automatically expires, typically 24 hours after creation
    is_sociafam_story INTEGER DEFAULT 0, -- 1 if posted by Admin as "SociaFam" story
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create statuses table (For 24-hour video statuses, essentially a simplified story for current profile)
-- Note: Functionality partially overlapping with 'stories' but kept for explicit separate management
CREATE TABLE statuses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);


-- Create notifications table
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receiver_id INTEGER NOT NULL,
    type TEXT NOT NULL, -- e.g., 'friend_request', 'friend_accepted', 'message_received', 'warning', 'system_message', 'group_invite', 'post_like', 'comment_on_post'
    message TEXT NOT NULL,
    link TEXT, -- Optional URL to redirect to
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_read INTEGER DEFAULT 0, -- 0 for unread, 1 for read
    FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create warnings table (for admin-issued warnings)
CREATE TABLE warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active', -- 'active', 'resolved'
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create reports table (for user-reported content/users/groups)
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reported_by_user_id INTEGER NOT NULL,
    reported_item_type TEXT NOT NULL, -- 'user', 'group', 'post', 'reel', 'story'
    reported_item_id INTEGER NOT NULL, -- ID of the reported item/user/group
    reason TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending', -- 'pending', 'handled', 'ignored'
    admin_notes TEXT, -- Admin's notes after handling the report
    FOREIGN KEY (reported_by_user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create blocked_users table
CREATE TABLE blocked_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blocker_id INTEGER NOT NULL,
    blocked_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (blocker_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (blocked_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (blocker_id, blocked_id) -- A user can only block another user once
);

-- Create game_invitations table
CREATE TABLE game_invitations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    game_name TEXT NOT NULL,
    game_id TEXT, -- Optional: ID of an ongoing game instance
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending', -- 'pending', 'accepted', 'declined'
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
);

