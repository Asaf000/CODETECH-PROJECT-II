"""
Database Configuration and Connection Handler for Chat Application
"""
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class DatabaseConfig:
    """Database configuration and connection management"""
    
    def __init__(self):
        self.host = os.getenv('DB_HOST')
        self.user = os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        self.database = os.getenv('DB_NAME')
    
    def get_connection(self):
        """Create and return database connection"""
        try:
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            if connection.is_connected():
                return connection
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return None
    
    def initialize_database(self):
        """Initialize database and create tables"""
        try:
            # Connect without database first
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password
            )
            cursor = connection.cursor()
            
            # Create database if not exists
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            cursor.execute(f"USE {self.database}")
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    display_name VARCHAR(100),
                    avatar_color VARCHAR(7) DEFAULT '#4A90E2',
                    is_online BOOLEAN DEFAULT FALSE,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create rooms table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rooms (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    room_name VARCHAR(100) UNIQUE NOT NULL,
                    room_type ENUM('public', 'private') DEFAULT 'public',
                    created_by INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            
            # Create messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    room_id INT NOT NULL,
                    user_id INT NOT NULL,
                    username VARCHAR(50) NOT NULL,
                    message TEXT NOT NULL,
                    message_type ENUM('text', 'system') DEFAULT 'text',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_room_timestamp (room_id, timestamp)
                )
            """)
            
            # Create room_members table (for tracking who's in which room)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS room_members (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    room_id INT NOT NULL,
                    user_id INT NOT NULL,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_room_user (room_id, user_id)
                )
            """)
            
            # Insert default rooms
            cursor.execute("""
                INSERT IGNORE INTO rooms (room_name, room_type) 
                VALUES 
                    ('General', 'public'),
                    ('Technology', 'public'),
                    ('Random', 'public')
            """)
            
            connection.commit()
            print("✅ Database and tables created successfully!")
            
            cursor.close()
            connection.close()
            return True
            
        except Error as e:
            print(f"❌ Error initializing database: {e}")
            return False

# User Management Functions
def create_user(username, email, password_hash, display_name=None):
    """Create a new user"""
    db_config = DatabaseConfig()
    connection = db_config.get_connection()
    
    if connection:
        try:
            cursor = connection.cursor()
            query = """
                INSERT INTO users (username, email, password_hash, display_name)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (username, email, password_hash, display_name or username))
            connection.commit()
            user_id = cursor.lastrowid
            cursor.close()
            connection.close()
            return user_id
        except Error as e:
            print(f"Error creating user: {e}")
            return None
    return None

def get_user_by_username(username):
    """Get user by username"""
    db_config = DatabaseConfig()
    connection = db_config.get_connection()
    
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT * FROM users WHERE username = %s"
            cursor.execute(query, (username,))
            user = cursor.fetchone()
            cursor.close()
            connection.close()
            return user
        except Error as e:
            print(f"Error fetching user: {e}")
            return None
    return None

def update_user_status(user_id, is_online):
    """Update user online status"""
    db_config = DatabaseConfig()
    connection = db_config.get_connection()
    
    if connection:
        try:
            cursor = connection.cursor()
            query = """
                UPDATE users 
                SET is_online = %s, last_seen = CURRENT_TIMESTAMP 
                WHERE id = %s
            """
            cursor.execute(query, (is_online, user_id))
            connection.commit()
            cursor.close()
            connection.close()
            return True
        except Error as e:
            print(f"Error updating user status: {e}")
            return False
    return False

# Room Management Functions
def get_all_rooms():
    """Get all available rooms"""
    db_config = DatabaseConfig()
    connection = db_config.get_connection()
    
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT r.*, COUNT(DISTINCT m.id) as message_count,
                       COUNT(DISTINCT rm.user_id) as member_count
                FROM rooms r
                LEFT JOIN messages m ON r.id = m.room_id
                LEFT JOIN room_members rm ON r.id = rm.room_id
                WHERE r.room_type = 'public'
                GROUP BY r.id
                ORDER BY r.created_at
            """
            cursor.execute(query)
            rooms = cursor.fetchall()
            cursor.close()
            connection.close()
            return rooms
        except Error as e:
            print(f"Error fetching rooms: {e}")
            return []
    return []

def create_room(room_name, room_type='public', created_by=None):
    """Create a new chat room"""
    db_config = DatabaseConfig()
    connection = db_config.get_connection()
    
    if connection:
        try:
            cursor = connection.cursor()
            query = """
                INSERT INTO rooms (room_name, room_type, created_by)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (room_name, room_type, created_by))
            connection.commit()
            room_id = cursor.lastrowid
            cursor.close()
            connection.close()
            return room_id
        except Error as e:
            print(f"Error creating room: {e}")
            return None
    return None

# Message Management Functions
def save_message(room_id, user_id, username, message, message_type='text'):
    """Save a message to database"""
    db_config = DatabaseConfig()
    connection = db_config.get_connection()
    
    if connection:
        try:
            cursor = connection.cursor()
            query = """
                INSERT INTO messages (room_id, user_id, username, message, message_type)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (room_id, user_id, username, message, message_type))
            connection.commit()
            message_id = cursor.lastrowid
            cursor.close()
            connection.close()
            return message_id
        except Error as e:
            print(f"Error saving message: {e}")
            return None
    return None

def get_room_messages(room_id, limit=50):
    """Get recent messages from a room"""
    db_config = DatabaseConfig()
    connection = db_config.get_connection()
    
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT m.*, u.avatar_color, u.display_name
                FROM messages m
                JOIN users u ON m.user_id = u.id
                WHERE m.room_id = %s
                ORDER BY m.timestamp DESC
                LIMIT %s
            """
            cursor.execute(query, (room_id, limit))
            messages = cursor.fetchall()
            cursor.close()
            connection.close()
            return list(reversed(messages))  # Return in chronological order
        except Error as e:
            print(f"Error fetching messages: {e}")
            return []
    return []

def join_room(room_id, user_id):
    """Add user to room members"""
    db_config = DatabaseConfig()
    connection = db_config.get_connection()
    
    if connection:
        try:
            cursor = connection.cursor()
            query = """
                INSERT IGNORE INTO room_members (room_id, user_id)
                VALUES (%s, %s)
            """
            cursor.execute(query, (room_id, user_id))
            connection.commit()
            cursor.close()
            connection.close()
            return True
        except Error as e:
            print(f"Error joining room: {e}")
            return False
    return False

def get_online_users(room_id=None):
    """Get list of online users, optionally filtered by room"""
    db_config = DatabaseConfig()
    connection = db_config.get_connection()
    
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            if room_id:
                query = """
                    SELECT DISTINCT u.id, u.username, u.display_name, 
                           u.avatar_color, u.is_online
                    FROM users u
                    JOIN room_members rm ON u.id = rm.user_id
                    WHERE u.is_online = TRUE AND rm.room_id = %s
                    ORDER BY u.username
                """
                cursor.execute(query, (room_id,))
            else:
                query = """
                    SELECT id, username, display_name, avatar_color, is_online
                    FROM users
                    WHERE is_online = TRUE
                    ORDER BY username
                """
                cursor.execute(query)
            
            users = cursor.fetchall()
            cursor.close()
            connection.close()
            return users
        except Error as e:
            print(f"Error fetching online users: {e}")
            return []
    return []