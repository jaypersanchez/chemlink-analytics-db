# Chat/Messaging System - Handoff Document

**Project**: ChemLink Engagement Platform - Chat Testing Interface  
**Date**: November 10, 2025  
**Status**: ✅ Completed and Committed (commit: 73e2549)

---

## 📋 Overview

This handoff covers the complete chat/messaging testing infrastructure built to test direct and group chat functionality against the `engagement-platform-dev` database.

### What Was Built

1. **2-Panel Direct Chat Interface** - Test 1-on-1 messaging
2. **3-Panel Group Chat Interface** - Test group messaging with dynamic participant management
3. **Backend API** - Flask server with messaging endpoints
4. **Database Integration** - Full integration with PostgreSQL messaging schema

---

## 🗄️ Database Requirements

### Required Database

- **Database Name**: `engagement-platform-dev`
- **Host**: `localhost`
- **Port**: `5433`
- **User**: `dev`
- **Password**: `dev`

### Required Tables

The following tables **MUST exist** in the target database:

#### Core Tables

```sql
-- Conversations
conversations (
    id UUID PRIMARY KEY,
    conversation_type VARCHAR NOT NULL,  -- 'DIRECT' or 'GROUP'
    created_by UUID NOT NULL,            -- REQUIRED: person who created it
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ
)

-- Conversation Participants (composite PK, NO id column)
conversation_participants (
    conversation_id UUID NOT NULL,
    person_id UUID NOT NULL,
    role VARCHAR,
    notification_level VARCHAR,
    is_admin BOOLEAN NOT NULL DEFAULT false,
    pinned_at TIMESTAMPTZ,
    last_read_at TIMESTAMPTZ,
    left_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    folder VARCHAR DEFAULT 'MAIN',
    PRIMARY KEY (conversation_id, person_id)
)

-- Messages
messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL,
    sender_id UUID NOT NULL,
    message_type VARCHAR NOT NULL,  -- 'TEXT', 'IMAGE', 'VIDEO', 'AUDIO', 'FILE', 'SYSTEM'
    body TEXT,
    status VARCHAR NOT NULL,        -- 'SENT', 'DELIVERED', 'READ'
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
)

-- Message Reads
message_reads (
    message_id UUID NOT NULL,
    person_id UUID NOT NULL,
    read_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (message_id, person_id)  -- or similar unique constraint
)

-- Message Reactions
message_reactions (
    message_id UUID NOT NULL,
    person_id UUID NOT NULL,
    reaction_type VARCHAR NOT NULL,  -- Emoji or reaction code
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (message_id, person_id)  -- or similar unique constraint
)

-- Message Attachments
message_attachments (
    id UUID PRIMARY KEY,
    message_id UUID NOT NULL,
    storage_key VARCHAR NOT NULL,    -- Filename on disk
    mime_type VARCHAR NOT NULL,
    file_size_bytes BIGINT,
    metadata JSONB,                  -- Must contain: {"file_name": "original.ext"}
    created_at TIMESTAMPTZ NOT NULL
)

-- Persons (must exist for user lookups)
persons (
    id UUID PRIMARY KEY,
    first_name VARCHAR,
    last_name VARCHAR,
    email VARCHAR
)
```

### Schema Location

The messaging schema can be found at:
```
/Users/jayperconstantinosanchez/projects/chemlink-analytics-db/schema/engagement_messaging_extension.sql
```

### How to Apply Schema

```bash
# Apply the messaging schema to a new database
cd /Users/jayperconstantinosanchez/projects/chemlink-analytics-db
PGPASSWORD=dev psql -h localhost -p 5433 -U dev -d engagement-platform-dev \
  -f schema/engagement_messaging_extension.sql
```

---

## 🚀 Application Setup

### Location

```
/Users/jayperconstantinosanchez/projects/chemlink-analytics-db/chat-app-test/
```

### Files Structure

```
chat-app-test/
├── app.py                          # Main Flask application (ACTIVE)
├── app_v2.py                       # Secondary version (not used)
├── start.sh                        # Start server script
├── stop.sh                         # Stop server script
├── templates/
│   ├── chat.html                   # 2-panel direct chat UI
│   ├── group-chat.html             # 3-panel group chat UI (NEW)
│   └── inbox.html                  # Conversation list (future)
├── uploads/                        # File upload storage
└── IMPLEMENTATION_GUIDE.md         # Technical documentation
```

### Dependencies

```bash
# Python packages required
pip install flask flask-cors psycopg2-binary
```

Or via requirements.txt:
```bash
pip install -r ../requirements.txt
```

---

## 🎮 Running the Application

### Start Server

```bash
cd /Users/jayperconstantinosanchez/projects/chemlink-analytics-db/chat-app-test
./start.sh
```

**Output:**
```
🚀 Starting ChemLink Chat Test...

📋 Configuration:
  ✓ Flask app: app.py (original working version)
  ✓ Port: 5005
  ✓ Database: engagement-platform-dev (localhost:5433)
  ✓ Users: Jay Sanchez ↔ David Uy
  ✓ Features: File uploads (images/audio), Reactions, Read receipts

✅ Chat app started successfully!
   PID: 1292
   URL: http://localhost:5005
   Logs: tail -f server.log
```

### Stop Server

```bash
./stop.sh
```

### Access URLs

- **2-Panel Direct Chat**: http://localhost:5005
- **3-Panel Group Chat**: http://localhost:5005/group-test

---

## 👥 Test Users

These user IDs are hardcoded in the application for testing:

### Hardcoded Users (2-Panel Direct Chat)

```python
JAYPER_ID = '78033fa0-db62-43f9-8e00-02488aeb0ed5'      # jsanchez@nmblr.ai
DAVID_ID = '24c5aed9-b257-4d33-99d1-2b7e297a2634'       # David Uy (old ID)
CONVERSATION_ID = 'c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c' # Pre-created conversation
```

### Dynamic Users (3-Panel Group Chat)

```javascript
JAY:   '78033fa0-db62-43f9-8e00-02488aeb0ed5'  // jsanchez@nmblr.ai (Initiator)
DAVID: '5fda75f7-17b1-44d8-9ca5-d070a8cdb247'  // daviduy@nmblr.ai
TIN:   'e2663e4b-61f4-4b51-9c10-ed0242c693bc'  // ktayco@nmblr.ai
```

### ⚠️ Important Note

These user IDs **MUST exist** in the `persons` table in your database. If deploying to a new environment, you must either:

1. Create these users in the `persons` table, OR
2. Update the user IDs in the code to match existing users

---

## 🔌 API Endpoints

### Direct Chat Endpoints (Original)

```
GET  /api/messages
     Query: None (uses hardcoded CONVERSATION_ID)
     Returns: All messages with read status and reactions

POST /api/send
     Body: { sender_id, body } OR multipart/form-data with file
     Returns: { id, created_at }

POST /api/mark-read
     Body: { person_id, message_ids: [] }
     Returns: { status, marked_count }

POST /api/react
     Body: { message_id, person_id, reaction_type }
     Returns: { status }

POST /api/remove-reaction
     Body: { message_id, person_id }
     Returns: { status }
```

### Group Chat Endpoints (New)

```
POST /api/conversations/start
     Body: {
       sender_id: UUID,
       recipient_ids: [UUID, ...],
       conversation_type: 'DIRECT' | 'GROUP'
     }
     Returns: { conversation_id, conversation_type, participants }

GET  /api/conversations/<conversation_id>/messages
     Query: user_id=UUID
     Returns: { messages: [...] }

POST /api/conversations/<conversation_id>/messages
     Body: { sender_id: UUID, body: string }
     Returns: { id, created_at }

POST /api/conversations/<conversation_id>/participants
     Body: { person_id: UUID, added_by: UUID }
     Returns: { status, person_id }

DELETE /api/conversations/<conversation_id>/participants/<person_id>
     Returns: { status, person_id }
```

---

## ✨ Features Implemented

### 2-Panel Direct Chat (`/`)
- ✅ Side-by-side chat windows (Jay Sanchez ↔ David Uy)
- ✅ Real-time message sync (2-second polling)
- ✅ Text messaging with Enter key support
- ✅ File uploads (images, audio, video, files)
- ✅ Message reactions (emoji)
- ✅ Read receipts (✓ sent, ✓✓ read)
- ✅ Auto-scroll to latest message

### 3-Panel Group Chat (`/group-test`)
- ✅ 3 side-by-side panels (Jay, David, Tin)
- ✅ Create new GROUP conversations
- ✅ Add participants dynamically (➕ Add Tin)
- ✅ Remove participants dynamically (➖ Remove David/Tin)
- ✅ System messages for join/leave events
- ✅ Sender name display on received messages
- ✅ Individual panel enable/disable based on participation
- ✅ Real-time message sync across all active participants

---

## 🔧 Configuration

### Database Configuration (app.py)

```python
def get_db():
    """Connect to engagement-platform-dev"""
    return psycopg2.connect(
        host='localhost',
        port=5433,
        database='engagement-platform-dev',
        user='dev',
        password='dev',
        cursor_factory=psycopg2.extras.RealDictCursor
    )
```

### File Upload Configuration

```python
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
```

### Server Configuration

```python
app.run(debug=True, host='0.0.0.0', port=5005)
```

---

## 🧪 Testing Guide

### Test Direct Chat (2-Panel)

1. Open http://localhost:5005
2. Type in left panel (as Jay) → appears in both panels
3. Type in right panel (as David) → appears in both panels
4. Upload a file → shows in both panels with preview
5. Click reaction icon → adds emoji to message
6. Watch read receipts change from ✓ to ✓✓

### Test Group Chat (3-Panel)

1. Open http://localhost:5005/group-test
2. Click **✨ Create Group Chat**
3. Type in Panel 1 (Jay) → appears in Panels 1 & 2
4. Type in Panel 2 (David) → appears in Panels 1 & 2
5. Click **➕ Add Tin**
6. Watch system message: "Tin Tayco joined the group"
7. Type in Panel 3 (Tin) → appears in all 3 panels
8. Click **➖ Remove Tin**
9. Watch system message: "Tin Tayco left the group"
10. Panel 3 becomes disabled

---

## 📝 Known Issues & Limitations

### Current Limitations

1. **Hardcoded User IDs**: Test users are hardcoded in the UI
2. **No Authentication**: No login system (for testing only)
3. **Polling Only**: Uses 2-second polling instead of WebSockets
4. **No Typing Indicators**: Not implemented yet
5. **No Message Editing**: Cannot edit sent messages
6. **No Message Deletion**: Cannot delete messages
7. **File Upload Storage**: Files stored locally in `uploads/` folder

### Future Enhancements

- [ ] WebSocket support for real-time updates
- [ ] User authentication/login
- [ ] Message search
- [ ] Conversation list (inbox view)
- [ ] Typing indicators
- [ ] Message editing/deletion
- [ ] Better file management (cloud storage)
- [ ] Push notifications
- [ ] Message threads/replies
- [ ] Read receipts per user in group chats

---

## 🚨 Deployment Checklist

When deploying to a new environment:

### Database Setup
- [ ] PostgreSQL 12+ installed
- [ ] Database `engagement-platform-dev` created
- [ ] User `dev` with password `dev` exists (or update credentials)
- [ ] Run `schema/engagement_messaging_extension.sql`
- [ ] Verify all required tables exist
- [ ] Insert test users into `persons` table

### Application Setup
- [ ] Python 3.9+ installed
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Create `uploads/` directory: `mkdir -p uploads`
- [ ] Update database credentials in `app.py` if needed
- [ ] Update user IDs in code if using different test users
- [ ] Test connection: `python -c "from app import get_db; get_db()"`

### Running
- [ ] Run `./start.sh`
- [ ] Verify server starts on port 5005
- [ ] Check logs: `tail -f server.log`
- [ ] Access http://localhost:5005
- [ ] Access http://localhost:5005/group-test
- [ ] Test sending messages in both interfaces

### Troubleshooting
- [ ] Check database is running: `psql -h localhost -p 5433 -U dev -d engagement-platform-dev`
- [ ] Verify tables exist: `\dt` in psql
- [ ] Check server logs: `tail -f server.log`
- [ ] Stop/restart server: `./stop.sh && ./start.sh`

---

## 📚 Related Documentation

- **Implementation Guide**: `IMPLEMENTATION_GUIDE.md` - Technical details and architecture
- **Schema Files**: `../schema/engagement_messaging_extension.sql`
- **Sample Data**: `../sample_data/sample_chat_conversation.sql`
- **Database Docs**: `../docs/` - PlantUML diagrams and sequence flows

---

## 🔗 Git Repository

**Commit**: `73e2549` - Add 3-panel group chat testing interface  
**Branch**: `main`  
**Location**: `/Users/jayperconstantinosanchez/projects/chemlink-analytics-db/chat-app-test/`

### Recent Changes (This Cycle)

```
73e2549 Add 3-panel group chat testing interface
  - Created group-chat.html: 3-panel interface
  - Added 4 new group chat API endpoints
  - Dynamic participant add/remove
  - System messages for join/leave
  - Real-time message sync
```

---

## 👤 Contact

**Developer**: Warp AI Agent  
**Project Owner**: Jay Sanchez (jsanchez@nmblr.ai)  
**Date**: November 10, 2025  

---

## ✅ Sign-Off

- [x] Database schema documented
- [x] Required tables listed
- [x] API endpoints documented
- [x] Test users documented
- [x] Setup instructions provided
- [x] Testing guide included
- [x] Known limitations noted
- [x] Deployment checklist created
- [x] Code committed to git

**Status**: ✅ Ready for handoff

---

*End of Handoff Document*
