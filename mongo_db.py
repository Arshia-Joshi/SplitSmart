from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId

load_dotenv()

class MongoDB:
    def __init__(self):
        self.connection_string = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        self.database_name = 'splitsmart'
        self.client = None
        self.db = None
    
    def connect(self):
        try:
            self.client = MongoClient(self.connection_string)
            self.db = self.client[self.database_name]
            
            # Ensure collections exist
            self._ensure_collections()
            print("✅ Connected to MongoDB successfully!")
            return True
        except Exception as e:
            print(f"❌ MongoDB connection error: {e}")
            return False
    
    def _ensure_collections(self):
        """Ensure all required collections exist"""
        collections = self.db.list_collection_names()
        
        required_collections = ['users', 'bill_history', 'split_details', 'notifications']
        
        for coll in required_collections:
            if coll not in collections:
                self.db.create_collection(coll)
                print(f"✅ Created collection: {coll}")
    
    def get_db(self):
        if self.db is None:
            self.connect()
        return self.db
    
    # User operations
    def create_user(self, username, email, password):
        db = self.get_db()
        
        # Check if user already exists
        if db.users.find_one({'$or': [{'username': username}, {'email': email}]}):
            return None, "Username or email already exists"
        
        # Create new user
        user_data = {
            'username': username,
            'email': email,
            'password_hash': generate_password_hash(password),
            'created_at': datetime.utcnow()
        }
        
        try:
            result = db.users.insert_one(user_data)
            return str(result.inserted_id), "User created successfully"
        except Exception as e:
            print(f"Error creating user: {e}")
            return None, "Error creating user"
    
    def authenticate_user(self, email, password):
        db = self.get_db()
        
        user = db.users.find_one({'email': email})
        if user and check_password_hash(user['password_hash'], password):
            return {
                'id': str(user['_id']),
                'username': user['username'],
                'email': user['email']
            }
        return None
    
    def get_user_by_id(self, user_id):
        db = self.get_db()
        try:
            user = db.users.find_one({'_id': ObjectId(user_id)})
            if user:
                return {
                    'id': str(user['_id']),
                    'username': user['username'],
                    'email': user['email']
                }
        except Exception as e:
            print(f"Error getting user by ID: {e}")
            return None
        return None
    
    def close_connection(self):
        if self.client:
            self.client.close()
            print("✅ MongoDB connection closed.")

# Global database instance
db_instance = MongoDB()

# Initialize database connection when module is imported
db_instance.connect()