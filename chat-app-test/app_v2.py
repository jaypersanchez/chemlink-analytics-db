from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS
import psycopg2
import psycopg2.extras
from datetime import datetime
import uuid
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_db():
    return psycopg2.connect(
        host='localhost',
        port=5433,
        database='engagement-platform-dev',
        user='dev',
        password='dev',
        cursor_factory=psycopg2.extras.RealDictCursor
    )

@app.route('/')
def index():
    return render_template('inbox.html')

@app.route('/test')
def test():
    """Split-screen testing interface"""
    return render_template('test.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ====================
# User Search
# ====================
@app.route('/api/users/search')
def search_users():
    """Search users by name or email"""
    query = request.args.get('q', '').strip()
    current_user_id = request.args.get('user_id')
    
    if not query or len(query) < 2:
        return jsonify([])
    
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    id,
                    first_name,
                    last_name,
                    first_name || ' ' || last_name AS full_name,
                    email
                FROM persons
                WHERE (
                    LOWER(first_name || ' ' || last_name) LIKE LOWER(%s) OR
                    LOWER(email) LIKE LOWER(%s)
                ) AND id != %s
                LIMIT 20
            """, (f'%{query}%', f'%{query}%', current_user_id))
            
            users = cur.fetchall()
            return jsonify(users)
    finally:
        conn.close()

# ====================
# Conversations List
# ====================
@app.route('/api/conversations')
def get_conversations():
    """Get all conversations for a user, grouped by folder"""
    user_id = request.args.get('user_id')
    folder = request.args.get('folder', 'MAIN')  # MAIN, REQUEST, RESTRICTED
    
    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400
    
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    c.id AS conversation_id,
                    c.conversation_type,
                    c.updated_at,
                    cp.folder,
                    cp.last_read_at,
                    cp.notification_level,
                    -- Get other participant info
                    (SELECT 
                        jsonb_build_object(
                            'id', p.id,
                            'name', p.first_name || ' ' || p.last_name,
                            'email', p.email
                        )
                     FROM conversation_participants cp2
                     JOIN persons p ON cp2.person_id = p.id
                     WHERE cp2.conversation_id = c.id 
                       AND cp2.person_id != %s
                     LIMIT 1
                    ) AS other_participant,
                    -- Get last message
                    (SELECT 
                        jsonb_build_object(
                            'id', m.id,
                            'body', m.body,
                            'sender_id', m.sender_id,
                            'created_at', m.created_at,
                            'message_type', m.message_type
                        )
                     FROM messages m
                     WHERE m.conversation_id = c.id
                     ORDER BY m.created_at DESC
                     LIMIT 1
                    ) AS last_message,
                    -- Count unread messages
                    (SELECT COUNT(*)
                     FROM messages m
                     WHERE m.conversation_id = c.id
                       AND m.sender_id != %s
                       AND NOT EXISTS (
                           SELECT 1 FROM message_reads mr
                           WHERE mr.message_id = m.id AND mr.person_id = %s
                       )
                    ) AS unread_count
                FROM conversations c
                JOIN conversation_participants cp ON c.id = cp.conversation_id
                WHERE cp.person_id = %s
                  AND cp.folder = %s
                  AND cp.left_at IS NULL
                ORDER BY c.updated_at DESC
            """, (user_id, user_id, user_id, user_id, folder))
            
            conversations = cur.fetchall()
            
            # Format timestamps
            for conv in conversations:
                if conv['updated_at']:
                    conv['updated_at'] = conv['updated_at'].isoformat()
                if conv['last_read_at']:
                    conv['last_read_at'] = conv['last_read_at'].isoformat()
            
            return jsonify(conversations)
    finally:
        conn.close()

# ====================
# Messages
# ====================
@app.route('/api/conversations/<conversation_id>/messages')
def get_conversation_messages(conversation_id):
    """Get all messages in a conversation"""
    user_id = request.args.get('user_id')
    
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    m.id,
                    m.sender_id,
                    m.body,
                    m.message_type,
                    m.status,
                    m.created_at,
                    m.updated_at,
                    p.first_name || ' ' || p.last_name AS sender_name,
                    -- Get read status
                    EXISTS(SELECT 1 FROM message_reads WHERE message_id = m.id AND person_id = %s) AS is_read,
                    -- Get reactions
                    COALESCE(
                        (SELECT JSON_AGG(JSON_BUILD_OBJECT('person_id', person_id, 'reaction', reaction_type))
                         FROM message_reactions WHERE message_id = m.id),
                        '[]'::json
                    ) AS reactions,
                    -- Get attachment
                    (SELECT ROW_TO_JSON(att.*) FROM (
                        SELECT storage_key, mime_type, file_size_bytes, 
                               metadata->>'file_name' AS file_name
                        FROM message_attachments
                        WHERE message_id = m.id
                        LIMIT 1
                    ) att) AS attachment
                FROM messages m
                JOIN persons p ON m.sender_id = p.id
                WHERE m.conversation_id = %s
                ORDER BY m.created_at ASC
            """, (user_id, conversation_id))
            
            messages = cur.fetchall()
            
            # Format timestamps
            for msg in messages:
                if msg['created_at']:
                    msg['created_at'] = msg['created_at'].isoformat()
                if msg['updated_at']:
                    msg['updated_at'] = msg['updated_at'].isoformat()
            
            return jsonify(messages)
    finally:
        conn.close()

@app.route('/api/conversations/<conversation_id>/messages', methods=['POST'])
def send_message_to_conversation(conversation_id):
    """Send a message to a conversation"""
    # Check if request has file
    if 'file' in request.files:
        file = request.files['file']
        sender_id = request.form.get('sender_id')
        body = request.form.get('body', '')
        
        if not sender_id:
            return jsonify({'error': 'Missing sender_id'}), 400
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1]
        storage_key = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], storage_key)
        
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        mime_type = file.content_type or 'application/octet-stream'
        
        conn = get_db()
        try:
            with conn.cursor() as cur:
                message_id = str(uuid.uuid4())
                message_type = 'IMAGE' if mime_type.startswith('image/') else \
                               'VIDEO' if mime_type.startswith('video/') else \
                               'AUDIO' if mime_type.startswith('audio/') else 'FILE'
                
                cur.execute("""
                    INSERT INTO messages (id, conversation_id, sender_id, message_type, body, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, 'DELIVERED', NOW(), NOW())
                    RETURNING id, created_at
                """, (message_id, conversation_id, sender_id, message_type, body))
                
                result = cur.fetchone()
                
                # Insert attachment
                attachment_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO message_attachments 
                    (id, message_id, storage_key, mime_type, file_size_bytes, metadata, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (attachment_id, message_id, storage_key, mime_type, file_size,
                      f'{{"file_name": "{secure_filename(file.filename)}"}}'))
                
                # Auto-mark as read by sender
                cur.execute("""
                    INSERT INTO message_reads (message_id, person_id, read_at, created_at)
                    VALUES (%s, %s, NOW(), NOW())
                """, (message_id, sender_id))
                
                # Update conversation timestamp
                cur.execute("UPDATE conversations SET updated_at = NOW() WHERE id = %s", (conversation_id,))
                
                conn.commit()
                
                return jsonify({
                    'id': result['id'],
                    'created_at': result['created_at'].isoformat()
                })
        finally:
            conn.close()
    else:
        # Text-only message
        data = request.json
        sender_id = data.get('sender_id')
        body = data.get('body')
        
        if not sender_id or not body:
            return jsonify({'error': 'Missing sender_id or body'}), 400
        
        conn = get_db()
        try:
            with conn.cursor() as cur:
                message_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO messages (id, conversation_id, sender_id, message_type, body, status, created_at, updated_at)
                    VALUES (%s, %s, %s, 'TEXT', %s, 'DELIVERED', NOW(), NOW())
                    RETURNING id, created_at
                """, (message_id, conversation_id, sender_id, body))
                
                result = cur.fetchone()
                
                # Auto-mark as read by sender
                cur.execute("""
                    INSERT INTO message_reads (message_id, person_id, read_at, created_at)
                    VALUES (%s, %s, NOW(), NOW())
                """, (message_id, sender_id))
                
                # Update conversation timestamp
                cur.execute("UPDATE conversations SET updated_at = NOW() WHERE id = %s", (conversation_id,))
                
                conn.commit()
                
                return jsonify({
                    'id': result['id'],
                    'created_at': result['created_at'].isoformat()
                })
        finally:
            conn.close()

# ====================
# Start New Conversation
# ====================
@app.route('/api/conversations/start', methods=['POST'])
def start_conversation():
    """Start a new conversation with a user"""
    data = request.json
    user1_id = data.get('user1_id')
    user2_id = data.get('user2_id')
    
    if not user1_id or not user2_id:
        return jsonify({'error': 'Missing user IDs'}), 400
    
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Check if conversation already exists
            cur.execute("""
                SELECT c.id
                FROM conversations c
                JOIN conversation_participants cp1 ON c.id = cp1.conversation_id
                JOIN conversation_participants cp2 ON c.id = cp2.conversation_id
                WHERE c.conversation_type = 'DIRECT'
                  AND cp1.person_id = %s
                  AND cp2.person_id = %s
                LIMIT 1
            """, (user1_id, user2_id))
            
            existing = cur.fetchone()
            if existing:
                return jsonify({'conversation_id': existing['id'], 'existing': True})
            
            # Create new conversation
            conversation_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO conversations (id, conversation_type, created_by, created_at, updated_at)
                VALUES (%s, 'DIRECT', %s, NOW(), NOW())
            """, (conversation_id, user1_id))
            
            # Add participants (new conversations start in REQUEST folder for recipient)
            cur.execute("""
                INSERT INTO conversation_participants 
                (conversation_id, person_id, folder, created_at, updated_at)
                VALUES 
                (%s, %s, 'MAIN', NOW(), NOW()),
                (%s, %s, 'REQUEST', NOW(), NOW())
            """, (conversation_id, user1_id, conversation_id, user2_id))
            
            conn.commit()
            
            return jsonify({'conversation_id': conversation_id, 'existing': False})
    finally:
        conn.close()

# ====================
# Folder Management
# ====================
@app.route('/api/conversations/<conversation_id>/folder', methods=['PUT'])
def update_conversation_folder(conversation_id):
    """Move conversation to different folder (MAIN, REQUEST, RESTRICTED)"""
    data = request.json
    user_id = data.get('user_id')
    folder = data.get('folder')  # MAIN, REQUEST, RESTRICTED
    
    if not user_id or not folder:
        return jsonify({'error': 'Missing user_id or folder'}), 400
    
    if folder not in ['MAIN', 'REQUEST', 'RESTRICTED']:
        return jsonify({'error': 'Invalid folder'}), 400
    
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Update folder
            cur.execute("""
                UPDATE conversation_participants
                SET folder = %s, updated_at = NOW()
                WHERE conversation_id = %s AND person_id = %s
            """, (folder, conversation_id, user_id))
            
            # If moving to RESTRICTED, set notification_level to MUTED
            if folder == 'RESTRICTED':
                cur.execute("""
                    UPDATE conversation_participants
                    SET notification_level = 'MUTED'
                    WHERE conversation_id = %s AND person_id = %s
                """, (conversation_id, user_id))
            elif folder == 'MAIN':
                # Enable notifications when moving to MAIN
                cur.execute("""
                    UPDATE conversation_participants
                    SET notification_level = 'ALL'
                    WHERE conversation_id = %s AND person_id = %s
                """, (conversation_id, user_id))
            
            conn.commit()
            
            return jsonify({'status': 'success', 'folder': folder})
    finally:
        conn.close()

# ====================
# Read Receipts
# ====================
@app.route('/api/messages/mark-read', methods=['POST'])
def mark_messages_read():
    """Mark multiple messages as read"""
    data = request.json
    user_id = data.get('user_id')
    message_ids = data.get('message_ids', [])
    conversation_id = data.get('conversation_id')
    
    if not user_id or not message_ids:
        return jsonify({'error': 'Missing user_id or message_ids'}), 400
    
    conn = get_db()
    try:
        with conn.cursor() as cur:
            for message_id in message_ids:
                cur.execute("""
                    INSERT INTO message_reads (message_id, person_id, read_at, created_at)
                    VALUES (%s, %s, NOW(), NOW())
                    ON CONFLICT DO NOTHING
                """, (message_id, user_id))
            
            # Update last_read_at
            if conversation_id:
                cur.execute("""
                    UPDATE conversation_participants
                    SET last_read_at = NOW(), updated_at = NOW()
                    WHERE conversation_id = %s AND person_id = %s
                """, (conversation_id, user_id))
            
            conn.commit()
            
            return jsonify({'status': 'success'})
    finally:
        conn.close()

# ====================
# Reactions
# ====================
@app.route('/api/messages/<message_id>/react', methods=['POST'])
def add_message_reaction(message_id):
    """Add reaction to a message"""
    data = request.json
    user_id = data.get('user_id')
    reaction = data.get('reaction')
    
    if not user_id or not reaction:
        return jsonify({'error': 'Missing user_id or reaction'}), 400
    
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO message_reactions (message_id, person_id, reaction_type, created_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (message_id, person_id) 
                DO UPDATE SET reaction_type = %s
            """, (message_id, user_id, reaction, reaction))
            
            conn.commit()
            
            return jsonify({'status': 'success'})
    finally:
        conn.close()

@app.route('/api/messages/<message_id>/react', methods=['DELETE'])
def remove_message_reaction(message_id):
    """Remove reaction from a message"""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400
    
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM message_reactions
                WHERE message_id = %s AND person_id = %s
            """, (message_id, user_id))
            
            conn.commit()
            
            return jsonify({'status': 'success'})
    finally:
        conn.close()

# ====================
# Unread Count
# ====================
@app.route('/api/conversations/unread-count')
def get_unread_count():
    """Get total unread message count for user"""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400
    
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(DISTINCT m.id) AS unread_count
                FROM messages m
                JOIN conversation_participants cp ON m.conversation_id = cp.conversation_id
                WHERE cp.person_id = %s
                  AND m.sender_id != %s
                  AND cp.folder != 'RESTRICTED'
                  AND NOT EXISTS (
                      SELECT 1 FROM message_reads mr
                      WHERE mr.message_id = m.id AND mr.person_id = %s
                  )
            """, (user_id, user_id, user_id))
            
            result = cur.fetchone()
            return jsonify({'unread_count': result['unread_count'] or 0})
    finally:
        conn.close()

if __name__ == '__main__':
    print("🚀 ChemLink Messaging Server v2")
    print("=" * 60)
    print(f"📍 URL: http://localhost:5005")
    print(f"📬 Inbox: http://localhost:5005")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5005)
