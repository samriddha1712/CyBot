"""
Fallback utilities for handling failures gracefully.
This module provides fallback mechanisms when core services like MongoDB fail.
"""
import os
import json
import uuid
import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

# Local file storage location for fallbacks
FALLBACK_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
    "fallback_data"
)

def ensure_fallback_storage():
    """Ensure the fallback storage directory exists"""
    if not os.path.exists(FALLBACK_DIR):
        os.makedirs(FALLBACK_DIR)

def save_complaint_locally(name: str, phone_number: str, email: str, complaint_details: str) -> Dict[str, Any]:
    """
    Save complaint to a local file when MongoDB is unavailable
    Returns complaint data including the generated ID
    """
    ensure_fallback_storage()
    
    # Generate a unique ID (similar to MongoDB)
    complaint_id = str(uuid.uuid4())[:8].upper()
    
    # Create complaint data structure
    complaint = {
        "complaint_id": complaint_id,
        "name": name,
        "phone_number": phone_number,
        "email": email,
        "complaint_details": complaint_details,
        "created_at": datetime.datetime.now().isoformat(),
        "status": "PENDING",
        "stored_locally": True,
        "notes": "This complaint was stored locally due to database connection issues."
    }
    
    # Save to a JSON file
    file_path = os.path.join(FALLBACK_DIR, f"complaint_{complaint_id}.json")
    with open(file_path, 'w') as f:
        # Convert datetime to string for JSON serialization
        json.dump(complaint, f, indent=2)
    
    return complaint

def get_local_complaint(complaint_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a locally stored complaint by ID
    Returns None if not found
    """
    ensure_fallback_storage()
    
    # Look for matching complaint file
    file_path = os.path.join(FALLBACK_DIR, f"complaint_{complaint_id}.json")
    
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                complaint = json.load(f)
                # Add indicator that this was retrieved locally
                complaint["retrieved_locally"] = True
                return complaint
        except Exception as e:
            print(f"Error loading local complaint file: {str(e)}")
            return None
    
    # Also try looking through all complaint files
    for filename in os.listdir(FALLBACK_DIR):
        if filename.endswith(".json") and filename.startswith("complaint_"):
            try:
                with open(os.path.join(FALLBACK_DIR, filename), 'r') as f:
                    complaint = json.load(f)
                    # Check if this file contains the complaint we're looking for
                    if complaint.get("complaint_id") == complaint_id:
                        complaint["retrieved_locally"] = True
                        return complaint
            except:
                continue
    
    return None

def list_local_complaints() -> list:
    """List all locally stored complaints"""
    ensure_fallback_storage()
    complaints = []
    
    for filename in os.listdir(FALLBACK_DIR):
        if filename.endswith(".json") and filename.startswith("complaint_"):
            try:
                with open(os.path.join(FALLBACK_DIR, filename), 'r') as f:
                    complaint = json.load(f)
                    complaints.append(complaint)
            except:
                continue
    
    return complaints

class FallbackChatbot:
    """
    A simple fallback chatbot implementation that can be used when the main RAG chatbot is unavailable.
    This provides basic responses to keep the application functional during service disruptions.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the fallback chatbot with basic configuration"""
        self.fallback_knowledge = {
            "shipping": "Standard shipping takes 3-5 business days. Express shipping takes 1-2 business days.",
            "returns": "You can return items within 30 days of purchase. Please include your order number.",
            "contact": "You can reach customer service at support@example.com or call 1-800-555-1234.",
            "hours": "Our customer service hours are Monday-Friday 9am-5pm EST.",
            "complaint": "You can submit a complaint through our form. We'll respond within 48 hours.",
        }
    
    def process_query(self, query: str, chat_history: Optional[List] = None) -> Dict[str, Any]:
        """
        Process a query with a simple keyword-based approach
        Returns a dictionary with answer and context
        """
        query = query.lower()
        
        # Basic keyword matching
        for topic, response in self.fallback_knowledge.items():
            if topic in query:
                return {
                    "answer": response,
                    "context": "I'm currently operating in fallback mode with limited capabilities.",
                    "is_fallback": True
                }
        
        # Default response
        return {
            "answer": "I'm sorry, I'm currently operating with limited capabilities and don't have access to the full knowledge base. Please try again later or contact customer service directly.",
            "context": "Operating in fallback mode",
            "is_fallback": True
        }
    
    def get_response(self, user_query: str, chat_history: List = None) -> str:
        """
        Process a query and return a response string.
        This is a convenience method used by the Streamlit app.
        
        Args:
            user_query: The user's query string
            chat_history: List of previous messages
            
        Returns:
            String response from the chatbot
        """
        # Process the query using the main query processing method
        result = self.process_query(user_query, chat_history)
        
        # Return just the answer portion of the result
        return result.get("answer", "I'm sorry, I wasn't able to generate a response.")
