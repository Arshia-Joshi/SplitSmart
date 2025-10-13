from mongo_db import MongoDB

def test_mongodb():
    db = MongoDB()
    if db.connect():
        print("🎉 MongoDB is working with Python!")
        
        # Test database operations
        test_db = db.get_db()
        
        # List collections
        collections = test_db.list_collection_names()
        print(f"📁 Collections: {collections}")
        
        db.close_connection()
        return True
    else:
        print("❌ MongoDB connection failed!")
        return False

if __name__ == "__main__":
    test_mongodb()