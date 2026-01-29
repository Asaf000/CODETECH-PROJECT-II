"""
Real-Time Chat Application with Socket.IO
Flask + Socket.IO Backend
"""
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
from dotenv import load_dotenv
from datetime import datetime
import hashlib
from config.database import (
    DatabaseConfig, create_user, get_user_by_username, 
    update_user_status, get_all_rooms, create_room,
    save_message, get_room_messages, join_room as db_join_room,
    get_online_users
)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')

# Initialize Socket.IO with CORS support
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize database on startup
db_config = DatabaseConfig()
db_config.initialize_database()

# Store active users (socket_id -> user_info)
active_users = {}

# Simple password hashing (use bcrypt in production)
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/')
def index():
    """Main chat interface - requires login"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('chat.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username and password:
            user = get_user_by_username(username)
            
            if user and user['password_hash'] == hash_password(password):
                # Set session
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['display_name'] = user['display_name']
                session['avatar_color'] = user['avatar_color']
                
                # Update online status
                update_user_status(user['id'], True)
                
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        display_name = request.form.get('display_name')
        
        if username and email and password:
            # Check if user already exists
            existing_user = get_user_by_username(username)
            if existing_user:
                return render_template('register.html', error='Username already exists')
            
            # Create new user
            password_hash = hash_password(password)
            user_id = create_user(username, email, password_hash, display_name)
            
            if user_id:
                return redirect(url_for('login', success='Account created! Please login.'))
            else:
                return render_template('register.html', error='Registration failed')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Logout user"""
    if 'user_id' in session:
        update_user_status(session['user_id'], False)
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/rooms')
def api_rooms():
    """Get all available rooms"""
    rooms = get_all_rooms()
    return jsonify({'success': True, 'rooms': rooms})

@app.route('/api/messages/<int:room_id>')
def api_messages(room_id):
    """Get messages for a specific room"""
    messages = get_room_messages(room_id, limit=100)
    return jsonify({'success': True, 'messages': messages})

@app.route('/api/online-users/<int:room_id>')
def api_online_users(room_id):
    """Get online users in a room"""
    users = get_online_users(room_id)
    return jsonify({'success': True, 'users': users})

# Socket.IO Event Handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    if 'user_id' in session:
        user_info = {
            'user_id': session['user_id'],
            'username': session['username'],
            'display_name': session['display_name'],
            'avatar_color': session['avatar_color']
        }
        active_users[request.sid] = user_info
        
        # Update user status
        update_user_status(session['user_id'], True)
        
        print(f"✅ User connected: {session['username']} (SID: {request.sid})")
        
        emit('connection_success', {
            'user_id': session['user_id'],
            'username': session['username'],
            'display_name': session['display_name']
        })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    if request.sid in active_users:
        user_info = active_users[request.sid]
        
        # Update user status
        update_user_status(user_info['user_id'], False)
        
        # Notify all rooms
        emit('user_left', {
            'username': user_info['username'],
            'display_name': user_info['display_name']
        }, broadcast=True)
        
        del active_users[request.sid]
        print(f"❌ User disconnected: {user_info['username']}")

@socketio.on('join_room')
def handle_join_room(data):
    """Handle user joining a room"""
    room_id = data.get('room_id')
    room_name = data.get('room_name')
    
    if 'user_id' not in session:
        return
    
    # Join Socket.IO room
    join_room(str(room_id))
    
    # Add to database
    db_join_room(room_id, session['user_id'])
    
    # Send join notification to room
    emit('user_joined', {
        'username': session['username'],
        'display_name': session['display_name'],
        'avatar_color': session['avatar_color'],
        'message': f"{session['display_name']} joined the room",
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }, room=str(room_id))
    
    # Save system message
    save_message(
        room_id, 
        session['user_id'], 
        session['username'],
        f"{session['display_name']} joined the room",
        'system'
    )
    
    print(f"👥 {session['username']} joined room: {room_name}")

@socketio.on('leave_room')
def handle_leave_room(data):
    """Handle user leaving a room"""
    room_id = data.get('room_id')
    
    if 'user_id' not in session:
        return
    
    # Leave Socket.IO room
    leave_room(str(room_id))
    
    # Send leave notification to room
    emit('user_left_room', {
        'username': session['username'],
        'display_name': session['display_name'],
        'message': f"{session['display_name']} left the room",
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }, room=str(room_id))
    
    # Save system message
    save_message(
        room_id,
        session['user_id'],
        session['username'],
        f"{session['display_name']} left the room",
        'system'
    )

@socketio.on('send_message')
def handle_send_message(data):
    """Handle incoming chat message"""
    room_id = data.get('room_id')
    message = data.get('message', '').strip()
    
    if not message or 'user_id' not in session:
        return
    
    # Save message to database
    message_id = save_message(
        room_id,
        session['user_id'],
        session['username'],
        message,
        'text'
    )
    
    if message_id:
        # Broadcast message to room
        emit('new_message', {
            'id': message_id,
            'username': session['username'],
            'display_name': session['display_name'],
            'avatar_color': session['avatar_color'],
            'message': message,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'message_type': 'text'
        }, room=str(room_id))
        
        print(f"💬 Message from {session['username']}: {message[:50]}...")

@socketio.on('typing')
def handle_typing(data):
    """Handle typing indicator"""
    room_id = data.get('room_id')
    is_typing = data.get('is_typing', False)
    
    if 'user_id' not in session:
        return
    
    emit('user_typing', {
        'username': session['username'],
        'display_name': session['display_name'],
        'is_typing': is_typing
    }, room=str(room_id), include_self=False)

@socketio.on('create_room')
def handle_create_room(data):
    """Handle room creation"""
    room_name = data.get('room_name', '').strip()
    
    if not room_name or 'user_id' not in session:
        emit('room_creation_error', {'error': 'Invalid room name'})
        return
    
    room_id = create_room(room_name, 'public', session['user_id'])
    
    if room_id:
        emit('room_created', {
            'room_id': room_id,
            'room_name': room_name,
            'message': f"Room '{room_name}' created successfully!"
        }, broadcast=True)
    else:
        emit('room_creation_error', {'error': 'Failed to create room'})

if __name__ == '__main__':
    socketio.run(
        app,
        host=os.getenv('SERVER_HOST', '0.0.0.0'),
        port=int(os.getenv('SERVER_PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', True)
    )