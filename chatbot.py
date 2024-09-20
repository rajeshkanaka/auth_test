import asyncio
import os
import logging
import streamlit as st
import aiohttp

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')  # Use environment variable for API URL

async def handle_user_query_frontend(user_question, chat_history):
    payload = {
        "user_question": user_question,
        "chat_history": chat_history
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{API_BASE_URL}/chatbot/chat', json=payload) as resp:
                resp.raise_for_status()
                chat_response = await resp.json()
                return chat_response['response'], chat_response['step']
    except Exception as e:
        logger.error(f"Error communicating with backend: {e}")
        raise

def run_chatbot():
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        st.warning("Please log in to use the chatbot.")
        return

    st.title("WAIV EvalAssist")

    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get('step'):
                st.markdown(f"*Step:* {message['step']}")

    if prompt := st.chat_input("Ask me anything about the US property market:"):
        with st.chat_message("user"):
            st.markdown(prompt)
            st.markdown(f"*Step:* user_input")

        # Send user input to backend and get response and step
        response_text, next_step = asyncio.run(handle_user_query_frontend(prompt, st.session_state.chat_history))

        with st.chat_message("assistant"):
            st.markdown(response_text)
            st.markdown(f"*Step:* {next_step}")

        # Update chat history
        st.session_state.chat_history.append({"role": "user", "content": prompt, "step": "user_input"})
        st.session_state.chat_history.append({"role": "assistant", "content": response_text, "step": next_step})

if __name__ == "__main__":
    run_chatbot()
