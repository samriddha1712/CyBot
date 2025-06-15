"""
Intent recognition module for CyBot.
Detects user intents using multiple approaches including regex, fuzzy matching, and NLP.
"""

import re
from typing import Dict, Tuple, List, Optional
from rapidfuzz import fuzz, process
import spacy

# Try to load spaCy model, fall back if not available
try:
    nlp = spacy.load("en_core_web_sm")
except:
    try:
        # Download if not available
        import subprocess
        subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], check=True)
        nlp = spacy.load("en_core_web_sm")
    except:
        nlp = None
        print("Warning: spaCy model not available. Some NLP features will be limited.")

class IntentRecognizer:
    """Recognizes user intents using multiple methods (regex, fuzzy matching, NLP)."""
    
    # Intent examples for matching
    COMPLAINT_FILING_EXAMPLES = [
        "file a complaint", "submit a complaint", "make a complaint",
        "register a complaint", "lodge a complaint", "raise a complaint",
        "complain about", "report an issue", "report a problem",
        "I want to complain", "I need to report", "I have an issue",
        "I'm having a problem", "not satisfied with", "unhappy with"
    ]
    
    COMPLAINT_RETRIEVAL_EXAMPLES = [
        "show me complaint", "view complaint", "check complaint", 
        "retrieve complaint", "what is my complaint", "where is my complaint",
        "track my complaint", "status of complaint", "complaint status",
        "find my complaint", "look up my complaint", "see my complaint details"
    ]
    
    # Regex patterns
    FILING_PATTERNS = [
        r'file\s+a\s+complaint',
        r'submit\s+a\s+complaint',
        r'make\s+a\s+complaint',
        r'register\s+a\s+complaint',
        r'lodge\s+a\s+complaint',
        r'raise\s+a\s+complaint',
        r'complain\s+about',
        r'report\s+an?\s+issue',
        r'report\s+a\s+problem'
    ]
    
    RETRIEVAL_PATTERNS = [
        r'(get|show|view|check|retrieve)\s+(my\s+)?(details|status|info)?\s*(for|of|about)?\s*(complaint|issue|ticket)',
        r'(what|where)\s+is\s+(my\s+)?(complaint|issue|ticket)',
        r'track\s+(my\s+)?(complaint|issue|ticket)',
    ]
    
    @classmethod
    def is_filing_complaint(cls, text: str, threshold: float = 0.7) -> bool:
        """
        Check if user wants to file a complaint using multiple methods
        
        Args:
            text: User input text
            threshold: Threshold for fuzzy matching (0.0-1.0)
            
        Returns:
            Boolean indicating if filing complaint intent was detected
        """
        # 1. Check with regex (exact matches)
        for pattern in cls.FILING_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
          # 2. Try fuzzy matching
        result = process.extractOne(
            text.lower(), 
            cls.COMPLAINT_FILING_EXAMPLES,
            scorer=fuzz.token_set_ratio
        )
        
        if result:
            # Unpack correctly based on what was returned
            if len(result) >= 2:  # At minimum we need match and score
                score = result[1]  # Score is the second element
                if score >= threshold * 100:  # Convert threshold to percentage
                    return True
            
        # 3. Try NLP intent detection if spaCy is available
        if nlp:
            doc = nlp(text.lower())
            
            # Check for complaint-related keywords and verbs indicating action
            filing_keywords = ["complaint", "report", "issue", "problem", "concern"]
            action_verbs = ["file", "submit", "make", "register", "lodge", "raise"]
            
            has_filing_keyword = any(token.text in filing_keywords for token in doc)
            has_action_verb = any(token.lemma_ in action_verbs for token in doc)
            
            if has_filing_keyword and has_action_verb:
                return True
                
        return False
    
    @classmethod
    def is_retrieving_complaint(cls, text: str, threshold: float = 0.7) -> bool:
        """
        Check if user wants to retrieve complaint details using multiple methods
        
        Args:
            text: User input text
            threshold: Threshold for fuzzy matching (0.0-1.0)
            
        Returns:
            Boolean indicating if retrieving complaint intent was detected
        """
        # 1. Check with regex (exact matches)
        for pattern in cls.RETRIEVAL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
          # 2. Try fuzzy matching
        result = process.extractOne(
            text.lower(), 
            cls.COMPLAINT_RETRIEVAL_EXAMPLES,
            scorer=fuzz.token_set_ratio
        )
        
        if result:
            # Unpack correctly based on what was returned
            if len(result) >= 2:  # At minimum we need match and score
                score = result[1]  # Score is the second element
                if score >= threshold * 100:  # Convert threshold to percentage
                    return True
            
        # 3. Try NLP intent detection if spaCy is available
        if nlp:
            doc = nlp(text.lower())
            
            # Check for retrieval-related keywords and verbs
            retrieval_keywords = ["complaint", "ticket", "case", "issue", "status"]
            retrieval_verbs = ["show", "see", "find", "get", "check", "track", "view", "retrieve"]
            
            has_retrieval_keyword = any(token.text in retrieval_keywords for token in doc)
            has_retrieval_verb = any(token.lemma_ in retrieval_verbs for token in doc)
            
            if has_retrieval_keyword and has_retrieval_verb:
                return True
                
        return False
    
    @staticmethod
    def extract_complaint_info(text: str) -> Dict[str, str]:
        """Extract complaint information from text"""
        info = {}
        
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, text)
        if email_match:
            info['email'] = email_match.group(0)
        
        # Extract phone
        phone_pattern = r'\b\d{10}\b|\+\d{1,3}\s?\d{10}\b|\(\d{3}\)\s?\d{3}-\d{4}'
        phone_match = re.search(phone_pattern, text)
        if phone_match:
            info['phone'] = phone_match.group(0)
            
        return info
