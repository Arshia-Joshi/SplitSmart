from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId

load_dotenv()

class MongoDB:
    def __init__(self):
        self.connection_string = os.getenv('MONGODB_URI')
        self.database_name = 'splitsmart'
        self.client = None
        self.db = None
        self._is_connected = False
    
    def connect(self):
        try:
            if self._is_connected and self.client:
                return True
                
            self.client = MongoClient(self.connection_string)
            self.db = self.client[self.database_name]
            
            # Test connection
            self.client.admin.command('ping')
            self._is_connected = True
            
            # Ensure collections exist
            self._ensure_collections()
            print("✅ Connected to MongoDB successfully!")
            return True
        except Exception as e:
            print(f"❌ MongoDB connection error: {e}")
            self._is_connected = False
            return False
    
    def _ensure_collections(self):
        """Ensure all required collections exist"""
        collections = self.db.list_collection_names()
        
        required_collections = ['users', 'bill_history', 'split_details', 'notifications']
        
        for coll in required_collections:
            if coll not in collections:
                self.db.create_collection(coll)
                print(f"✅ Created collection: {coll}")
        
        # Create indexes for better performance
        self.db.users.create_index('email', unique=True)
        self.db.users.create_index('username', unique=True)
        self.db.bill_history.create_index('user_id')
        self.db.bill_history.create_index('bill_date')
        self.db.split_details.create_index('bill_id')
        self.db.notifications.create_index('user_id')
        self.db.notifications.create_index([('user_id', 1), ('is_read', 1)])
        
        print("✅ Database indexes created/verified")
    
    def get_db(self):
        """Get database instance, reconnecting if necessary"""
        if not self._is_connected or self.db is None:
            self.connect()
        return self.db
    
    def is_connected(self):
        """Check if database is connected"""
        return self._is_connected
    
    # User operations
    def create_user(self, username, email, password):
        db = self.get_db()
        
        if not self._is_connected:
            return None, "Database connection unavailable"
        
        # Validate input
        if not all([username, email, password]):
            return None, "All fields are required"
        
        if len(password) < 6:
            return None, "Password must be at least 6 characters"
        
        # Check if user already exists
        existing_user = db.users.find_one({
            '$or': [
                {'username': username},
                {'email': email.lower()}
            ]
        })
        
        if existing_user:
            return None, "Username or email already exists"
        
        # Create new user
        user_data = {
            'username': username,
            'email': email.lower(),
            'password_hash': generate_password_hash(password),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        try:
            result = db.users.insert_one(user_data)
            print(f"✅ New user created: {username}")
            return str(result.inserted_id), "User created successfully"
        except Exception as e:
            print(f"Error creating user: {e}")
            return None, "Error creating user"
    
    def authenticate_user(self, email, password):
        db = self.get_db()
        
        if not self._is_connected:
            return None
        
        user = db.users.find_one({'email': email.lower()})
        if user and check_password_hash(user['password_hash'], password):
            print(f"✅ User authenticated: {user['username']}")
            return {
                'id': str(user['_id']),
                'username': user['username'],
                'email': user['email']
            }
        return None
    
    def get_user_by_id(self, user_id):
        db = self.get_db()
        
        if not self._is_connected:
            return None
            
        try:
            user = db.users.find_one({'_id': ObjectId(user_id)})
            if user:
                return {
                    'id': str(user['_id']),
                    'username': user['username'],
                    'email': user['email']
                }
        except Exception as e:
            print(f"Error getting user by ID {user_id}: {e}")
            return None
        return None
    
    def get_user_by_username(self, username):
        """Get user by username - NEW METHOD ADDED"""
        db = self.get_db()
        
        if not self._is_connected:
            return None
            
        try:
            user = db.users.find_one({'username': username})
            if user:
                return {
                    'id': str(user['_id']),
                    'username': user['username'],
                    'email': user['email']
                }
            else:
                print(f"⚠️ User not found by username: {username}")
                return None
        except Exception as e:
            print(f"Error getting user by username {username}: {e}")
            return None
    
    def update_user_profile(self, user_id, update_data):
        """Update user profile information"""
        db = self.get_db()
        
        if not self._is_connected:
            return False, "Database connection unavailable"
        
        try:
            # Remove None values and add updated_at timestamp
            update_data = {k: v for k, v in update_data.items() if v is not None}
            update_data['updated_at'] = datetime.utcnow()
            
            result = db.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                print(f"✅ User profile updated: {user_id}")
                return True, "Profile updated successfully"
            else:
                return False, "No changes made"
                
        except Exception as e:
            print(f"Error updating user profile {user_id}: {e}")
            return False, "Error updating profile"
    
    def close_connection(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            self._is_connected = False
            print("✅ MongoDB connection closed.")

# Global database instance
db_instance = MongoDB()

# Initialize database connection when module is imported
if __name__ == "__main__":
    # Test connection
    if db_instance.connect():
        print("✅ MongoDB connection test successful!")
    else:
        print("❌ MongoDB connection test failed!")

