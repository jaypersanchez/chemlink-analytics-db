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

# Create uploads directory if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# User IDs
JAYPER_ID = '78033fa0-db62-43f9-8e00-02488aeb0ed5'
DAVID_ID = '24c5aed9-b257-4d33-99d1-2b7e297a2634'
CONVERSATION_ID = 'c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c'

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

@app.route('/')
def index():
    """Render chat interface"""
    return render_template('chat.html')

@app.route('/group-test')
def group_test():
    """Render 3-panel group chat test interface"""
    return render_template('group-chat.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/messages')
def get_messages():
    """Get all messages in the conversation with read status and reactions"""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    m.id,
                    m.sender_id,
                    p.first_name || ' ' || p.last_name AS sender_name,
                    m.body,
                    m.status,
                    m.created_at,
                    -- Check if Jayper read it
                    EXISTS(SELECT 1 FROM message_reads WHERE message_id = m.id AND person_id = %s) AS jayper_read,
                    -- Check if David read it
                    EXISTS(SELECT 1 FROM message_reads WHERE message_id = m.id AND person_id = %s) AS david_read,
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
                ORDER BY m.created_at
            """, (JAYPER_ID, DAVID_ID, CONVERSATION_ID))
            
            messages = cur.fetchall()
            
            # Convert datetime to ISO format
            for msg in messages:
                if msg['created_at']:
                    msg['created_at'] = msg['created_at'].isoformat()
            
            return jsonify(messages)
    finally:
        conn.close()

@app.route('/api/send', methods=['POST'])
def send_message():
    """Send a new message with optional file attachment"""
    # Check if request has file
    if 'file' in request.files:
        # Handle file upload
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
        
        # Save file
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
                
                # Insert message
                cur.execute("""
                    INSERT INTO messages (id, conversation_id, sender_id, message_type, body, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, 'DELIVERED', NOW(), NOW())
                    RETURNING id, created_at
                """, (message_id, CONVERSATION_ID, sender_id, message_type, body))
                
                result = cur.fetchone()
                
                # Insert attachment
                attachment_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO message_attachments 
                    (id, message_id, storage_key, mime_type, file_size_bytes, metadata, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (attachment_id, message_id, storage_key, mime_type, file_size, 
                      f'{{"file_name": "{secure_filename(file.filename)}"}}'  ))
                
                # Auto-mark as read by sender
                cur.execute("""
                    INSERT INTO message_reads (message_id, person_id, read_at, created_at)
                    VALUES (%s, %s, NOW(), NOW())
                """, (message_id, sender_id))
                
                # Update conversation updated_at
                cur.execute("""
                    UPDATE conversations SET updated_at = NOW() WHERE id = %s
                """, (CONVERSATION_ID,))
                
                conn.commit()
                
                return jsonify({
                    'id': result['id'],
                    'created_at': result['created_at'].isoformat()
                })
        finally:
            conn.close()
    else:
        # Handle text-only message
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
                """, (message_id, CONVERSATION_ID, sender_id, body))
                
                result = cur.fetchone()
                
                # Auto-mark as read by sender
                cur.execute("""
                    INSERT INTO message_reads (message_id, person_id, read_at, created_at)
                    VALUES (%s, %s, NOW(), NOW())
                """, (message_id, sender_id))
                
                # Update conversation updated_at
                cur.execute("""
                    UPDATE conversations SET updated_at = NOW() WHERE id = %s
                """, (CONVERSATION_ID,))
                
                conn.commit()
                
                return jsonify({
                    'id': result['id'],
                    'created_at': result['created_at'].isoformat()
                })
        finally:
            conn.close()

@app.route('/api/mark-read', methods=['POST'])
def mark_read():
    """Mark messages as read"""
    data = request.json
    person_id = data.get('person_id')
    message_ids = data.get('message_ids', [])
    
    if not person_id or not message_ids:
        return jsonify({'error': 'Missing person_id or message_ids'}), 400
    
    conn = get_db()
    try:
        with conn.cursor() as cur:
            for message_id in message_ids:
                # Check if already read
                cur.execute("""
                    SELECT 1 FROM message_reads WHERE message_id = %s AND person_id = %s
                """, (message_id, person_id))
                
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO message_reads (message_id, person_id, read_at, created_at)
                        VALUES (%s, %s, NOW(), NOW())
                        ON CONFLICT DO NOTHING
                    """, (message_id, person_id))
            
            # Update participant last_read_at
            cur.execute("""
                UPDATE conversation_participants 
                SET last_read_at = NOW(), updated_at = NOW()
                WHERE conversation_id = %s AND person_id = %s
            """, (CONVERSATION_ID, person_id))
            
            conn.commit()
            
            return jsonify({'status': 'success', 'marked_count': len(message_ids)})
    finally:
        conn.close()

@app.route('/api/react', methods=['POST'])
def add_reaction():
    """Add emoji reaction to a message"""
    data = request.json
    message_id = data.get('message_id')
    person_id = data.get('person_id')
    reaction = data.get('reaction_type')
    
    if not all([message_id, person_id, reaction]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Check if reaction already exists
            cur.execute("""
                SELECT 1 FROM message_reactions 
                WHERE message_id = %s AND person_id = %s
            """, (message_id, person_id))
            
            if cur.fetchone():
                # Update existing reaction
                cur.execute("""
                    UPDATE message_reactions 
                    SET reaction_type = %s
                    WHERE message_id = %s AND person_id = %s
                """, (reaction, message_id, person_id))
            else:
                # Insert new reaction
                cur.execute("""
                    INSERT INTO message_reactions (message_id, person_id, reaction_type, created_at)
                    VALUES (%s, %s, %s, NOW())
                """, (message_id, person_id, reaction))
            
            conn.commit()
            
            return jsonify({'status': 'success'})
    finally:
        conn.close()

@app.route('/api/remove-reaction', methods=['POST'])
def remove_reaction():
    """Remove emoji reaction from a message"""
    data = request.json
    message_id = data.get('message_id')
    person_id = data.get('person_id')
    
    if not message_id or not person_id:
        return jsonify({'error': 'Missing message_id or person_id'}), 400
    
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM message_reactions 
                WHERE message_id = %s AND person_id = %s
            """, (message_id, person_id))
            
            conn.commit()
            
            return jsonify({'status': 'success'})
    finally:
        conn.close()

# ==================== Group Chat API Endpoints ====================

@app.route('/api/conversations/start', methods=['POST'])
def start_conversation():
    """Create a new conversation (DIRECT or GROUP)"""
    data = request.json
    sender_id = data.get('sender_id')
    recipient_ids = data.get('recipient_ids', [])
    conversation_type = data.get('conversation_type', 'DIRECT')
    
    if not sender_id or not recipient_ids:
        return jsonify({'error': 'Missing sender_id or recipient_ids'}), 400
    
    conn = get_db()
    try:
        with conn.cursor() as cur:
            conversation_id = str(uuid.uuid4())
            
            # Create conversation
            cur.execute("""
                INSERT INTO conversations (id, conversation_type, created_by, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
            """, (conversation_id, conversation_type, sender_id))
            
            # Add sender as participant
            cur.execute("""
                INSERT INTO conversation_participants 
                (conversation_id, person_id, created_at, updated_at)
                VALUES (%s, %s, NOW(), NOW())
            """, (conversation_id, sender_id))
            
            # Add recipients as participants
            for recipient_id in recipient_ids:
                cur.execute("""
                    INSERT INTO conversation_participants 
                    (conversation_id, person_id, created_at, updated_at)
                    VALUES (%s, %s, NOW(), NOW())
                """, (conversation_id, recipient_id))
            
            conn.commit()
            
            return jsonify({
                'conversation_id': conversation_id,
                'conversation_type': conversation_type,
                'participants': [sender_id] + recipient_ids
            })
    finally:
        conn.close()

@app.route('/api/conversations/<conversation_id>/messages', methods=['GET', 'POST'])
def conversation_messages(conversation_id):
    """Get or send messages in a conversation"""
    if request.method == 'GET':
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        m.id,
                        m.sender_id,
                        m.body,
                        m.message_type,
                        m.created_at,
                        EXISTS(SELECT 1 FROM message_reads WHERE message_id = m.id AND person_id = %s) AS is_read
                    FROM messages m
                    WHERE m.conversation_id = %s
                    ORDER BY m.created_at
                """, (user_id, conversation_id))
                
                messages = cur.fetchall()
                
                for msg in messages:
                    if msg['created_at']:
                        msg['created_at'] = msg['created_at'].isoformat()
                
                return jsonify({'messages': messages})
        finally:
            conn.close()
    
    elif request.method == 'POST':
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
                
                # Update conversation updated_at
                cur.execute("""
                    UPDATE conversations SET updated_at = NOW() WHERE id = %s
                """, (conversation_id,))
                
                conn.commit()
                
                return jsonify({
                    'id': result['id'],
                    'created_at': result['created_at'].isoformat()
                })
        finally:
            conn.close()

@app.route('/api/conversations/<conversation_id>/participants', methods=['POST'])
def add_participant(conversation_id):
    """Add a participant to an existing conversation"""
    data = request.json
    person_id = data.get('person_id')
    added_by = data.get('added_by')
    
    if not person_id:
        return jsonify({'error': 'Missing person_id'}), 400
    
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Check if already a participant
            cur.execute("""
                SELECT 1 FROM conversation_participants 
                WHERE conversation_id = %s AND person_id = %s
            """, (conversation_id, person_id))
            
            if cur.fetchone():
                return jsonify({'error': 'Already a participant'}), 400
            
            # Add participant
            cur.execute("""
                INSERT INTO conversation_participants 
                (conversation_id, person_id, created_at, updated_at)
                VALUES (%s, %s, NOW(), NOW())
            """, (conversation_id, person_id))
            
            # Optionally add system message
            if added_by:
                cur.execute("""
                    SELECT first_name, last_name FROM persons WHERE id = %s
                """, (person_id,))
                person = cur.fetchone()
                if person:
                    system_message = f"{person['first_name']} {person['last_name']} joined the group"
                    cur.execute("""
                        INSERT INTO messages 
                        (id, conversation_id, sender_id, message_type, body, status, created_at, updated_at)
                        VALUES (%s, %s, %s, 'SYSTEM', %s, 'DELIVERED', NOW(), NOW())
                    """, (str(uuid.uuid4()), conversation_id, added_by, system_message))
            
            conn.commit()
            
            return jsonify({'status': 'success', 'person_id': person_id})
    finally:
        conn.close()

@app.route('/api/conversations/<conversation_id>/participants/<person_id>', methods=['DELETE'])
def remove_participant(conversation_id, person_id):
    """Remove a participant from a conversation"""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Get person name for system message
            cur.execute("""
                SELECT first_name, last_name FROM persons WHERE id = %s
            """, (person_id,))
            person = cur.fetchone()
            
            # Remove participant
            cur.execute("""
                DELETE FROM conversation_participants 
                WHERE conversation_id = %s AND person_id = %s
            """, (conversation_id, person_id))
            
            # Add system message
            if person:
                system_message = f"{person['first_name']} {person['last_name']} left the group"
                cur.execute("""
                    INSERT INTO messages 
                    (id, conversation_id, sender_id, message_type, body, status, created_at, updated_at)
                    VALUES (%s, %s, %s, 'SYSTEM', %s, 'DELIVERED', NOW(), NOW())
                """, (str(uuid.uuid4()), conversation_id, person_id, system_message))
            
            conn.commit()
            
            return jsonify({'status': 'success', 'person_id': person_id})
    finally:
        conn.close()

if __name__ == '__main__':
    print("🚀 Chat App Test Server")
    print("=" * 50)
    print(f"📍 2-Panel Direct Chat: http://localhost:5005")
    print(f"👥 3-Panel Group Chat: http://localhost:5005/group-test")
    print("=" * 50)
    print(f"👤 Jay Sanchez: {JAYPER_ID}")
    print(f"👤 David Uy (old ID): {DAVID_ID}")
    print(f"💬 Direct Conversation: {CONVERSATION_ID}")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5005)
