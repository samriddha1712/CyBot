"""
Conversation state manager for CyBot.
Manages the state of complaint-related conversations.
"""

from typing import Dict, Optional, List
import uuid
import json
import os

class ConversationState:
    """Manages the state of complaint-related conversations."""
    
    def __init__(self):
        self.active_complaints = {}  # session_id -> complaint data
    
    def start_complaint_filing(self, session_id: str) -> Dict:
        """Initialize a new complaint filing process"""
        self.active_complaints[session_id] = {
            "name": None,
            "phone": None,
            "email": None,
            "details": None,
            "current_field": "name"
        }
        return self.active_complaints[session_id]
    
    def update_complaint_data(self, session_id: str, field: str, value: str) -> Dict:
        """Update a field in the complaint data"""
        if session_id not in self.active_complaints:
            self.start_complaint_filing(session_id)
        
        self.active_complaints[session_id][field] = value
        return self.active_complaints[session_id]
    
    def get_complaint_data(self, session_id: str) -> Optional[Dict]:
        """Get current complaint data"""
        return self.active_complaints.get(session_id)
    
    def get_next_field(self, session_id: str) -> Optional[str]:
        """Get the next field that needs to be filled"""
        if session_id not in self.active_complaints:
            return None
        
        data = self.active_complaints[session_id]
        required_fields = ["name", "phone", "email", "details"]
        
        for field in required_fields:
            if not data.get(field):
                return field
        
        return None
    
    def clear_complaint_data(self, session_id: str) -> None:
        """Clear complaint data after submission"""
        if session_id in self.active_complaints:
            del self.active_complaints[session_id]
    
    def is_complaint_complete(self, session_id: str) -> bool:
        """Check if all required fields are filled"""
        if session_id not in self.active_complaints:
            return False
        
        data = self.active_complaints[session_id]
        return all(data.get(field) for field in ["name", "phone", "email", "details"])
