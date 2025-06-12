import subprocess
import os
import sys
import time
from pathlib import Path

def run_servers():
    # Get the root directory and add it to sys.path
    root_dir = Path(__file__).parent.absolute()
    sys.path.append(str(root_dir))
    
    # Set environment variables to suppress warnings
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"  # Disable HuggingFace symlinks warning
    
    # Import and use the centralized environment manager
    try:
        from app.utils.env_manager import load_environment, validate_required_variables
        
        # Load environment variables
        if not load_environment():
            print("WARNING: Could not load environment variables from .env file")
        
        # Validate required environment variables
        is_valid, missing_vars, warnings = validate_required_variables()
        
        # Show warnings
        for warning in warnings:
            print(f"WARNING: {warning}")
        
        # Exit if required variables are missing
        if not is_valid:
            print("\nERROR: The following required environment variables are not set:")
            for var in missing_vars:
                print(f"  - {var}")
            print("\nPlease make sure you have created a .env file with the required variables.")
            print("Example: MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/complaint_system")
            sys.exit(1)
    except ImportError:
        print("WARNING: Could not import env_manager - falling back to basic checks")
        # Basic fallback check for MONGODB_URI
        if not os.environ.get("MONGODB_URI"):
            print("ERROR: MONGODB_URI environment variable is not set")
            sys.exit(1)
    # Import after loading environment variables
    sys.path.append(str(root_dir))
    from app.utils.helpers import test_mongodb_connection
      # Test MongoDB connection before starting servers with retry mechanism
    print("Testing MongoDB Atlas connection...")
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        success, message = test_mongodb_connection()
        if success:
            print(f"MongoDB connection successful: {message}")
            break
        else:
            retry_count += 1
            print(f"MongoDB connection attempt {retry_count} failed: {message}")
            if retry_count < max_retries:
                print(f"Retrying in 3 seconds...")
                time.sleep(3)
            else:
                print("Maximum retry attempts reached.")
                print("Please check your MongoDB Atlas connection string in .env file")
                if input("Do you want to continue anyway? (y/n): ").lower() != 'y':
                    return
    
    # Start FastAPI server
    print("Starting FastAPI server...")
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"],
        cwd=root_dir
    )
    
    # Wait for API to start
    time.sleep(3)
      # Start Streamlit app with environment variables set to reduce initialization noise
    print("Starting Streamlit app...")
    env = os.environ.copy()
    env["STREAMLIT_SERVER_HEADLESS"] = "1"  # Run in headless mode
    env["PYTHONWARNINGS"] = "ignore::DeprecationWarning"  # Suppress deprecation warnings
    env["STREAMLIT_LOGGER_LEVEL"] = "error"  # Only show error level logs
    
    streamlit_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app/streamlit_app.py"],
        cwd=root_dir,
        env=env
    )
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Handle Ctrl+C
        print("Shutting down servers...")
        api_process.terminate()
        streamlit_process.terminate()
        print("Servers shut down.")

if __name__ == "__main__":
    run_servers()
