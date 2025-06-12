#!/usr/bin/env python3
"""
RAG Chatbot implementation that works with all PDFs.
This clean implementation fixes indentation issues and properly
handles PDF content truncation to avoid token limit problems.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFDirectoryLoader, TextLoader
import os
import glob
import json
import re
from typing import List, Tuple, Dict, Any, Optional
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from root directory
dotenv_path = os.getenv("DOTENV_PATH", str(Path(__file__).parent.parent.parent / ".env"))
load_dotenv(dotenv_path)

# Maximum characters to avoid token limit issues
# Adjusted to approximately match the 2048 token limit (roughly 4 chars per token)
MAX_CHARS = 8000

class RAGChatbot:
    _instance = None

    def __new__(cls, *args, **kwargs):
        # Ensure only one instance is created
        if cls._instance is None:
            cls._instance = super(RAGChatbot, cls).__new__(cls)
        return cls._instance

    def __init__(self):        # Prevent repeated initialization
        if getattr(self, '_is_initialized', False):
            return
        self._is_initialized = True
        # Load API key and setup
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.vector_store = None
        self.llm = None
        self.raw_kb_content = ""
        self.qa_pairs = {}
        self.pdf_contents = {}  # Initialize dictionary to store PDF contents
        self.content_sources = {}  # Track which document each chunk came from
        # Initialize components lazily only once
        self._init_vector_store()
        self._init_llm()
        
    def _extract_qa_pairs(self, text: str) -> Dict[str, str]:
        """Extract Q&A pairs from knowledge base text for direct lookup"""
        qa_pairs = {}
        # Find all Q: and A: patterns
        questions = re.findall(r'Q: (.+?)(?=\nA:|\n\n|$)', text, re.DOTALL)
        answers = re.findall(r'A: (.+?)(?=\nQ:|\n\n|$)', text, re.DOTALL)
        
        # Pair them up
        for q, a in zip(questions, answers):
            qa_pairs[q.strip().lower()] = a.strip()
            
        return qa_pairs
    
    def _find_direct_answer(self, query: str) -> Optional[str]:
        """Check if query directly matches a known question"""
        # Clean up the query
        clean_query = query.lower().strip().rstrip("?").strip()
        
        # Direct match
        if clean_query in self.qa_pairs:
            return self.qa_pairs[clean_query]
        
        # Try to find the most similar question
        for question, answer in self.qa_pairs.items():
            # Check if query is very similar to a known question
            if clean_query in question or question in clean_query:
                return answer
                
            # Check for key terms match
            query_terms = set(clean_query.split())
            question_terms = set(question.split())
            common_terms = query_terms.intersection(question_terms)
            # If most of the query terms are in the question
            if len(common_terms) >= max(2, len(query_terms) * 0.7):
                return answer
        
        return None

    def _init_vector_store(self):
        """Initialize the vector store with documents from the knowledge base"""
        # Get documents from knowledge base directory
        knowledge_base_dir = os.path.join(os.path.dirname(__file__), '..', 'knowledge_base')
        documents = []
        self.raw_kb_content = ""  # Store raw knowledge base content for direct matching
          # Read all text files in the knowledge base directory
        for file_path in glob.glob(os.path.join(knowledge_base_dir, '*.txt')):
            with open(file_path, 'r') as f:
                text = f.read()
                file_name = os.path.basename(file_path)
                self.raw_kb_content += f"[From {file_name}]\n{text}\n\n"
                documents.append({"content": text, "source": file_name})
        
        # Load PDF files from the knowledge base directory        
        pdf_docs = []
        try:
            # First, check if PDF files exist
            pdf_files = glob.glob(os.path.join(knowledge_base_dir, "*.pdf"))
            
            if pdf_files:  # Only attempt to load if PDF files exist
                # Load PDFs
                pdf_loader = PyPDFDirectoryLoader(knowledge_base_dir, glob="*.pdf")
                pdf_docs = pdf_loader.load()
                
                # Extract text from PDF docs and add to raw_kb_content
                for i, doc in enumerate(pdf_docs):
                    # Add metadata to track source of content
                    doc_source = doc.metadata.get('source', 'Unknown PDF')
                    doc_source_filename = os.path.basename(doc_source) # Get just the filename
                    self.raw_kb_content += f"[From {doc_source_filename}]\n{doc.page_content}\n\n"
                    
                    # Store PDF content by filename, appending if content already exists
                    if doc_source_filename in self.pdf_contents:
                        self.pdf_contents[doc_source_filename] += f"\n\n{doc.page_content}"
                    else:
                        self.pdf_contents[doc_source_filename] = doc.page_content
        except Exception as e:
            import traceback
            traceback.print_exc()
            pdf_docs = []
          # Parse Q&A pairs for direct lookup
        self.qa_pairs = self._extract_qa_pairs(self.raw_kb_content)
        
        # Combine text documents and PDF documents with their sources
        all_docs = []
        
        # Add text documents with source information
        for doc in documents:
            all_docs.append({"content": doc["content"], "source": doc["source"]})
        
        # Add PDF documents with source information
        for doc in pdf_docs:
            source = os.path.basename(doc.metadata.get('source', 'Unknown PDF'))
            all_docs.append({"content": doc.page_content, "source": source})
        
        # Early exit if there are no documents to process
        if not all_docs:
            self.vector_store = None
            return
        
        # Use multiple fallback approaches for embedding initialization
        try:
            # Split documents into chunks with optimized parameters for better retrieval
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,  # Smaller chunks to ensure more specific retrieval
                chunk_overlap=100,  # Decent overlap to maintain context
                separators=["\n\n", "\n", ". ", " ", ""],  # Try to keep paragraphs together
                keep_separator=False
            )
            
            # Process each document separately to maintain source information
            text_chunks = []
            for doc in all_docs:
                chunks = text_splitter.create_documents([doc["content"]])
                # Add source information to each chunk's metadata
                for chunk in chunks:
                    chunk.metadata["source"] = doc["source"]
                    # Store the chunk with its source for later retrieval
                    chunk_id = f"chunk_{len(text_chunks)}"
                    self.content_sources[chunk_id] = doc["source"]
                    
                text_chunks.extend(chunks)
            
            # First approach: Use HuggingFace embeddings with explicit CPU device
            try:
                embeddings = HuggingFaceEmbeddings(
                    model_name="all-MiniLM-L6-v2", 
                    model_kwargs={"device": "cpu"}
                )
                
                # Create vector store
                self.vector_store = FAISS.from_documents(text_chunks, embeddings)
                return
            except Exception:
                # Silent exception, try alternative approach
                pass
                
            # Second approach: Try with different model loading approach
            try:
                import torch
                embeddings = HuggingFaceEmbeddings(
                    model_name="all-MiniLM-L6-v2",
                    model_kwargs={"device": torch.device('cpu')}
                )
                self.vector_store = FAISS.from_documents(
                    text_chunks, embeddings, normalize_L2=True
                )
                return
            except Exception:
                # Silent exception
                pass            # If we're here, all approaches failed - set vector_store to None
            self.vector_store = None
        except Exception:
            self.vector_store = None
        
    def _init_llm(self):
        """Initialize LLM with Groq"""
        # Use the loaded GROQ API key from initialization
        key = self.groq_api_key
        if not key or key.lower().startswith("your_"):
            # LLM functionality will be limited without a valid key
            self.llm = None
            return
        
        # Use a known working model name
        model_name = "llama3-8b-8192"
        
        # Initialize ChatGroq with validated key
        try:
            self.llm = ChatGroq(
                api_key=key,
                model=model_name,
                temperature=0.2,  # Lower temperature for more deterministic responses
                max_tokens=2048,   # Set maximum token limit to 2048 as requested
            )
        except Exception as e:
            print(f"Error initializing Groq LLM: {e}")
            self.llm = None
    def _format_chat_history(self, chat_history: List[Tuple[str, str]]) -> List[Dict[str, str]]:
        """Format chat history for the LLM"""
        formatted_history = []
        for user_msg, ai_msg in chat_history:
            formatted_history.append(HumanMessage(content=user_msg))
            formatted_history.append(AIMessage(content=ai_msg))
        return formatted_history
        
    def _enhance_query_with_keywords(self, user_query: str) -> str:
        """
        Enhance the user query with relevant keywords to improve retrieval
        Works with all document topics in the knowledge base
        """
        # Define common keywords and their related terms - dynamically include PDF filenames
        keyword_mapping = {
            # "amazon": ["amazon", "amazon case study", "amazon company", "amazon delivery", "amazon logistics"], # Removed Amazon-specific
            "case study": ["case study", "business case", "case analysis", "company profile", "success story"], # Broadened
            "delivery": ["delivery", "home delivery", "package delivery", "shipping", "logistics methods"], # Slightly broadened
            "logistics": ["logistics", "supply chain", "distribution", "transportation", "fulfillment"] # Slightly broadened
        }
        
        # Add PDF filenames as keywords
        for pdf_name in self.pdf_contents.keys():
            base_name = pdf_name.lower().replace('.pdf', '')
            keyword_mapping[base_name] = [base_name, pdf_name.lower(), base_name + " document", base_name + " information"]
        
        # Check if query contains any of our keywords
        query_lower = user_query.lower()
        additional_terms = set()
        
        for key, related_terms in keyword_mapping.items():
            if key in query_lower:
                # Add related terms to enhance the query
                additional_terms.update(related_terms)
        
        # If we found related terms, append them to the query
        if additional_terms:
            enhanced_query = user_query + " " + " ".join(additional_terms)
            return enhanced_query
        
        return user_query
        
    def process_query(self, query: str, chat_history: List[Tuple[str, str]] = None) -> Dict[str, Any]:
        """Process a user query and get a response from the RAG system"""
        if chat_history is None:
            chat_history = []
            
        # Check if query is asking for complaint details before using LLM
        if "complaint" in query.lower() and ("details" in query.lower() or "show" in query.lower() or "get" in query.lower()):
            # This might be a request to get complaint details - will be handled by the UI logic
            return {"response": "FETCH_COMPLAINT", "answer": "Let me fetch that complaint for you", "source_documents": []}
        
        # First, try to find a direct answer in our knowledge base
        direct_answer = self._find_direct_answer(query)
        if direct_answer:
            return {
                "answer": direct_answer,
                "source_documents": []
            }
            
        # Check if vector_store initialization failed
        if self.vector_store is None:
            return {
                "answer": "I'm sorry, but I'm currently experiencing technical difficulties with my knowledge retrieval system. I can only answer very basic questions right now. For more complex inquiries, please contact our customer service at 1800-302-199 (Toll Free).",
                "source_documents": []
            }
              # Create a retriever and get relevant documents
        try:
            # Enhance the query with relevant keywords for better retrieval
            enhanced_query = self._enhance_query_with_keywords(query)
            
            # Use enhanced query for retrieval with higher k for more context
            retriever = self.vector_store.as_retriever(search_kwargs={"k": 5})
            relevant_docs = retriever.invoke(enhanced_query)
            
            # Process and format the retrieved documents
            context_texts = []
            source_files = set()
            
            for doc in relevant_docs:
                # Extract source information
                source = doc.metadata.get('source', 'Unknown')
                source_files.add(source)
                
                # Format the context with source attribution
                context_text = f"[From {source}]: {doc.page_content}"
                context_texts.append(context_text)
            
            # Join all context texts with clear separation
            context_text = "\n\n---\n\n".join(context_texts)
              # Generic approach to check for case studies or specific sections in any PDF
            # Check if query mentions case studies or specific document names
            query_lower = query.lower()
            for pdf_name, content in self.pdf_contents.items():
                if pdf_name not in source_files:  # Only add if not already retrieved
                    pdf_name_lower = pdf_name.lower().replace('.pdf', '')
                    
                    # Check if the query specifically mentions this PDF
                    if pdf_name_lower in query_lower or "case study" in query_lower:
                        # Try to find any case study section in the PDF
                        case_study_match = re.search(r'(?i)CASE STUDY.+?(?=\n\n\d+\.|\Z)', content, re.DOTALL)
                        if case_study_match:
                            case_study_content = case_study_match.group(0)
                            context_text += f"\n\n---\n\n[From {pdf_name} - CASE STUDY SECTION]: {case_study_content}"
                            break  # Only add one case study to avoid context length issues
            
        except Exception as e:
            print(f"Error in document retrieval: {e}")
            # Silent error handling for production
            return {
                "answer": "I apologize, but I encountered an error while searching for information. Please try a different question or contact our customer service at 1800-302-199 (Toll Free) for assistance.",
                "source_documents": []
            }
        
        # If we have relevant documents but no Groq API key, try to extract an answer from them
        if not self.llm:
            # Simple extraction-based response
            return {
                "answer": f"Based on our information: {context_text[:500]}...\n\nPlease note: The chatbot is operating with limited functionality as the LLM service is not configured.",
                "source_documents": relevant_docs
            }            
        # Convert the chat history to the format expected by the LLM
        formatted_history = self._format_chat_history(chat_history)
        
        try:
            # Create the RAG prompt with improved instructions
            rag_prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="""You are a helpful customer service assistant named CyBot Support Assistant.
                You have access to PDF documents and knowledge base content.
                
                Use the following context to answer the user's question based ONLY on the information in these documents.
                The context contains information from PDFs and text files, with source attribution in [From X] format.
                
                If the document source is included in the context (like [From document.pdf]), always reference it in your answer.
                
                If the exact information requested is not found in the context, respond with: "I don't have specific information about this topic in my knowledge base. Please contact our customer service at 1800-302-199 (Toll Free) to know more about this topic."
                
                Don't respond with vague, generic answers. Be honest when you don't know.
                
                Always be polite, professional, and concise in your responses.
                Always provide attribution when referencing information from documents (e.g., "According to my knowledge...").
                
                Context:
                {context}"""),
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessage(content="{question}")
            ])
              # Process context text to prioritize the most relevant parts before truncation
            if len(context_text) > 20000:
                query_terms = set(query.lower().split())
                # Split into document sections by source
                sections = re.split(r'\n\n---\n\n', context_text)
                scored_sections = []
                
                for section in sections:
                    # Score based on keyword matches
                    section_lower = section.lower()
                    matched_terms = sum(1 for term in query_terms if term in section_lower)
                    score = matched_terms / (len(section) + 1) * 1000  # Normalize by length
                    scored_sections.append((score, section))
                
                # Sort by relevance
                scored_sections.sort(reverse=True)
                
                # Build optimal context with highest-scoring sections
                optimized_context = ""
                total_chars = 0
                max_chars = 20000
                
                for _, section in scored_sections:
                    if total_chars + len(section) + 10 > max_chars:
                        # If adding this section would exceed the limit, stop
                        if total_chars == 0:
                            # Special case: first section exceeds limit, so truncate it
                            optimized_context = section[:max_chars]
                            total_chars = len(optimized_context)
                        break
                    
                    if optimized_context:
                        optimized_context += "\n\n---\n\n"
                    
                    optimized_context += section
                    total_chars += len(section) + 10  # Account for section separator
                
                truncated_context = optimized_context
                print(f"Context text optimized from {len(context_text)} to {len(truncated_context)} characters")
            else:
                truncated_context = context_text
            
            # Create the chain
            chain = (
                {
                    "context": lambda x: truncated_context,
                    "question": lambda x: x,
                    "chat_history": lambda x: formatted_history
                }
                | rag_prompt
                | self.llm
                | StrOutputParser()
            )
            
            # Run the chain
            answer = chain.invoke(query)
            
            # Check if the response contains generic text patterns suggesting no specific knowledge
            generic_responses = [
                "I'd be happy to help",
                "I don't have specific information",
                "I don't have information about this", 
                "I don't have that information",
                "not available in my knowledge base",
                "not found in the context",
                "don't have detailed information",
                "I don't have information on",
                "not mentioned in"
            ]
            
            if any(phrase in answer for phrase in generic_responses):
                # Try our specialized PDF content query method for any PDF
                pdf_answer = self.query_pdf_content(query)
                if pdf_answer and not any(phrase in pdf_answer for phrase in generic_responses):
                    return {
                        "answer": pdf_answer,
                        "source_documents": relevant_docs
                    }
                
                # If we have any PDFs, try each one until we get a good response
                for pdf_name in self.pdf_contents.keys():
                    print(f"Trying direct query with {pdf_name}")
                    direct_answer = self.query_specific_pdf_with_groq(query, pdf_name)
                    if direct_answer and not any(phrase in direct_answer for phrase in generic_responses):
                        return {
                            "answer": direct_answer,
                            "source_documents": relevant_docs
                        }
                
                # Replace with a clear, specific "not found" response that includes the query topic
                answer = f"I'm sorry, I don't have specific information about '{query}' in my knowledge base. Please contact our customer service at 1800-302-199 (Toll Free) to know more about this topic."
            
            return {
                "answer": answer,
                "source_documents": relevant_docs
            }
        except Exception:
            # Silent error handling for production
            return {
                "answer": "I apologize, but I encountered an error processing your question. Please try rephrasing or ask a different question.",
                "source_documents": relevant_docs
            }
    
    def get_all_questions(self) -> List[str]:
        """Get all direct questions from the knowledge base"""
        questions = list(self.qa_pairs.keys())
        # Capitalize first letter and add question mark if not present
        questions = [q.capitalize() if q.endswith('?') else q.capitalize() + '?' for q in questions]
        return questions[:6]  # Limit to 6 questions for UI display
        
    def get_response(self, user_query: str, chat_history: List = None) -> str:
        """
        Process a query and return a response string.
        This is a convenience method used by the Streamlit app.
        
        Args:
            user_query: The user's query string
            chat_history: List of previous messages
            
        Returns:
            String response from the chatbot
        """
        # Process the query using the main query processing method
        result = self.process_query(user_query, chat_history)
          # Return just the answer portion of the result
        return result.get("answer", "I'm sorry, I wasn't able to generate a response.")
        
    def get_available_pdf_filenames(self) -> List[str]:
        """Returns a list of PDF filenames loaded into the chatbot."""
        return list(self.pdf_contents.keys())
        
    def query_specific_pdf_with_groq(self, query: str, pdf_filename: str) -> str:
        """
        Answers a query based *only* on the content of a specific PDF using Groq LLM.
        """
        if not self.llm:
            return "I'm sorry, the advanced query service (Groq) is not available at the moment. Please ensure the Groq API key is configured."
            
        pdf_text = self.pdf_contents.get(pdf_filename)
        if not pdf_text:
            return f"I'm sorry, I could not find or load the content for the PDF: '{pdf_filename}'. Please ensure it is in the knowledge_base directory."
              
        # Track original size for logging
        original_size = len(pdf_text)
        
        # First process the query and content to find most relevant sections
        query_terms = set(query.lower().split())
        
        # Search for the most relevant parts of the PDF based on the query
        paragraphs = re.split(r'\n\s*\n', pdf_text)
        scored_paragraphs = []
        
        # Score paragraphs based on keyword matches
        for paragraph in paragraphs:
            if len(paragraph.strip()) < 20:  # Skip very short paragraphs
                continue
                
            # Score based on keyword density
            paragraph_lower = paragraph.lower()
            matched_terms = sum(1 for term in query_terms if term in paragraph_lower)
            score = matched_terms / (len(paragraph) + 1) * 1000  # Normalize by length
            
            scored_paragraphs.append((score, paragraph))
        
        # Sort paragraphs by relevance score (highest first)
        scored_paragraphs.sort(reverse=True)
        
        # Prepare the optimized content with the most relevant paragraphs
        optimized_text = ""
        char_count = 0
        max_chars = MAX_CHARS  # Use our defined maximum character limit
        
        # Add document introduction for context
        intro = pdf_text[:1000]  # First 1000 characters as context
        optimized_text += intro + "\n\n...\n\n"
        char_count += len(intro) + 5
        
        # Add the most relevant paragraphs until we approach the limit
        for _, paragraph in scored_paragraphs[:10]:  # Top 10 most relevant paragraphs
            if char_count + len(paragraph) + 10 > max_chars:
                break
            optimized_text += paragraph + "\n\n"
            char_count += len(paragraph) + 2
        
        # If content is extremely large, truncate it to avoid API errors
        if len(optimized_text) > MAX_CHARS * 2:  # Allow double the normal limit for input
            print(f"Content for {pdf_filename} truncated from {original_size} to {MAX_CHARS * 2} characters to avoid API rate limits")
            pdf_text = optimized_text[:MAX_CHARS * 2]
        else:
            pdf_text = optimized_text
                
        # Create the prompt
        system_content = f"""You are a specialized assistant for {pdf_filename}. 
Your task is to answer the user's question based EXCLUSIVELY on the provided text from this document.
Do not use any external knowledge outside of this text.

Always include specific details from the document in your response. 
Cite statistics, numbers, and examples when available in the text.

If the answer cannot be found in the provided text, say clearly that the information is not available in {pdf_filename}.

Document content:
---
{pdf_text}
---
"""

        human_content = f"Based on {pdf_filename} only, {query}"
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": human_content}
        ]
        
        # Use a lower temperature for more precise answers
        original_temp = self.llm.temperature if hasattr(self.llm, "temperature") else None
        if original_temp is not None:
            self.llm.temperature = 0.1
        
        try:
            # Direct invoke for more reliable behavior
            response = self.llm.invoke(messages)
            answer = response.content
            
            # Reset temperature if needed
            if original_temp is not None:
                self.llm.temperature = original_temp
                
            # Handle empty responses
            if not answer or not answer.strip():
                return f"I couldn't find relevant information about this in {pdf_filename}."
            
            # Add attribution if not present
            if pdf_filename not in answer:
                answer = f"According to {pdf_filename}: {answer}"
                
            return answer
            
        except Exception as e:
            # Reset temperature if modified
            if original_temp is not None:
                self.llm.temperature = original_temp
                
            print(f"Error during PDF query: {e}")
            return f"I encountered an error while processing your question about {pdf_filename}. Please try again."
            
    def query_pdf_content(self, query: str, pdf_filename: str = None) -> str:
        """
        Generic method that answers a query based on content of any PDF.
        Handles token limit issues by truncating content.
        """
        if not self.llm:
            return None  # No LLM available

        # If no specific PDF provided, check if query indicates a specific document
        if not pdf_filename:
            pdf_filename = self._determine_relevant_pdf(query)
            if not pdf_filename:
                # No specific PDF determined
                return None
                
        # First try to load any pre-extracted content file for this PDF
        extracted_file = os.path.join(os.path.dirname(__file__), f"{pdf_filename.replace('.pdf', '')}_extract.txt")
        
        # If extracted file exists, use it
        if os.path.exists(extracted_file):
            try:
                with open(extracted_file, "r", encoding="utf-8") as f:
                    extracted_content = f.read()
                    
                return self._query_with_extracted_content(query, extracted_content, pdf_filename)
            except Exception as e:
                print(f"Error loading extracted content: {e}")
                # Fall through to PDF content method
        
        # Use the PDF content directly as fallback
        if pdf_filename in self.pdf_contents:
            return self.query_specific_pdf_with_groq(query, pdf_filename)
            
        return None

    def _determine_relevant_pdf(self, query: str) -> str:
        """
        Determines the most relevant PDF based on the query text.
        Works with any PDF in the knowledge base.
        """
        # Get available PDFs
        available_pdfs = list(self.pdf_contents.keys())
        if not available_pdfs:
            return None
            
        query_lower = query.lower()
        
        # Check for direct PDF name mentions
        for pdf in available_pdfs:
            pdf_name = pdf.lower().replace('.pdf', '')
            if pdf_name in query_lower:
                return pdf
                
        # For other PDFs, try to find the most relevant one based on content keywords
        highest_match_count = 0
        best_pdf = None
        
        # Parse query into potential keywords
        query_words = set(query_lower.split())
        
        # Check each PDF's content for keyword matches
        for pdf, content in self.pdf_contents.items():
            content_lower = content.lower()
            match_count = sum(1 for word in query_words if word in content_lower and len(word) > 3)
            
            if match_count > highest_match_count:
                highest_match_count = match_count
                best_pdf = pdf
        
        # If we found a good match
        if highest_match_count >= 2 and best_pdf:
            return best_pdf
            
        # If only one PDF exists, use it as default
        if len(available_pdfs) == 1:
            return available_pdfs[0]
            
        # No specific PDF determined
        return None

    def _query_with_extracted_content(self, query: str, content: str, source_name: str) -> str:
        """
        Queries the LLM using extracted content from a document.
        Optimized to avoid token limit issues with Groq.
        """
        # Track original size for logging
        original_size = len(content)
        
        # Process content to find most relevant sections for the query
        query_terms = set(query.lower().split())
        
        # Split content into paragraphs
        paragraphs = re.split(r'\n\s*\n', content)
        scored_paragraphs = []
        
        # Score paragraphs based on keyword matches
        for paragraph in paragraphs:
            if len(paragraph.strip()) < 20:  # Skip very short paragraphs
                continue
                
            # Score based on keyword density
            paragraph_lower = paragraph.lower()
            matched_terms = sum(1 for term in query_terms if term in paragraph_lower)
            score = matched_terms / (len(paragraph) + 1) * 1000  # Normalize by length
            
            scored_paragraphs.append((score, paragraph))
        
        # Sort paragraphs by relevance score (highest first)
        scored_paragraphs.sort(reverse=True)
        
        # Take top relevant paragraphs until we approach the limit
        relevant_content = ""
        char_count = 0
        char_limit = MAX_CHARS - 2000  # Leave room for context
        
        # Get document intro for context (up to 2000 chars)
        intro = content[:2000] if len(content) > 2000 else content[:int(len(content)/10)]
        
        for _, paragraph in scored_paragraphs[:10]:  # Top 10 relevant paragraphs
            if char_count + len(paragraph) + 10 > char_limit:
                break
            relevant_content += paragraph + "\n\n"
            char_count += len(paragraph) + 2
            
        # Combine intro with relevant sections
        final_content = f"{intro}\n\n...\n\n{relevant_content}"
        
        # If content is extremely large, truncate it to avoid API errors
        if len(final_content) > MAX_CHARS * 2:  # Allow double the normal limit for input
            print(f"Content for {source_name} truncated from {original_size} to {MAX_CHARS * 2} characters to avoid API rate limits")
            final_content = final_content[:MAX_CHARS * 2]
        
        # Create direct messages for more reliable behavior
        system_content = f"""You are a specialized assistant focusing on information from {source_name}.
Your task is to answer the user's question based EXCLUSIVELY on the provided extract from this document.
Do not use any external knowledge outside of this text.

Always include specific details from the document in your response.
Cite statistics, numbers, and examples when available in the text.

If the answer cannot be found in the provided text, state clearly that the information is not available in the document.

Document extract:
---
{final_content}
---
"""

        human_content = f"Based on the document {source_name}, {query}"
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": human_content}
        ]
        
        # Use a lower temperature for more precise answers
        original_temp = self.llm.temperature if hasattr(self.llm, "temperature") else None
        if original_temp is not None:
            self.llm.temperature = 0.1
        
        try:
            # Invoke the LLM
            response = self.llm.invoke(messages)
            answer = response.content
            
            # Reset temperature if needed
            if original_temp is not None:
                self.llm.temperature = original_temp
                  
            # Truncate answer if needed
            if len(answer) > MAX_CHARS:
                print(f"Answer truncated from {len(answer)} to {MAX_CHARS} characters")
                answer = answer[:MAX_CHARS] + "... [Response truncated due to length]"
                
            # Ensure attribution
            if source_name not in answer:
                answer = f"Based on {source_name}: {answer}"
                
            return answer
            
        except Exception as e:
            # Reset temperature if modified
            if original_temp is not None:
                self.llm.temperature = original_temp
                
            print(f"Error in extracted content query: {e}")
            return f"I encountered an error processing your question about {source_name}. Please try again."
