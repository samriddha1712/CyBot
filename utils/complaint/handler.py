"""
Complaint handler module for CyBot.
Handles the creation and retrieval of complaints through API calls.
"""

import requests
import re
import os
from typing import Dict, Optional, List, Union
from datetime import datetime

# API base URL - adjust based on your deployment
API_BASE_URL = "https://fast-api-bot-samriddha-biswas-projects.vercel.app"

class ComplaintHandler:
    """Handles the creation and retrieval of complaints via API."""
    
    required_fields = ["name", "phone", "email", "details"]
    
    @staticmethod
    def create_complaint(data: Dict[str, str]) -> Dict:
        """Create a complaint via API call"""
        url = f"{API_BASE_URL}/api/complaints"
        
        # Map the field names to match API expectations
        payload = {
            "name": data.get("name", ""),
            "phone_number": data.get("phone", ""),  # Map phone to phone_number
            "email": data.get("email", ""),
            "complaint_details": data.get("details", "")  # Map details to complaint_details
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()  # Raise exception for error status codes
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"API error: {str(e)}"}
    
    @staticmethod
    def get_complaint(complaint_id: str) -> Dict:
        """Retrieve a complaint by ID"""
        url = f"{API_BASE_URL}/api/complaints/{complaint_id}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {"error": f"Complaint with ID {complaint_id} not found"}
            else:
                return {"error": f"Error retrieving complaint: {response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"error": f"API error: {str(e)}"}
    
    @staticmethod
    def extract_complaint_id(text: str) -> Optional[str]:
        """Extract complaint ID from text using regex patterns"""
        # Look for common patterns like "XYZ123", "complaint XYZ123", etc.
        patterns = [
            # Match "My complaint ID is XYZ123" or similar
            r'(?:my|the)\s+complaint\s+id\s+(?:is|was|:)?\s*([A-Z0-9]{6,})',
            # Match "status of complaint ID: XYZ123" or similar
            r'status\s+of\s+complaint\s+id\s*[:=]?\s*([A-Z0-9]{6,})',
            # Match "what happened to my complaint number XYZ123" or similar
            r'complaint\s+number\s+([A-Z0-9]{6,})',
            # Standard patterns with word boundaries
            r'complaint\s+(?:id\s*[:=]?\s*)?([A-Z0-9]{6,})',
            r'(?:id|complaint id)\s*[:=]?\s*([A-Z0-9]{6,})'
        ]
        
        # If the text is just a simple ID format (like 622A9F6E), capture it directly
        if re.match(r'^[A-Z0-9]{6,}$', text.strip(), re.IGNORECASE):
            return text.strip()
        
        # Try the more specific patterns
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                candidate = match.group(1)
                return candidate
          # Look for alphanumeric patterns that look like IDs with word boundaries
        # Only look for patterns that contain both letters and numbers
        id_pattern = r'\b([A-Z0-9]{6,})\b'
        matches = re.findall(id_pattern, text, re.IGNORECASE)
        if matches:
            # Filter out common words that might be mistaken for IDs
            common_words = ["number", "status", "complaint", "details", "everywhere"]
            for match in matches:
                # Skip common words
                if match.lower() in common_words:
                    continue
                
                # Skip if it's not a likely ID (needs to contain at least one digit and one letter)
                if not (re.search(r'[0-9]', match) and re.search(r'[A-Z]', match, re.IGNORECASE)):
                    continue
                    
                return match
                
        # No valid ID found
        return None
    
    @staticmethod
    def format_complaint_details(complaint: Dict) -> str:
        """Format complaint details for display"""
        created_at = complaint.get('created_at', '')
        if created_at:
            # Format datetime if needed
            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                created_at = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
        
        return (
            f"**Complaint ID**: {complaint.get('complaint_id', complaint.get('_id', 'N/A'))}\n"
            f"**Name**: {complaint.get('name', 'N/A')}\n"
            f"**Phone**: {complaint.get('phone_number', 'N/A')}\n"
            f"**Email**: {complaint.get('email', 'N/A')}\n"
            f"**Details**: {complaint.get('complaint_details', 'N/A')}\n"
            f"**Created At**: {created_at}"
        )
