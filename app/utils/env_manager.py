"""
Environment management utilities for the CyBot application.
Handles both local development and Streamlit Cloud deployment.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

def is_streamlit_cloud():
    """
    Check if the application is running on Streamlit Cloud.
    """
    return os.getenv("STREAMLIT_RUNTIME") == "1" or os.getenv("STREAMLIT_SHARING") == "1"

def load_environment():
    """
    Unified environment loading function that works both locally
    and on Streamlit Cloud.
    """
    # On Streamlit Cloud, load environment variables from secrets.toml
    if is_streamlit_cloud():
        print("Running on Streamlit Cloud - loading secrets")
        try:
            import streamlit as st
            # Transfer secrets to environment variables
            for key, value in st.secrets.items():
                if isinstance(value, dict):
                    # Handle nested secrets
                    for subkey, subvalue in value.items():
                        full_key = f"{key}_{subkey}".upper()
                        if not os.environ.get(full_key):
                            os.environ[full_key] = str(subvalue)
                else:
                    # Handle top-level secrets
                    if not os.environ.get(key):
                        os.environ[key] = str(value)
            return True
        except Exception as e:
            print(f"Failed to load Streamlit secrets: {str(e)}")
            return False
      # For local development, try to find and load .env file
    root_dir = Path(__file__).parent.parent.parent
    dotenv_path = os.getenv("DOTENV_PATH", str(root_dir / ".env"))
    
    # Load environment variables
    if os.path.exists(dotenv_path):
        print(f"Loading environment variables from {dotenv_path}")
        load_dotenv(dotenv_path, override=True)
        return True
    else:
        print(f"Warning: .env file not found at {dotenv_path}")
        return False

def validate_required_variables():
    """
    Validates that all required environment variables are set.
    Returns a tuple (is_valid, missing_vars, warnings).
    """
    required_vars = ["MONGODB_URI"]
    optional_vars = ["GROQ_API_KEY", "GROQ_MODEL_NAME"]
    
    missing = []
    warnings = []
    
    # Check required variables
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    # Check optional variables and give warnings
    for var in optional_vars:
        if not os.getenv(var):
            warnings.append(f"{var} is not set - some features may not work properly")
    
    # Special validation for GROQ_API_KEY format
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key and not groq_api_key.startswith("gsk_"):
        warnings.append("GROQ_API_KEY appears to be in an invalid format")
    
    is_valid = len(missing) == 0
    return is_valid, missing, warnings

def get_environment_info():
    """
    Returns information about the current environment setup.
    """
    return {
        "GROQ_API_KEY": "***" if os.getenv("GROQ_API_KEY") else None,
        "GROQ_MODEL_NAME": os.getenv("GROQ_MODEL_NAME"),
        "MONGODB_URI": "***" if os.getenv("MONGODB_URI") else None,
        "DB_NAME": os.getenv("DB_NAME"),
    }
