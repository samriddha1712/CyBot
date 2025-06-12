import re
import requests
import json
from typing import Dict, Any, List, Tuple
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

def extract_complaint_id(text: str) -> str:
    """Extract a complaint ID from text"""
    # Look for patterns like "XYZ123", "ABC-123", etc.
    pattern = r'[A-Z0-9]{5,12}'  # Increased range to match larger IDs
    matches = re.findall(pattern, text)
    
    if matches:
        print(f"Extracted complaint ID: {matches[0]}")
        return matches[0]
    
    # If not found with the pattern, check if the input itself might be an ID
    if re.match(r'^[A-Za-z0-9]{5,12}$', text.strip()):
        result = text.strip().upper()
        print(f"Input text appears to be a complaint ID: {result}")
        return result
    
    # Specifically check for your known format like "18E78ACA"
    if re.match(r'^[A-Za-z0-9]{8}$', text.strip()):
        result = text.strip().upper()
        print(f"Input text matches exact complaint ID format: {result}")
        return result
    
    print("No complaint ID found")
    return None

def validate_email(email: str) -> bool:
    """Simple email validation"""
    pattern = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
    return bool(pattern.match(email))

def validate_phone(phone: str) -> bool:
    """Simple phone number validation"""
    pattern = re.compile(r'^\d{10,15}$')
    return bool(pattern.match(phone))

def make_api_request(endpoint: str, method: str = "GET", data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make an API request to the FastAPI backend"""
    base_url = "https://fast-api-bot-samriddha-biswas-projects.vercel.app"  # Updated FastAPI base URL
    url = f"{base_url}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url)
        elif method.upper() == "POST":
            response = requests.post(url, json=data)
        else:
            return {"error": "Unsupported method"}
        
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def identify_user_intent(query: str) -> str:
    """
    Identify user intent to minimize LLM calls
    Returns one of: 'create_complaint', 'get_complaint', 'general_query'
    """
    query_lower = query.lower()
    
    # Check for complaint creation intent
    if any(phrase in query_lower for phrase in ["file a complaint", "submit a complaint", 
                                              "register a complaint", "make a complaint", 
                                              "new complaint", "create complaint"]):
        return "create_complaint"
    
    # Check for complaint retrieval intent
    if any(phrase in query_lower for phrase in ["show complaint", "get complaint", 
                                              "complaint details", "view complaint", 
                                              "find complaint", "check complaint"]):
        return "get_complaint"
    
    # Default to general query
    return "general_query"

def extract_entity_from_text(text: str, entity_type: str) -> Tuple[str, bool]:
    """
    Extract specific entities from text without using LLM
    Returns the entity and whether it was found
    """
    if entity_type == "email":
        email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        matches = re.findall(email_pattern, text)
        return (matches[0], True) if matches else ("", False)
    
    elif entity_type == "phone":
        # Look for sequences of numbers that could be phone numbers
        phone_pattern = r'\b\d{10,15}\b'
        matches = re.findall(phone_pattern, text)
        return (matches[0], True) if matches else ("", False)
    
    elif entity_type == "complaint_id":
        # Look for complaint ID pattern (alphanumeric, with more flexible length)
        id_pattern = r'\b[A-Z0-9]{5,12}\b'
        matches = re.findall(id_pattern, text)
        if matches:
            print(f"Extracted complaint ID: {matches[0]}")
            return (matches[0], True)
        
        # If specific ID pattern not found, try to extract any word that might be an ID
        # This is a fallback for when the user directly inputs just the ID
        words = text.strip().split()
        if len(words) == 1 and re.match(r'^[A-Za-z0-9]{5,12}$', words[0]):
            id_value = words[0].upper()
            print(f"Extracted complaint ID from single word: {id_value}")
            return (id_value, True)
        
        print("No complaint ID found in text")
        return ("", False)
    
    return "", False

# New function for MongoDB connection testing with improved robustness
def test_mongodb_connection() -> Tuple[bool, str]:
    """
    Test MongoDB connection using the configured connection string
    Returns a tuple of (success, message)
    
    This enhanced version uses more robust error handling and retry logic
    """
    import socket
    import time
    
    uri = os.getenv("MONGODB_URI")
    if not uri:
        return False, "MongoDB URI is not configured in environment variables"
        
    # Maximum number of retries
    max_retries = 2
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            # Try to connect with progressive timeouts based on retry count
            timeout_ms = 5000 * (retry_count + 1)
            
            # Configure client with aggressive timeouts
            client = MongoClient(
                uri, 
                serverSelectionTimeoutMS=timeout_ms,
                connectTimeoutMS=timeout_ms,
                socketTimeoutMS=timeout_ms,
                retryWrites=True,
                retryReads=True
            )
            
            # Try a lightweight operation first to test connection
            client.admin.command('ping')
            
            # If ping succeeds, try to access the database
            db_name = os.getenv("DB_NAME", "complaint_system")
            db = client[db_name]
            
            try:
                # Try to list collections with timeout protection
                collections = db.list_collection_names(maxTimeMS=3000)
                collection_count = len(list(collections))
                return True, f"Successfully connected to MongoDB Atlas. Database: {db_name}, Collections: {collection_count}"
            except Exception as e:
                # We could connect but couldn't list collections - still consider this a success
                return True, f"Connected to MongoDB Atlas, but couldn't list collections: {str(e)}"
                
        except socket.timeout:
            # Handle specific timeout errors with retry
            retry_count += 1
            if retry_count <= max_retries:
                time.sleep(1)  # Wait before retrying
                continue
            return False, f"MongoDB connection timed out after {max_retries + 1} attempts. DNS resolution may be failing."
            
        except ConnectionFailure as e:
            retry_count += 1
            if retry_count <= max_retries:
                time.sleep(1)  # Wait before retrying
                continue
            return False, f"Failed to connect to MongoDB Atlas: {str(e)}"
            
        except OperationFailure as e:
            return False, f"Authentication error or insufficient permissions: {str(e)}"
            
        except Exception as e:
            retry_count += 1
            if retry_count <= max_retries:
                time.sleep(1)  # Wait before retrying
                continue
            return False, f"Unexpected error connecting to MongoDB Atlas: {str(e)}"
