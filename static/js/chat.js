// Real-Time Chat Application - Frontend JavaScript
// Socket.IO Integration

// Initialize Socket.IO connection
const socket = io();

// DOM Elements
const roomsList = document.getElementById('roomsList');
const messagesContainer = document.getElementById('messagesContainer');
const messageForm = document.getElementById('messageForm');
const messageInput = document.getElementById('messageInput');
const messageInputContainer = document.getElementById('messageInputContainer');
const currentRoomName = document.getElementById('currentRoomName');
const roomMemberCount = document.getElementById('roomMemberCount');
const typingIndicator = document.getElementById('typingIndicator');
const typingText = document.getElementById('typingText');
const onlineUsersList = document.getElementById('onlineUsersList');

// Modal Elements
const createRoomBtn = document.getElementById('createRoomBtn');
const createRoomModal = document.getElementById('createRoomModal');
const closeModalBtn = document.getElementById('closeModalBtn');
const cancelCreateRoom = document.getElementById('cancelCreateRoom');
const createRoomForm = document.getElementById('createRoomForm');
const newRoomName = document.getElementById('newRoomName');

// State
let currentRoom = null;
let typingTimeout = null;
let isTyping = false;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    loadRooms();
    setupEventListeners();
});

// Setup Event Listeners
function setupEventListeners() {
    // Message form
    messageForm.addEventListener('submit', handleSendMessage);
    
    // Typing indicator
    messageInput.addEventListener('input', handleTyping);
    
    // Modal controls
    createRoomBtn.addEventListener('click', () => openModal());
    closeModalBtn.addEventListener('click', () => closeModal());
    cancelCreateRoom.addEventListener('click', () => closeModal());
    createRoomForm.addEventListener('submit', handleCreateRoom);
    
    // Click outside modal to close
    createRoomModal.addEventListener('click', (e) => {
        if (e.target === createRoomModal) closeModal();
    });
    
    // Mobile sidebar toggle
    const toggleSidebar = document.getElementById('toggleSidebar');
    if (toggleSidebar) {
        toggleSidebar.addEventListener('click', () => {
            document.querySelector('.sidebar').classList.toggle('show');
        });
    }
}

// Load available rooms
async function loadRooms() {
    try {
        const response = await fetch('/api/rooms');
        const data = await response.json();
        
        if (data.success) {
            displayRooms(data.rooms);
        }
    } catch (error) {
        console.error('Error loading rooms:', error);
        roomsList.innerHTML = '<p style="padding: 1rem; color: #FF6B6B;">Failed to load rooms</p>';
    }
}

// Display rooms in sidebar
function displayRooms(rooms) {
    roomsList.innerHTML = '';
    
    rooms.forEach(room => {
        const roomElement = document.createElement('div');
        roomElement.className = 'room-item';
        roomElement.dataset.roomId = room.id;
        
        roomElement.innerHTML = `
            <div class="room-name">
                <i class="fas fa-hashtag"></i>
                ${escapeHtml(room.room_name)}
            </div>
            <div class="room-meta">
                <span title="Messages"><i class="fas fa-comment"></i> ${room.message_count || 0}</span>
                <span title="Members"><i class="fas fa-user"></i> ${room.member_count || 0}</span>
            </div>
        `;
        
        roomElement.addEventListener('click', () => joinRoom(room.id, room.room_name));
        roomsList.appendChild(roomElement);
    });
}

// Join a chat room
function joinRoom(roomId, roomName) {
    // Leave current room if any
    if (currentRoom) {
        socket.emit('leave_room', { room_id: currentRoom.id });
    }
    
    // Update current room
    currentRoom = { id: roomId, name: roomName };
    
    // Update UI
    currentRoomName.textContent = roomName;
    messageInputContainer.style.display = 'block';
    
    // Update active room in sidebar
    document.querySelectorAll('.room-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-room-id="${roomId}"]`).classList.add('active');
    
    // Join Socket.IO room
    socket.emit('join_room', { room_id: roomId, room_name: roomName });
    
    // Load room messages
    loadRoomMessages(roomId);
    
    // Load online users for this room
    loadOnlineUsers(roomId);
    
    // Hide mobile sidebar
    document.querySelector('.sidebar').classList.remove('show');
}

// Load messages for a room
async function loadRoomMessages(roomId) {
    try {
        const response = await fetch(`/api/messages/${roomId}`);
        const data = await response.json();
        
        if (data.success) {
            messagesContainer.innerHTML = '';
            data.messages.forEach(message => displayMessage(message));
            scrollToBottom();
        }
    } catch (error) {
        console.error('Error loading messages:', error);
    }
}

// Display a message
function displayMessage(message) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${message.message_type === 'system' ? 'system' : ''}`;
    
    if (message.message_type === 'system') {
        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-text">${escapeHtml(message.message)}</div>
            </div>
        `;
    } else {
        const avatarColor = message.avatar_color || '#4A90E2';
        const displayName = message.display_name || message.username;
        const initial = displayName.charAt(0).toUpperCase();
        
        messageDiv.innerHTML = `
            <div class="message-avatar" style="background: ${avatarColor}">
                ${initial}
            </div>
            <div class="message-content">
                <div class="message-header">
                    <span class="message-author">${escapeHtml(displayName)}</span>
                    <span class="message-time">${formatTime(message.timestamp)}</span>
                </div>
                <div class="message-text">${escapeHtml(message.message)}</div>
            </div>
        `;
    }
    
    messagesContainer.appendChild(messageDiv);
}

// Handle sending message
function handleSendMessage(e) {
    e.preventDefault();
    
    const message = messageInput.value.trim();
    
    if (message && currentRoom) {
        socket.emit('send_message', {
            room_id: currentRoom.id,
            message: message
        });
        
        messageInput.value = '';
        
        // Stop typing indicator
        if (isTyping) {
            socket.emit('typing', { room_id: currentRoom.id, is_typing: false });
            isTyping = false;
        }
    }
}

// Handle typing indicator
function handleTyping() {
    if (!currentRoom) return;
    
    if (!isTyping) {
        isTyping = true;
        socket.emit('typing', { room_id: currentRoom.id, is_typing: true });
    }
    
    clearTimeout(typingTimeout);
    typingTimeout = setTimeout(() => {
        isTyping = false;
        socket.emit('typing', { room_id: currentRoom.id, is_typing: false });
    }, 1000);
}

// Handle room creation
function handleCreateRoom(e) {
    e.preventDefault();
    
    const roomName = newRoomName.value.trim();
    
    if (roomName) {
        socket.emit('create_room', { room_name: roomName });
        newRoomName.value = '';
        closeModal();
    }
}

// Load online users
async function loadOnlineUsers(roomId) {
    try {
        const response = await fetch(`/api/online-users/${roomId}`);
        const data = await response.json();
        
        if (data.success) {
            displayOnlineUsers(data.users);
        }
    } catch (error) {
        console.error('Error loading online users:', error);
    }
}

// Display online users
function displayOnlineUsers(users) {
    if (users.length === 0) {
        onlineUsersList.innerHTML = '<div style="padding: 0.5rem; color: #b8b8b8; font-size: 0.85rem;">No users online</div>';
        return;
    }
    
    onlineUsersList.innerHTML = '';
    
    users.forEach(user => {
        const userElement = document.createElement('div');
        userElement.className = 'online-user-item';
        userElement.innerHTML = `
            <div class="online-user-dot"></div>
            <span>${escapeHtml(user.display_name || user.username)}</span>
        `;
        onlineUsersList.appendChild(userElement);
    });
}

// Socket.IO Event Handlers
socket.on('connect', () => {
    console.log('✅ Connected to server');
});

socket.on('connection_success', (data) => {
    console.log('✅ Authentication successful:', data);
});

socket.on('new_message', (message) => {
    if (currentRoom && message) {
        displayMessage(message);
        scrollToBottom();
    }
});

socket.on('user_joined', (data) => {
    if (currentRoom) {
        displayMessage({
            message: data.message,
            message_type: 'system',
            timestamp: data.timestamp
        });
        scrollToBottom();
        
        // Refresh online users
        if (currentRoom) {
            loadOnlineUsers(currentRoom.id);
        }
    }
});

socket.on('user_left_room', (data) => {
    if (currentRoom) {
        displayMessage({
            message: data.message,
            message_type: 'system',
            timestamp: data.timestamp
        });
        scrollToBottom();
        
        // Refresh online users
        if (currentRoom) {
            loadOnlineUsers(currentRoom.id);
        }
    }
});

socket.on('user_typing', (data) => {
    if (currentRoom) {
        typingText.textContent = `${data.display_name} is typing...`;
        typingIndicator.style.display = 'flex';
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
            typingIndicator.style.display = 'none';
        }, 3000);
    }
});

socket.on('room_created', (data) => {
    console.log('✅ Room created:', data.room_name);
    
    // Show success notification
    showNotification(`Room "${data.room_name}" created successfully!`, 'success');
    
    // Reload rooms list
    loadRooms();
});

socket.on('room_creation_error', (data) => {
    showNotification(data.error || 'Failed to create room', 'error');
});

socket.on('disconnect', () => {
    console.log('❌ Disconnected from server');
    showNotification('Disconnected from server', 'error');
});

// Utility Functions
function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    
    if (isToday) {
        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    } else {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + 
               ' ' + date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    }
}

function openModal() {
    createRoomModal.classList.add('show');
}

function closeModal() {
    createRoomModal.classList.remove('show');
    newRoomName.value = '';
}

function showNotification(message, type = 'info') {
    // Simple notification (you can enhance this with a proper notification system)
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: ${type === 'success' ? '#50C878' : '#FF6B6B'};
        color: white;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Auto-refresh online users every 30 seconds
setInterval(() => {
    if (currentRoom) {
        loadOnlineUsers(currentRoom.id);
    }
}, 30000);