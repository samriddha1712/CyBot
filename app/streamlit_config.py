"""
Streamlit configuration helper module for both local and Streamlit Cloud deployments.
This file helps with initializing the app regardless of deployment environment.
"""
import os
import sys
from pathlib import Path
import streamlit as st

# Add project root to path if needed
def setup_environment():
    """
    Sets up the environment for the Streamlit app to run properly
    in both local and cloud environments.
    """
    # Add app directory's parent to system path if not already there
    parent_dir = Path(__file__).parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.append(str(parent_dir))

    # Try to load environment using the centralized manager
    try:
        from app.utils.env_manager import load_environment, is_streamlit_cloud
        
        # Load environment variables
        load_environment()
        
        # Return deployment context
        return {
            "is_cloud": is_streamlit_cloud(),
            "env_loaded": True
        }
    except ImportError as e:
        print(f"Error importing env_manager: {str(e)}")
        # Fallback method
        try:
            from dotenv import load_dotenv
            dotenv_path = Path(__file__).parent.parent / ".env"
            if dotenv_path.exists():
                load_dotenv(dotenv_path)
                return {"is_cloud": False, "env_loaded": True}
        except Exception as e:
            print(f"Error in fallback env loading: {str(e)}")
        
        return {"is_cloud": False, "env_loaded": False}

def get_mongodb_uri():
    """
    Gets the MongoDB URI from the environment or Streamlit secrets.
    """
    # First try environment variable
    mongodb_uri = os.environ.get("MONGODB_URI")
    
    # If not found and in Streamlit Cloud, try secrets
    if not mongodb_uri and "secrets" in dir(st):
        try:
            mongodb_uri = st.secrets["MONGODB_URI"]
        except:
            # Try nested format
            try:
                mongodb_uri = st.secrets.get("mongodb", {}).get("uri")
            except:
                pass
    
    return mongodb_uri

# Cache other common environment variables
def get_app_settings():
    """
    Get application settings from environment variables or Streamlit secrets.
    """
    settings = {}
    
    # Helper function to get a value from env or secrets
    def get_setting(key, default=None):
        # First try environment
        value = os.environ.get(key)
        
        # If not found and in Streamlit Cloud, try secrets
        if value is None and "secrets" in dir(st):
            try:
                value = st.secrets.get(key)
            except:
                pass
        
        return value if value is not None else default
    
    # Get common settings
    settings["GROQ_API_KEY"] = get_setting("GROQ_API_KEY")
    settings["GROQ_MODEL_NAME"] = get_setting("GROQ_MODEL_NAME", "llama3-8b-8192")
    settings["DB_NAME"] = get_setting("DB_NAME", "complaint_system")
    settings["MONGO_COLLECTION"] = get_setting("MONGO_COLLECTION", "complaints")
    settings["DEBUG"] = get_setting("DEBUG", "False") == "True"
    
    return settings
