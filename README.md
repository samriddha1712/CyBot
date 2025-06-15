# CyBot - Document-aware Chatbot

CyBot is an advanced document-aware chatbot that can answer questions based on your own documents. By leveraging the power of LangChain, Groq's Llama 3 70B model, and vector databases, CyBot provides accurate responses to user queries while being able to maintain context in conversations.

## Features

- **Document-Aware**: Upload your own documents and get answers based on their content
- **Context-Aware**: The chatbot remembers previous interactions and can handle follow-up questions
- **Query Refinement**: Automatically refines user queries to improve document retrieval
- **Complaint Management**: File and track customer complaints through conversational interface
- **Smart Intent Detection**: Recognizes user intent through regex, fuzzy matching and NLP
- **Interactive UI**: User-friendly interface built with Streamlit
- **Vector Search**: Efficient document retrieval using Pinecone vector database

## Project Structure

```
CyBot/
├── data/                # Directory to store your documents
├── utils/               # Utility functions
│   ├── __init__.py      # Query refinement, document matching, conversation tracking
│   ├── preprocessing.py # Document preprocessing utilities
│   └── complaint/       # Complaint handling functionality
│       ├── __init__.py  # Complaint module initialization
│       ├── handler.py   # API interaction for complaints
│       ├── intent.py    # Intent recognition for complaints
│       └── state.py     # Conversation state management
├── .env                 # Environment variables (API keys)
├── config.py            # Centralized configuration settings
├── indexing.py          # Script to index documents in Pinecone
├── main.py              # Main Streamlit application
├── run.py               # Python startup script
├── run.bat              # Windows batch startup script
├── README.md            # Project documentation
└── requirements.txt     # Python dependencies
```

## Supported File Types

CyBot can process and understand the following document types:

- **PDF** (.pdf) - Articles, reports, manuals
- **Word Documents** (.docx, .doc) - Text documents and reports
- **Plain Text** (.txt) - Simple text notes and data
- **Markdown** (.md) - Documentation and notes
- **HTML** (.html, .htm) - Web pages and exports
- **CSV** (.csv) - Structured data in tabular format
- **Excel** (.xlsx, .xls) - Spreadsheets and data tables

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/CyBot.git
cd CyBot
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your API keys:
```
GROQ_API_KEY=your_groq_api_key_here
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment
```

## Usage

1. **Add your documents**:
   - Place your PDF, TXT, DOCX, etc. files in the `data` directory

2. **Index your documents**:
   ```bash
   python indexing.py
   ```

3. **Run the application**:
   ```bash
   streamlit run main.py
   ```

4. **Access the web interface**:
   - Open your browser and navigate to `http://localhost:8501`

## Advanced Options

- **Query Refinement**: Toggle automatic query refinement based on conversation history
- **Show Context**: Display the retrieved document context with each response
- **Reset Conversation**: Clear the conversation history to start a new chat
- **Show Query Refinement Details**: View how user queries are being refined by the system

## Complaint Management

CyBot can handle customer complaints through its conversation interface:

- **Filing Complaints**: Users can initiate a complaint and the bot will collect required information
- **Retrieving Complaints**: Users can request details about their complaints using the complaint ID
- **Multiple Detection Methods**: Uses regex, fuzzy matching, and NLP to detect complaint-related intents
- **Seamless Integration**: No separate buttons or UI - just converse naturally with the bot

## Requirements

- Python 3.8+
- Groq API key
- Pinecone API key
- Internet connection for API calls

## Acknowledgments

- LangChain for the document processing and chat frameworks
- Groq for the Llama 3 70B model
- Sentence Transformers for embeddings
- Streamlit for the web interface
- Pinecone for vector database services
- spaCy and RapidFuzz for enhanced intent detection

## License

MIT
