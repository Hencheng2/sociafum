-- schema.sql

-- Drop existing tables (order matters due to foreign key constraints)
-- Dropping tables in reverse order of creation to respect foreign key dependencies.
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
    username TEXT UNIQUE NOT NULL,           -- Unique username for login and profile URLs
    originalName TEXT NOT NULL,             -- User's real name for display
    password_hash TEXT NOT NULL,            -- Hashed password for security
    is_admin INTEGER DEFAULT 0,             -- 0 for regular user, 1 for administrator
    theme_preference TEXT DEFAULT 'light',  -- 'light' or 'dark' theme choice
    chat_background_image_path TEXT,        -- Path to a custom chat background image
    unique_key TEXT UNIQUE NOT NULL,        -- Unique key for password recovery (e.g., "AB12")
    password_reset_pending INTEGER DEFAULT 0, -- 1 if a password reset has been initiated
    reset_request_timestamp TIMESTAMP,      -- When the password reset request was made
    last_login_at TIMESTAMP,                -- Timestamp of the last successful login
    last_seen_at TIMESTAMP,                 -- Timestamp of the last user activity
    language TEXT DEFAULT 'en',             -- User's preferred language

    -- Ban-related fields for moderation
    ban_status TEXT DEFAULT 'none',         -- 'none', 'temporary', 'permanent'
    ban_reason TEXT,                        -- Reason for the ban
    ban_starts_at TIMESTAMP,                -- When the ban started
    ban_ends_at TIMESTAMP,                  -- When a temporary ban ends

    -- Privacy and Notification Settings (controlled via settings.html)
    profile_locking INTEGER DEFAULT 0,      -- 0 for public, 1 for private/friends-only visibility
    posts_visibility TEXT DEFAULT 'public', -- 'public', 'friends', 'private' for posts
    allow_post_sharing INTEGER DEFAULT 1,   -- 0 for disabled, 1 for enabled
    allow_post_comments INTEGER DEFAULT 1,  -- 0 for disabled, 1 for enabled
    reels_visibility TEXT DEFAULT 'public', -- 'public', 'friends', 'private' for reels
    allow_reel_sharing INTEGER DEFAULT 1,   -- 0 for disabled, 1 for enabled
    allow_reel_comments INTEGER DEFAULT 1,  -- 0 for disabled, 1 for enabled
    notify_friend_requests INTEGER DEFAULT 1, -- 0 for disabled, 1 for enabled
    notify_friend_acceptance INTEGER DEFAULT 1, -- 0 for disabled, 1 for enabled
    notify_post_likes INTEGER DEFAULT 1,    -- 0 for disabled, 1 for enabled
    notify_new_messages INTEGER DEFAULT 1,  -- 0 for disabled, 1 for enabled
    notify_group_invites INTEGER DEFAULT 1, -- 0 for disabled, 1 for enabled
    notify_comments INTEGER DEFAULT 1,      -- 0 for disabled, 1 for enabled
    notify_tags INTEGER DEFAULT 1           -- 0 for disabled, 1 for enabled
);

-- Table: members
-- Stores extended profile details, linked to a user.
CREATE TABLE members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,                 -- Foreign key to users table (one-to-one)
    fullName TEXT NOT NULL,                 -- Full name of the member
    dateOfBirth TEXT,                       -- Date of birth (stored as TEXT for simplicity)
    gender TEXT,                            -- 'Male', 'Female', 'Other'
    contact TEXT,                           -- User's contact number
    email TEXT UNIQUE,                      -- User's email, can be used for login
    bio TEXT,                               -- Short biography
    profilePhoto TEXT,                      -- Path to the user's profile photo
    personalRelationshipDescription TEXT,   -- User's own description of relationships
    maritalStatus TEXT,                     -- 'Single', 'Married', 'Engaged', 'Divorced', 'Widowed'
    spouseNames TEXT,                       -- Names of spouses if applicable
    girlfriendNames TEXT,                   -- Names of partners if applicable (e.g., for 'Engaged' status)
    association TEXT,                       -- For family tree relationships (e.g., 'Mother', 'Brother')
    -- ADDED COLUMNS
    pronouns TEXT DEFAULT '',               -- User's preferred pronouns
    workInfo TEXT DEFAULT '',               -- User's work/employment information
    university TEXT DEFAULT '',             -- User's university information
    secondary TEXT DEFAULT '',              -- User's secondary school information
    location TEXT DEFAULT '',               -- User's current location
    socialLink TEXT DEFAULT '',             -- Link to other social media profiles
    websiteLink TEXT DEFAULT '',            -- Link to personal website/blog
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Table: friendships
-- Manages friend requests and accepted friendships between users.
CREATE TABLE friendships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user1_id INTEGER NOT NULL,              -- ID of the first user in the friendship
    user2_id INTEGER NOT NULL,              -- ID of the second user in the friendship
    status TEXT DEFAULT 'pending',          -- 'pending', 'accepted', 'declined'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- When the friendship was created/updated
    FOREIGN KEY (user1_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (user2_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user1_id, user2_id)             -- Ensures unique pair, regardless of order (handled in app logic)
);

-- Table: chat_rooms
-- Represents a conversation, which can be a 1-on-1 chat or a group chat.
CREATE TABLE chat_rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    is_group INTEGER DEFAULT 0,             -- 0 for 1-on-1 chat, 1 for group chat
    created_by INTEGER NOT NULL,            -- The user who initiated the chat or created the group
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE NO ACTION -- Do not delete user if they created a chat room
);

-- Table: chat_room_members
-- Junction table linking users to chat rooms, defining membership and roles.
CREATE TABLE chat_room_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_room_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_admin INTEGER DEFAULT 0,             -- 1 if user is an admin of this specific group chat
    last_read_message_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Tracks messages read by this user in this chat
    FOREIGN KEY (chat_room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (chat_room_id, user_id)          -- Ensures a user can only be a member of a chat room once
);

-- Table: chat_messages
-- Stores individual messages sent within chat rooms.
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_room_id INTEGER NOT NULL,
    sender_id INTEGER NOT NULL,
    content TEXT,                           -- Message text (can be NULL if only media is sent)
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    media_path TEXT,                        -- Path to an attached media file (image, video, audio)
    media_type TEXT,                        -- 'image', 'video', 'audio'
    is_ai_message INTEGER DEFAULT 0,        -- 1 if generated by AI (not used as AI is removed)
    FOREIGN KEY (chat_room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Table: groups
-- Stores detailed information specifically for group chats.
CREATE TABLE groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                     -- Name of the group
    description TEXT,                       -- Group description
    profilePhoto TEXT,                      -- Path to the group's profile photo
    created_by INTEGER NOT NULL,            -- The user who created this group
    chat_room_id INTEGER UNIQUE NOT NULL,   -- One-to-one link to its corresponding chat_room
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    unique_join_link TEXT UNIQUE,

    -- Ban-related fields for group moderation
    ban_status TEXT DEFAULT 'none',         -- 'none', 'temporary', 'permanent'
    ban_reason TEXT,                        -- Reason for the group ban
    ban_starts_at TIMESTAMP,                -- When the ban started
    ban_ends_at TIMESTAMP,                  -- When a temporary ban ends

    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE NO ACTION,
    FOREIGN KEY (chat_room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE
);

-- Table: posts
-- Stores user-generated posts with text and optional media.
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    description TEXT,                       -- Text content of the post
    media_path TEXT,                        -- Path to an attached image or video
    media_type TEXT,                        -- 'image' or 'video'
    visibility TEXT DEFAULT 'public',       -- 'public', 'friends', 'private'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    likes_count INTEGER DEFAULT 0,          -- Number of likes on the post
    comments_count INTEGER DEFAULT 0,       -- Number of comments on the post
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Table: reels
-- Stores user-generated short video/image reels.
CREATE TABLE reels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    description TEXT,                       -- Text description for the reel
    media_path TEXT NOT NULL,               -- Path to the reel's video or image content
    media_type TEXT NOT NULL,               -- 'video' or 'image'
    audio_path TEXT,                        -- Optional background audio for image reels or silent videos
    visibility TEXT DEFAULT 'public',       -- Reels are typically public
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    views_count INTEGER DEFAULT 0,          -- Number of times the reel has been viewed
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Table: stories
-- Stores temporary content (images, videos, voice notes) that expires.
CREATE TABLE stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    description TEXT,                       -- Optional text description for the story
    media_path TEXT NOT NULL,               -- Path to the story's media (image, video, or audio)
    media_type TEXT NOT NULL,               -- 'image', 'video', 'audio' (for voice notes)
    background_audio_path TEXT,             -- Optional background audio for image/video stories
    visibility TEXT DEFAULT 'friends',      -- Stories are typically visible to friends
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,          -- The time when the story will automatically expire (e.g., 24 hours after creation)
    is_sociafam_story INTEGER DEFAULT 0,    -- 1 if this is a special story posted by the Admin
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Table: notifications
-- Stores all system and user-generated notifications for users.
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receiver_id INTEGER NOT NULL,           -- The user who receives the notification
    type TEXT NOT NULL,                     -- e.g., 'friend_request', 'message_received', 'warning'
    message TEXT NOT NULL,                  -- The content of the notification
    link TEXT,                              -- Optional URL to redirect user upon clicking notification
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_read INTEGER DEFAULT 0,              -- 0 for unread, 1 for read
    FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Table: warnings
-- Stores warnings issued by administrators to users.
CREATE TABLE warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,               -- The user who received the warning
    title TEXT NOT NULL,                    -- Short title of the warning
    description TEXT,                       -- Detailed description/reason for the warning
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',           -- 'active' or 'resolved'
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Table: reports
-- Stores reports made by users against other content (users, groups, posts, reels, stories).
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reported_by_user_id INTEGER NOT NULL,   -- The user who filed the report
    reported_item_type TEXT NOT NULL,       -- 'user', 'group', 'post', 'reel', 'story'
    reported_item_id INTEGER NOT NULL,      -- The ID of the specific item being reported
    reason TEXT NOT NULL,                   -- The reason for the report
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',          -- 'pending', 'handled', 'ignored'
    admin_notes TEXT,                       -- Notes added by an admin after reviewing the report
    FOREIGN KEY (reported_by_user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Table: blocked_users
-- Records users who have been blocked by other users.
CREATE TABLE blocked_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blocker_id INTEGER NOT NULL,            -- The user who performed the blocking
    blocked_id INTEGER NOT NULL,            -- The user who was blocked
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (blocker_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (blocked_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (blocker_id, blocked_id)         -- Ensures a user can only block another user once
);
