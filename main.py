import os
import re
import streamlit as st
import uuid
from streamlit_chat import message
from langchain_groq import ChatGroq
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
    MessagesPlaceholder
)
from utils import query_refiner, find_match, get_conversation_string
from utils.complaint import ComplaintHandler, IntentRecognizer, ConversationState
from config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_TEMPERATURE,
    MEMORY_K,
    APP_TITLE,
    APP_DESCRIPTION
)

# Set page configuration
st.set_page_config(page_title=APP_TITLE, layout="wide")

# Add custom CSS for better appearance
st.markdown("""
<style>
.stApp {
    max-width: 1200px;
    margin: 0 auto;
}
.chat-container {
    border-radius: 10px;
    padding: 20px;
    background-color: #f5f5f5;
}
.title {
    color: #2e6e80;
    text-align: center;
}
/* Custom styling for the input area */
.stTextInput div {
    padding-bottom: 0px;
}
/* Make form container less obtrusive */
.stForm {
    background-color: transparent !important;
    border: none !important;
    padding: 0 !important;
}
/* Style the submit button */
.stButton button, .stFormSubmitButton button {
    border-radius: 20px;
    height: 45px;
    margin-top: 1px;
    padding-left: 20px;
    padding-right: 20px;
}
/* Hide the default Streamlit text input at the top */
header div[data-testid="stDecoration"] {
    display: none;
}
/* Hide all redundant text inputs except our custom one */
[data-testid="baseButton-headerNoPadding"] {
    display: none;
}
/* Additional hiding for the text area at the top */
header + section > div:first-child > div:first-child {
    visibility: hidden;
    height: 0px;
    min-height: 0px;
    padding: 0px;
    margin: 0px;
}
</style>
""", unsafe_allow_html=True)

# Initialize sidebar options early to avoid undefined variables
with st.sidebar:
    st.subheader("Settings")
    refine_query = st.checkbox("Enable Query Refinement", value=True)

st.markdown("<h1 class='title'>CyBot: Your Smart Assistant</h1>", unsafe_allow_html=True)
st.subheader(APP_DESCRIPTION)

# Initialize session state
if 'responses' not in st.session_state:
    st.session_state['responses'] = ["How can I assist you?"]

if 'requests' not in st.session_state:
    st.session_state['requests'] = []

if 'buffer_memory' not in st.session_state:
    st.session_state.buffer_memory = ConversationBufferWindowMemory(k=MEMORY_K, return_messages=True)
    
# Initialize conversation state for complaints management
if 'conversation_state' not in st.session_state:
    st.session_state.conversation_state = ConversationState()
    
# Initialize session ID for tracking conversations
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    
# Initialize query refinement tracking
if 'query_refinement' not in st.session_state:
    st.session_state.query_refinement = {'original': '', 'refined': ''}

# System message template
system_msg_template = SystemMessagePromptTemplate.from_template(
    template="""Answer the question as truthfully as possible using the provided context. 
    If the user wants or intents to file a complaint, then generate a response that says: To file a complaint, Write in the input box: "I want to file a complaint" and then follow the instructions.
    
    If the user asks about a complaint status, then generate a response that says: To get a complaint details, Write in the input box: "Get complaint status along with the complaint ID".
    
    If the answer is not contained within the text and you don't have enough information, say 'I don't have enough 
    information to answer that question. Please provide more details or check the "Query Refinement" option to refine your question.'
    
    Be concise, helpful, and informative."""
)

# Human message template
human_msg_template = HumanMessagePromptTemplate.from_template(template="{input}")

# Chat prompt template
prompt_template = ChatPromptTemplate.from_messages([
    system_msg_template,
    MessagesPlaceholder(variable_name="history"),
    human_msg_template
])

# Initialize the language model
llm = ChatGroq(
    model_name=GROQ_MODEL,
    groq_api_key=GROQ_API_KEY,
    temperature=GROQ_TEMPERATURE
)

# Initialize the conversation chain
conversation = ConversationChain(
    memory=st.session_state.buffer_memory,
    prompt=prompt_template,
    llm=llm,
    verbose=True
)

# Define functions for handling complaints

def validate_email(email: str) -> bool:
    """
    Validate email format using a more comprehensive regex pattern
    Args:
        email: Email string to validate
    Returns:
        Boolean indicating if email is valid
    """
    # More comprehensive email validation pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    """
    Validate phone number format - accepts various formats
    Args:
        phone: Phone number string to validate
    Returns:
        Boolean indicating if phone number is valid
    """
    # Clean the phone number of common separators
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)
    
    # Check for valid formats:
    # - 10 digits (standard)
    # - With country code (+1, etc.)
    if re.match(r'^\d{10}$', cleaned) or re.match(r'^\+\d{1,3}\d{10}$', cleaned):
        return True
    return False

def handle_complaint_filing(query):
    """
    Handle complaint filing process
    Args:
        query: User's input text
    Returns:
        Response message to display to the user
    """
    state = st.session_state.conversation_state
    session_id = st.session_state.session_id
      # Extract potential complaint information from the query
    extracted_info = IntentRecognizer.extract_complaint_info(query)
    
    # Get or initialize complaint data
    complaint_data = state.get_complaint_data(session_id)
    if not complaint_data:
        complaint_data = state.start_complaint_filing(session_id)
        
        # Update with any extracted information
        for field, value in extracted_info.items():
            state.update_complaint_data(session_id, field, value)
            
        # When first starting a complaint filing, always return the name prompt
        return "To file your complaint, I'll need some information. What is your name?"
    
    # Get or check what we're currently collecting - this is important
    # to track the state of our conversation
    current_field = None
    if session_id in state.active_complaints:
        current_field = state.active_complaints[session_id].get('current_field')
      # Get the next field that needs to be filled
    next_field = state.get_next_field(session_id)
    
    # If there's no current field set but we have a next field,
    # we should set the current field for proper tracking
    if not current_field and next_field:
        state.active_complaints[session_id]['current_field'] = next_field
        current_field = next_field
    
    # Only process the input if we have a current field we're expecting
    if current_field:
        # Track whether the current input was accepted
        input_accepted = False
        
        # Handle name field
        if current_field == 'name':
            # Try to extract from the input or check if it's a direct name input
            if 'name' in extracted_info:
                state.update_complaint_data(session_id, 'name', extracted_info['name'])
                input_accepted = True
            else:
                # Simple heuristic: if it's short and doesn't contain other fields, it might be a name
                words = query.strip().split()
                if 1 <= len(words) <= 3 and '@' not in query and not re.search(r'\d', query):
                    state.update_complaint_data(session_id, 'name', query.strip())
                    input_accepted = True
          # Handle phone field
        elif current_field == 'phone':
            # Check if extracted automatically or from direct input
            if 'phone' in extracted_info and validate_phone(extracted_info['phone']):
                state.update_complaint_data(session_id, 'phone', extracted_info['phone'])
                input_accepted = True
            elif validate_phone(query.strip()):
                state.update_complaint_data(session_id, 'phone', query.strip())
                input_accepted = True
            else:
                # Invalid phone - return error message
                return "Oops! The number you entered is not a valid phone number. Please enter a 10-digit phone number (e.g., 1234567890)."
        
        # Handle email field
        elif current_field == 'email':
            # Check if extracted automatically or from direct input
            if 'email' in extracted_info and validate_email(extracted_info['email']):
                state.update_complaint_data(session_id, 'email', extracted_info['email'])
                input_accepted = True
            elif validate_email(query.strip()):
                state.update_complaint_data(session_id, 'email', query.strip())
                input_accepted = True
            else:
                # Invalid email - return error message
                return "Oops! The email address you entered is not valid. Please enter a valid email address (e.g., name@example.com)."
        
        # Handle details field
        elif current_field == 'details':
            state.update_complaint_data(session_id, 'details', query.strip())
            input_accepted = True
          # If the input was accepted, get the next field
        if input_accepted:
            # Get the updated next field
            next_field = state.get_next_field(session_id)
            
            # Update the current field for next iteration
            if next_field:
                state.active_complaints[session_id]['current_field'] = next_field
            
            # Return a response based on the new field
            if next_field == 'phone':
                return "Thank you. What is your phone number? Please enter a 10-digit number without spaces or special characters."
            elif next_field == 'email':
                return "Got it. Please provide your email address in the format name@example.com."
            elif next_field == 'details':
                return "Thanks. Now, please describe your complaint in detail."
    
    # Prepare response based on what's needed next
    if next_field is None:  # All fields are filled
        # Submit the complaint
        complaint_data = state.get_complaint_data(session_id)
        response = ComplaintHandler.create_complaint(complaint_data)
          # Clear the complaint data
        state.clear_complaint_data(session_id)
        
        if 'complaint_id' in response:
            return f"Your complaint has been registered with ID: {response['complaint_id']}. You'll hear back from us soon."
        elif 'id' in response:
            return f"Your complaint has been registered with ID: {response['id']}. You'll hear back from us soon."
        else:
            return f"There was an issue registering your complaint: {response.get('error', 'Unknown error')}"
    
    # If we reach here with a new complaint but no field processing done yet,
    # just initiate the flow by asking for a name (this should rarely happen due to our logic above)
    if next_field == 'name':
        return "To file your complaint, I'll need some information. What is your name?"
    
    # Default message if we somehow get into an unexpected state
    return "I'm processing your complaint. Could you please provide the requested information?"

def handle_complaint_retrieval(query):
    """
    Handle complaint retrieval process
    Args:
        query: User's input text
    Returns:
        Response message with complaint details or error message
    """
    complaint_id = ComplaintHandler.extract_complaint_id(query)
    if not complaint_id:
        return "I couldn't identify a complaint ID in your message. Please provide a valid complaint ID."
    
    complaint = ComplaintHandler.get_complaint(complaint_id)
    if 'error' in complaint:
        return f"I couldn't find any complaint with ID: {complaint_id}. Please verify the ID and try again."
    
    return ComplaintHandler.format_complaint_details(complaint)

# Create containers for conversation and input
response_container = st.container()
input_container = st.container()

# Create the input container - Using a cleaner chat-like input
with input_container:
    # Use a form with clear_on_submit to automatically clear the input field
    with st.form(key="chat_form", clear_on_submit=True):
        # Create columns for chat input and button
        col1, col2 = st.columns([6, 1])
        
        # Use a smaller, more compact text input without the large white box
        with col1:
            query = st.text_input("", placeholder="Type your message...", 
                                  label_visibility="collapsed", key="chat_input")
        
        with col2:
            submit_button = st.form_submit_button("Send")
    
    # Advanced options collapsible section
    with st.expander("Advanced Options"):
        show_context = st.checkbox("Show retrieved document context", value=False)
    
    # Process the input when the form is submitted
    if submit_button and query:
        with st.spinner("Processing..."):
            # Store the current query for processing
            original_query = query
            
            # Refine query if option is selected
            if refine_query and len(st.session_state['responses']) > 1:
                conversation_string = get_conversation_string()
                refined_query = query_refiner(conversation_string, query)
                # Store the refinement for display in sidebar if enabled
                st.session_state.query_refinement = {
                    'original': query,
                    'refined': refined_query
                }                # Use the refined query for intent detection
                query_for_intent = refined_query
            else:
                query_for_intent = query
            
            # First, check if we're in the middle of filing a complaint
            # This should take priority over other checks to avoid interrupting the flow
            if st.session_state.conversation_state.get_complaint_data(st.session_state.session_id):
                response = handle_complaint_filing(original_query)  # Continue the complaint flow
            else:
                # Only check for complaint ID if we're not already in a complaint flow
                complaint_id = ComplaintHandler.extract_complaint_id(original_query)
                is_retrieval_intent = IntentRecognizer.is_retrieving_complaint(query_for_intent)
                
                # If we have a valid ID and either explicit retrieval intent or complaint context
                if complaint_id and (is_retrieval_intent or "complaint" in query_for_intent.lower()):
                    response = handle_complaint_retrieval(original_query)
                # Check if it's a new complaint-related intent
                elif IntentRecognizer.is_filing_complaint(query_for_intent):
                    response = handle_complaint_filing(original_query)  # Use original for data extraction
                elif is_retrieval_intent:
                    response = handle_complaint_retrieval(original_query)  # Use original for ID extraction
                else:
                    # For regular document queries
                    if refine_query and len(st.session_state['responses']) > 1:
                        context = find_match(refined_query)  # Use refined query if available
                        input_for_llm = f"Context:\n {context} \n\n Query:\n{refined_query}"
                    else:
                        context = find_match(query)
                        input_for_llm = f"Context:\n {context} \n\n Query:\n{query}"
                    
                    # Show context if option is selected
                    if show_context:
                        with st.expander("Document Context"):
                            st.write(context)
                    
                    # Generate response with context
                    response = conversation.predict(input=input_for_llm)
            
            # Store the query and response
            st.session_state.requests.append(query)
            st.session_state.responses.append(response)

# Display the conversation
with response_container:
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    
    if st.session_state['responses']:
        for i in range(len(st.session_state['responses'])):
            message(st.session_state['responses'][i], key=str(i))
            if i < len(st.session_state['requests']):
                message(st.session_state["requests"][i], is_user=True, key=str(i) + '_user')
    
    st.markdown("</div>", unsafe_allow_html=True)

# Add info section at the bottom
st.markdown("---")

# Add a sidebar with additional information
with st.sidebar:
    st.subheader("Settings")
    # refine_query is already defined at the top of the file
    
    # Show query refinement details if enabled
    if st.checkbox("Show Query Refinement Details", value=False) and st.session_state.query_refinement['refined']:
        with st.expander("Last Query Refinement"):
            st.write("**Original**: " + st.session_state.query_refinement['original'])
            st.write("**Refined**: " + st.session_state.query_refinement['refined'])
    
    st.subheader("About")    
    st.write("""
    CyBot is a document-aware chatbot that can answer questions based on your own documents. You can file complaints and also see the details of the complaints.
    """)
      # Add a reset button to clear the conversation
    if st.button("Reset Conversation"):
        st.session_state['responses'] = ["How can I assist you with your documents today?"]
        st.session_state['requests'] = []
        st.session_state.buffer_memory.clear()
        # Also clear any active complaint filing process
        st.session_state.conversation_state.clear_complaint_data(st.session_state.session_id)
        st.session_state.query_refinement = {'original': '', 'refined': ''}
        st.rerun()
