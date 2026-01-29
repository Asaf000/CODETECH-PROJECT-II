"""
Database Setup Script for Chat Application
Run this to initialize the database
"""
from config.database import DatabaseConfig
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    print("=" * 60)
    print("Real-Time Chat Application - Database Setup")
    print("=" * 60)
    print()
    
    # Check environment variables
    required_vars = ['DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ ERROR: Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease configure these in the .env file")
        return
    
    print("✓ Environment variables loaded")
    print(f"  Database Host: {os.getenv('DB_HOST')}")
    print(f"  Database User: {os.getenv('DB_USER')}")
    print(f"  Database Name: {os.getenv('DB_NAME')}")
    print()
    
    # Initialize database
    print("Initializing database...")
    db_config = DatabaseConfig()
    
    if db_config.initialize_database():
        print()
        print("Tables created:")
        print("  1. users - User accounts")
        print("  2. rooms - Chat rooms")
        print("  3. messages - Chat messages")
        print("  4. room_members - Room memberships")
        print()
        print("Default rooms created:")
        print("  - General")
        print("  - Technology")
        print("  - Random")
        print()
        print("✅ Setup complete! You can now run: python app.py")
    else:
        print("❌ Database setup failed!")
        print("Please check your MySQL connection and credentials")

if __name__ == '__main__':
    main()