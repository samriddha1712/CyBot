import os
import streamlit as st
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
import groq
from config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_TEMPERATURE,
    PINECONE_API_KEY,
    PINECONE_ENVIRONMENT,
    PINECONE_INDEX_NAME,
    EMBEDDING_MODEL
)

# Initialize Groq client
groq_client = groq.Client(api_key=GROQ_API_KEY)

# Initialize Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)

# Load the embedding model
model = SentenceTransformer(EMBEDDING_MODEL)

# Connect to the Pinecone index
index = pc.Index(PINECONE_INDEX_NAME)

def query_refiner(conversation, query):
    """
    Refines the user query based on the conversation history
    to make it more relevant for retrieval from the knowledge base.
    Uses Groq with the llama3-70b model.
    """
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that refines user queries to make them more relevant for knowledge base retrieval."},
            {"role": "user", "content": f"Given the following user query and conversation log, formulate a question that would be the most relevant to provide the user with an answer from a knowledge base.\n\nCONVERSATION LOG: \n{conversation}\n\nQuery: {query}\n\nRefined Query:"}
        ],
        temperature=GROQ_TEMPERATURE,
        max_tokens=256,
    )
    return response.choices[0].message.content.strip()

def find_match(input):
    """
    Finds the most relevant document matches for the given input query
    using the Pinecone vector index.
    """
    # Encode the input text
    input_em = model.encode(input).tolist()
    
    # Query the Pinecone index with the new API
    try:
        result = index.query(
            vector=input_em,
            top_k=2,
            include_metadata=True
        )
        
        # Combine the text from the top 2 matches
        if result['matches']:
            texts = []
            for match in result['matches']:
                if 'text' in match['metadata']:
                    texts.append(match['metadata']['text'])
            
            return "\n\n".join(texts)
    except Exception as e:
        print(f"Error querying Pinecone index: {str(e)}")
    
    return "No relevant information found."

def get_conversation_string():
    """
    Creates a string representation of the conversation history
    from the Streamlit session state.
    """
    conversation_string = ""
    for i in range(len(st.session_state['responses'])-1):
        conversation_string += "Human: " + st.session_state['requests'][i] + "\n"
        conversation_string += "Bot: " + st.session_state['responses'][i+1] + "\n"
    
    return conversation_string
