"""
Document preprocessing utility for CyBot.

This module provides functions to preprocess various document types 
before indexing them for the chatbot.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
    UnstructuredMarkdownLoader,
    UnstructuredHTMLLoader,
    CSVLoader,
    UnstructuredExcelLoader
)

def get_file_loader(file_path: str):
    """
    Returns the appropriate document loader based on file extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        A LangChain document loader instance
    """
    file_extension = Path(file_path).suffix.lower()
    
    if file_extension == '.pdf':
        return PyPDFLoader(file_path)
    elif file_extension == '.txt':
        return TextLoader(file_path)
    elif file_extension in ['.docx', '.doc']:
        return Docx2txtLoader(file_path)
    elif file_extension == '.md':
        return UnstructuredMarkdownLoader(file_path)
    elif file_extension in ['.html', '.htm']:
        return UnstructuredHTMLLoader(file_path)
    elif file_extension == '.csv':
        return CSVLoader(file_path)
    elif file_extension in ['.xlsx', '.xls']:
        return UnstructuredExcelLoader(file_path)
    else:
        # Default to text loader for unknown types
        return TextLoader(file_path)

def load_document(file_path: str) -> List[Dict[str, Any]]:
    """
    Load a document using the appropriate loader based on file extension.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        List of document chunks with metadata
    """
    loader = get_file_loader(file_path)
    docs = loader.load()
    
    # Add source filename as metadata
    for doc in docs:
        doc.metadata['source'] = os.path.basename(file_path)
    
    return docs

def clean_text(text: str) -> str:
    """
    Clean and normalize text content.
    
    Args:
        text: Raw text content
        
    Returns:
        Cleaned text
    """
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove special characters that might cause issues
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    
    return text

def process_documents(directory: str) -> List[Dict[str, Any]]:
    """
    Process all documents in a directory.
    
    Args:
        directory: Directory containing documents
        
    Returns:
        List of all document chunks with metadata
    """
    all_docs = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                docs = load_document(file_path)
                
                # Clean text content
                for doc in docs:
                    doc.page_content = clean_text(doc.page_content)
                
                all_docs.extend(docs)
                print(f"Processed {file_path}: {len(docs)} chunks")
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
    
    return all_docs
