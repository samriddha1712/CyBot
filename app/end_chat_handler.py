"""
Helper module containing functions for ending chat
"""

import streamlit as st

def add_end_chat_button():
    """Add an End Chat button to the sidebar"""
    def sidebar_end_chat_handler():
        # Clear any follow-up button clicks first to prevent them being processed
        st.session_state.yes_clicked = False
        st.session_state.no_clicked = False
        # Add the final exchange
        from app.streamlit_app import add_message
        add_message("user", "I want to end this chat")
        add_message("bot", "Thank you for chatting with me today. This conversation has been ended. You can start a new conversation by clicking the 'Start New Conversation' button below.")
        # Mark conversation as ended
        st.session_state.conversation_ended = True
        # Hide all UI elements except for the chat history
        st.session_state.show_options = False
        st.experimental_rerun()  # Direct rerun to update UI
        
    # Add End Chat button to the sidebar
    st.button("🛑 End Chat", key="end_chat_sidebar", 
            use_container_width=True,
            on_click=sidebar_end_chat_handler)
