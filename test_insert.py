
from pymongo import MongoClient

# Connect to local MongoDB
client = MongoClient("mongodb://localhost:27017/")

# Create (or connect to) the database
db = client["splitsmart"]

# Create (or connect to) the users collection
users_collection = db["users"]

# Insert one test user document
test_user = {
    "name": "Test User",
    "email": "test@example.com",
    "password": "hashed_password_example"
}

result = users_collection.insert_one(test_user)
print("✅ Test user inserted with ID:", result.inserted_id)
