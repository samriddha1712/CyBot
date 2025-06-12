"""
This script provides a direct MongoDB complaint submission function to bypass API issues.
Works both locally and on Streamlit Cloud.
"""
from pymongo import MongoClient
from datetime import datetime
import uuid
import streamlit as st
import string
import random
import os
import sys
from pathlib import Path

# Set up environment using streamlit_config
try:
    from app.streamlit_config import setup_environment, get_mongodb_uri, get_app_settings
    
    # Initialize environment
    setup_environment()
    
    # Get MongoDB URI from environment or secrets
    MONGODB_URI = get_mongodb_uri()
    
    # Get other settings
    app_settings = get_app_settings()
    
except ImportError as e:
    print(f"Error importing streamlit_config: {str(e)}")
    # Fallback to basic environment setup
    parent_dir = Path(__file__).parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.append(str(parent_dir))
    
    from dotenv import load_dotenv
    dotenv_path = os.getenv("DOTENV_PATH", str(Path(__file__).parent.parent / ".env"))
    load_dotenv(dotenv_path)
    
    # Get MongoDB URI directly
    MONGODB_URI = os.getenv("MONGODB_URI")

def generate_complaint_id(length=8):
    """Generate a random alphanumeric complaint ID"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def submit_complaint_direct_to_db(complaint_data):
    """Submit a complaint directly to MongoDB with local fallback"""
    # First try MongoDB submission
    try:
        # Set aggressive timeouts to prevent hanging
        if not MONGODB_URI:
            raise ValueError("MongoDB URI is not available. Check your environment configuration.")
        
        # Connect to MongoDB
        client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=20000,
            socketTimeoutMS=30000
        )
        
        # Use DB name from settings or fallback to default
        db_name = "complaint_system"
        if 'app_settings' in globals():
            db_name = app_settings.get("DB_NAME", db_name)
        
        db = client[db_name]
        complaints = db["complaints"]
        
        # Generate complaint ID
        complaint_id = generate_complaint_id()
        
        # Add complaint ID and timestamp to the data
        complaint_data["complaint_id"] = complaint_id
        complaint_data["created_at"] = datetime.now()
        complaint_data["status"] = "new"
        
        # Insert the complaint (write_concern is set at the client level)
        result = complaints.insert_one(complaint_data)
        print(f"Complaint submitted to MongoDB with ID: {complaint_id}")
        return {
            "complaint_id": complaint_id, 
            "success": True,
            "storage_type": "mongodb"
        }
    except Exception as e:
        print(f"MongoDB submission error: {str(e)}")
        
        # Try local fallback storage
        try:
            # Import the fallback module
            import sys
            import os
            
            # Ensure the fallback module is in path
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            try:
                from app.utils.fallback import save_complaint_locally
            except ImportError:
                # Fallback to direct import if relative import fails
                from utils.fallback import save_complaint_locally
            
            # Extract required fields from complaint_data
            name = complaint_data.get("name", "")
            phone_number = complaint_data.get("phone_number", "")
            email = complaint_data.get("email", "")
            complaint_details = complaint_data.get("complaint_details", "")
            
            # Save locally
            complaint = save_complaint_locally(name, phone_number, email, complaint_details)
            
            print(f"Complaint saved locally with ID: {complaint['complaint_id']}")
            return {
                "complaint_id": complaint['complaint_id'], 
                "success": True,
                "storage_type": "local",
                "warning": "Your complaint was saved locally due to database connectivity issues. It will be synced when the connection is restored."
            }
        except Exception as fallback_error:
            print(f"Both MongoDB and local fallback failed: {str(fallback_error)}")
            return {
                "error": f"Primary error: {str(e)}. Fallback error: {str(fallback_error)}",
                "success": False
            }

# For backwards compatibility
def submit_complaint_direct(complaint_data):
    """Backwards compatibility function that calls submit_complaint_direct_to_db"""
    return submit_complaint_direct_to_db(complaint_data)

# Test function - uncomment to test
if __name__ == "__main__":
    test_data = {
        "name": "Test User",
        "phone_number": "1234567890",
        "email": "test@example.com",
        "complaint_details": "This is a test complaint submitted directly to MongoDB."
    }
    result = submit_complaint_direct_to_db(test_data)
    print(result)
