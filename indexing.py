import os
from langchain_community.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from config import (
    PINECONE_API_KEY,
    PINECONE_ENVIRONMENT,
    PINECONE_INDEX_NAME,
    DOCUMENT_DIR,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    EMBEDDING_MODEL
)

# Initialize Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)

from utils.preprocessing import process_documents

def load_docs(directory):
    """
    Load documents from the specified directory using our custom preprocessing
    """
    documents = process_documents(directory)
    return documents

def split_docs(documents, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    """
    Split the documents into smaller chunks for better processing
    """
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs = text_splitter.split_documents(documents)
    return docs

def main():
    # Directory containing the documents
    directory = DOCUMENT_DIR
    
    # Load and split documents
    print("Loading documents...")
    documents = load_docs(directory)
    print(f"Loaded {len(documents)} documents")
    
    print("Splitting documents...")
    docs = split_docs(documents)
    print(f"Split into {len(docs)} chunks")
    
    # Create embeddings
    print("Creating embeddings...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    
    # Store embeddings in Pinecone
    print("Storing embeddings in Pinecone...")
    index_name = PINECONE_INDEX_NAME
    
    # Check if index already exists
    if index_name not in pc.list_indexes().names():
        # Create a new index
        pc.create_index(
            name=index_name,
            dimension=384,  # Dimension for all-MiniLM-L6-v2
            metric="cosine",
            spec=ServerlessSpec(
                cloud=PINECONE_ENVIRONMENT.split("-")[0],  # e.g. "aws" from "aws-us-west-2"
                region="-".join(PINECONE_ENVIRONMENT.split("-")[1:])  # e.g. "us-west-2" from "aws-us-west-2"
            )
        )
    
    # Get the index instance
    index = pc.Index(index_name)
    
    # Use the new PineconeVectorStore to store documents
    texts = [doc.page_content for doc in docs]
    metadatas = [doc.metadata for doc in docs]
    
    # Create embeddings
    embeddings_list = embeddings.embed_documents(texts)
    
    # Create vector records
    records = []
    for i, (text, metadata, embedding) in enumerate(zip(texts, metadatas, embeddings_list)):
        metadata["text"] = text  # Add text to metadata for retrieval
        records.append({"id": f"doc_{i}", "values": embedding, "metadata": metadata})
    
    # Upsert in batches
    batch_size = 100
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        index.upsert(batch)
    
    # Create a vector store for querying
    vector_store = PineconeVectorStore(
        index=index,
        embedding=embeddings,
        text_key="text"
    )
    print("Indexing complete!")
    
    # Example search
    query = "What is this document about?"
    try:
        similar_docs = vector_store.similarity_search(query, k=2)
        print(f"\nExample query: '{query}'")
        print("Results:")
        for doc in similar_docs:
            print(f"- {doc.page_content[:100]}...")
    except Exception as e:
        print(f"Error during search: {str(e)}")
        print("This is expected during initial setup - the vector store will work when accessed through the main application.")

if __name__ == "__main__":
    main()
