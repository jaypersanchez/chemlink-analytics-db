-- ============================================================================
-- Engagement Platform Messaging & Chat Extension Schema
-- ============================================================================
-- Purpose: Create messaging and chat conversation tables
-- Database: engagement-platform-dev (or engagement-platform-prod)
-- Note: persons table already exists, so it's excluded from this script
-- ============================================================================

-- Drop existing tables if they exist (in reverse dependency order)
DROP TABLE IF EXISTS message_reactions CASCADE;
DROP TABLE IF EXISTS message_attachments CASCADE;
DROP TABLE IF EXISTS message_reads CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS conversation_participants CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;

-- ============================================================================
-- CONVERSATIONS TABLE
-- ============================================================================
-- Supports direct (2-person) and group conversations
-- metadata stores preferences, pinned items, topics

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_type VARCHAR NOT NULL,  -- 'DIRECT' or 'GROUP'
    subject VARCHAR,                      -- Optional subject/title for group chats
    created_by UUID NOT NULL REFERENCES persons(id),
    metadata JSONB,                       -- Stores preferences, pinned items, topics
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,                -- When conversation was closed/archived
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_conversations_created_by ON conversations(created_by);
CREATE INDEX idx_conversations_type ON conversations(conversation_type);
CREATE INDEX idx_conversations_created_at ON conversations(created_at);

COMMENT ON TABLE conversations IS 'Supports direct (2-person) and group conversations';
COMMENT ON COLUMN conversations.metadata IS 'Stores preferences, pinned items, topics';
COMMENT ON COLUMN conversations.conversation_type IS 'Values: DIRECT, GROUP';


-- ============================================================================
-- CONVERSATION_PARTICIPANTS TABLE
-- ============================================================================
-- Tracks who is in each conversation
-- notification_level toggles mute/unmute
-- last_read_at tracks read receipts

CREATE TABLE conversation_participants (
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    person_id UUID NOT NULL REFERENCES persons(id),
    role VARCHAR,                         -- Role in conversation (e.g., 'ADMIN', 'MEMBER')
    notification_level VARCHAR,           -- Mute/unmute setting
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    pinned_at TIMESTAMPTZ,                -- When user pinned this conversation
    last_read_at TIMESTAMPTZ,             -- For read receipts and badge counts
    left_at TIMESTAMPTZ,                  -- When user left the conversation
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    PRIMARY KEY (conversation_id, person_id)
);

CREATE INDEX idx_conv_participants_person ON conversation_participants(person_id);
CREATE INDEX idx_conv_participants_last_read ON conversation_participants(last_read_at);

COMMENT ON TABLE conversation_participants IS 'Tracks participants in conversations with roles and preferences';
COMMENT ON COLUMN conversation_participants.notification_level IS 'Toggles mute/unmute';
COMMENT ON COLUMN conversation_participants.last_read_at IS 'For read receipts and badge counts';


-- ============================================================================
-- MESSAGES TABLE
-- ============================================================================
-- All messages in conversations
-- message_type: text, file, system, notification
-- status: sent, delivered, read, failed

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES persons(id),
    message_type VARCHAR NOT NULL,        -- 'TEXT', 'FILE', 'SYSTEM', 'NOTIFICATION'
    body TEXT,                             -- Message content
    media_keys JSONB,                      -- References to files/attachments
    status VARCHAR,                        -- 'SENT', 'DELIVERED', 'READ', 'FAILED'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_sender ON messages(sender_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_messages_type ON messages(message_type);

COMMENT ON TABLE messages IS 'All messages in conversations with delivery tracking';
COMMENT ON COLUMN messages.message_type IS 'Values: TEXT, FILE, SYSTEM, NOTIFICATION';
COMMENT ON COLUMN messages.status IS 'Tracks delivery: SENT, DELIVERED, READ, FAILED';


-- ============================================================================
-- MESSAGE_READS TABLE
-- ============================================================================
-- Tracks when each person read each message

CREATE TABLE message_reads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    person_id UUID NOT NULL REFERENCES persons(id),
    read_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(message_id, person_id)
);

CREATE INDEX idx_message_reads_message ON message_reads(message_id);
CREATE INDEX idx_message_reads_person ON message_reads(person_id);
CREATE INDEX idx_message_reads_read_at ON message_reads(read_at);

COMMENT ON TABLE message_reads IS 'Tracks individual message read receipts';


-- ============================================================================
-- MESSAGE_ATTACHMENTS TABLE
-- ============================================================================
-- File attachments for messages

CREATE TABLE message_attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    storage_key VARCHAR NOT NULL,         -- S3 key or storage reference
    mime_type VARCHAR,                     -- File type
    file_size_bytes BIGINT,                -- File size
    metadata JSONB,                        -- Additional file metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_message_attachments_message ON message_attachments(message_id);
CREATE INDEX idx_message_attachments_created_at ON message_attachments(created_at);

COMMENT ON TABLE message_attachments IS 'File attachments linked to messages';


-- ============================================================================
-- MESSAGE_REACTIONS TABLE
-- ============================================================================
-- Emoji reactions to messages

CREATE TABLE message_reactions (
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    person_id UUID NOT NULL REFERENCES persons(id),
    reaction_type VARCHAR NOT NULL,        -- Emoji or reaction identifier
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    PRIMARY KEY (message_id, person_id)
);

CREATE INDEX idx_message_reactions_message ON message_reactions(message_id);
CREATE INDEX idx_message_reactions_person ON message_reactions(person_id);

COMMENT ON TABLE message_reactions IS 'Emoji reactions on messages';


-- ============================================================================
-- SUMMARY
-- ============================================================================
-- Tables created:
-- 1. conversations              - Main conversation threads
-- 2. conversation_participants  - Who's in each conversation
-- 3. messages                   - All messages
-- 4. message_reads              - Read receipts
-- 5. message_attachments        - File attachments
-- 6. message_reactions          - Emoji reactions
--
-- Note: persons table is referenced but not created (already exists)
--
-- Features supported:
-- - Direct (1-on-1) and group conversations
-- - Message delivery tracking (sent/delivered/read/failed)
-- - Read receipts
-- - File attachments
-- - Emoji reactions
-- - Conversation archiving/closing
-- - Notification preferences (mute/unmute)
-- - Pinned conversations
-- - Conversation metadata (preferences, pinned items, topics)
-- ============================================================================
