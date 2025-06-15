"""
Configuration settings for the CyBot application.
This file centralizes all configurable parameters for the project.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Groq settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-70b-8192"  # Llama 3 70B model
GROQ_TEMPERATURE = 0.7  # Controls randomness (0: deterministic, 1: creative)

# Pinecone settings
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
PINECONE_INDEX_NAME = "langchain-bot"

# Embedding model settings
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # SentenceTransformer model

# Document processing settings
DOCUMENT_DIR = "data"  # Directory containing documents to index
CHUNK_SIZE = 500  # Size of text chunks for processing
CHUNK_OVERLAP = 20  # Overlap between chunks to maintain context

# Chat memory settings
MEMORY_K = 3  # Number of previous exchanges to keep in memory

# Application settings
APP_TITLE = "CyBot - Document Chatbot"
APP_DESCRIPTION = "Ask questions about your documents using AI"
