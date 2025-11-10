-- ============================================================================
-- Messaging Schema Enhancements
-- ============================================================================
-- Purpose: Add folder management (Request/Main/Restricted) and email tracking
-- Database: engagement-platform-dev
-- ============================================================================

-- Add folder field to conversation_participants
-- Supports REQUEST, MAIN, RESTRICTED folders per user
ALTER TABLE conversation_participants 
ADD COLUMN IF NOT EXISTS folder VARCHAR DEFAULT 'MAIN';

COMMENT ON COLUMN conversation_participants.folder IS 'Conversation folder: REQUEST, MAIN, or RESTRICTED';

CREATE INDEX IF NOT EXISTS idx_conv_participants_folder ON conversation_participants(folder);

-- Add email notification tracking to messages
-- Tracks when email notification was sent for each message
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS email_notification_sent_at TIMESTAMPTZ;

COMMENT ON COLUMN messages.email_notification_sent_at IS 'Timestamp when email notification was sent to recipient';

CREATE INDEX IF NOT EXISTS idx_messages_email_notification ON messages(email_notification_sent_at);

-- ============================================================================
-- Summary of Changes
-- ============================================================================
-- 1. conversation_participants.folder - tracks which inbox folder (REQUEST/MAIN/RESTRICTED)
-- 2. messages.email_notification_sent_at - tracks email notification delivery
--
-- Usage Examples:
-- 
-- Move conversation to Restricted folder:
--   UPDATE conversation_participants 
--   SET folder = 'RESTRICTED' 
--   WHERE conversation_id = ? AND person_id = ?;
--
-- Get conversations by folder:
--   SELECT * FROM conversation_participants 
--   WHERE person_id = ? AND folder = 'MAIN';
--
-- Mark email notification as sent:
--   UPDATE messages 
--   SET email_notification_sent_at = NOW() 
--   WHERE id = ?;
-- ============================================================================
