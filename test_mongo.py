import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError
from dotenv import load_dotenv

# --- 1. Load Environment Variables ---
# This loads the .env file from the current directory
load_dotenv() 
print("Attempting to load .env file...")

# --- 2. Get the Connection String ---
connection_string = os.getenv('MONGODB_URI')

# --- 3. Check and Print the String (CRITICAL DEBUG STEP) ---
print("--- DEBUG ---")
if connection_string:
    # Basic attempt to hide credentials in the print output
    try:
        user_pass, cluster_info = connection_string.split('@')
        user = user_pass.split('//')[1].split(':')[0]
        print(f"Loaded URI (password hidden): mongodb+srv://{user}:****@{cluster_info}")
    except:
        # Fallback if the string is in an unexpected format
        print("Loaded URI (preview): " + connection_string[:40] + "...")
else:
    print("Loaded URI: None")
    print("ERROR: MONGODB_URI is NOT SET or is EMPTY.")
print("-------------")


# --- 4. Attempt Connection ---
if connection_string:
    try:
        print("\nAttempting to connect to MongoDB...")
        
        # Set a short timeout (5 seconds) so it fails fast
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        
        # The 'ping' command is the standard way to test a connection
        client.admin.command('ping')
        
        print("\n✅ SUCCESS: Connection to MongoDB is successful!")

    except ConfigurationError as e:
        # This is likely your specific error!
        print(f"\n❌ CONFIGURATION FAILED: The URI string is malformed.")
        print(f"   Error details: {e}")
        print("\n   ACTION: Check for special characters in your password (like @, :, /) and encode them.")
        print("   Example: 'my@pass' should become 'my%40pass'")
    
    except ConnectionFailure as e:
        print(f"\n❌ CONNECTION FAILED: Could not connect to the server.")
        print(f"   Error details: {e}")
        print("\n   ACTION: Check your internet and firewall settings. If using Atlas, check your IP Allowlist.")
        
    except Exception as e:
        # Catch any other errors
        print(f"\n❌ AN UNEXPECTED ERROR OCCURRED: {e}")
else:
    print("\nTest not run. Fix the MONGODB_URI variable first.")