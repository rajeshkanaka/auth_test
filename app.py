import os
import streamlit as st
import requests
from chatbot import run_chatbot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_BASE_URL = os.getenv('VALTOOL_API_URL')
if not API_BASE_URL:
    raise ValueError("VALTOOL_API_URL is not set in the environment variables")

def authenticate_user(email, password):
    if not API_BASE_URL:
        st.error("API URL is not set. Please check your environment variables.")
        return None, None
    url = f'{API_BASE_URL}/api/login'
    headers = {'Content-Type': 'application/json'}
    data = {'EMail': email, 'Password': password}
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        auth_response = response.json()
        cookies = response.cookies.get_dict()
        
        # {{ edit: Extract auth_token and test_token correctly }}
        auth_token = auth_response.get('waivUser', {}).get('meta', {}).get('token', '')
        test_token = auth_response.get('waivUser', {}).get('meta', {}).get('test_token', '') or cookies.get('test_token') or cookies.get('evp-valuation', '')
        
        return {
            'auth_token': auth_token,
            'test_token': test_token,
            'user_name': auth_response.get('waivUser', {}).get('data', {}).get('name', 'N/A'),
            'email': auth_response.get('waivUser', {}).get('data', {}).get('email', 'N/A'),
            'phone': auth_response.get('waivUser', {}).get('data', {}).get('phone', 'N/A'),
            'organizations': [org.get('name', 'N/A') for org in auth_response.get('waivOrgs', {}).get('data', [])]
        }, cookies
    except requests.HTTPError as e:
        st.error(f"Authentication failed: {e}")
        return None, None
    except Exception as e:
        st.error("An unexpected error occurred during authentication.")
        logging.error(f"Unexpected error: {e}")  # {{ edit: Log unexpected errors }}
        return None, None
    
    #if user asks any question which is not related to real estate or waivio, then return a message saying that sorry I am only authorised to answer question related to real estate.
    def is_authorised_topic(user_question):
        if "real estate" in user_question.lower() or "waivio" in user_question.lower():
            return True
        else:
            return False  # Corrected indentation

def main():
    st.title("EvalAssist - Your Real Estate Assistant by WAIV")

    if not API_BASE_URL:
        st.error("API URL is not set. Please check your environment variables.")
        return

    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            auth_data, cookies = authenticate_user(email, password)
            if auth_data:
                st.session_state.authenticated = True
                st.session_state.auth_token = auth_data['auth_token']
                st.session_state.test_token = auth_data['test_token']
                st.session_state.user_name = auth_data['user_name']          # {{ edit: Store user_name in session state }}
                st.session_state.email = auth_data['email']                # {{ edit: Store email in session state }}
                st.session_state.phone = auth_data['phone']                # {{ edit: Store phone in session state }}
                st.session_state.organizations = auth_data['organizations']  # {{ edit: Store organizations in session state }}
                st.success("Authentication successful!")
                # {{ edit: Initialize chat history with the first step }}
                st.session_state.chat_history = [{"role": "assistant", "content": "Hello! How can I assist you with the US property market today?", "step": "info_gathering"}]
            else:
                st.error("Authentication failed. Please try again.")
    else:
        # Display User Details and Organization
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write("You are logged in.")
        with col2:
            st.markdown(f"**Name:** {st.session_state.user_name}")          # {{ edit: Display Name }}
            st.markdown(f"**Email:** {st.session_state.email}")             # {{ edit: Display Email }}
            st.markdown(f"**Phone:** {st.session_state.phone}")             # {{ edit: Display Phone }}
            st.markdown(f"**Organizations:** {', '.join(st.session_state.organizations)}")  # {{ edit: Display Organizations }} 

        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.pop('auth_token', None)
            st.session_state.pop('test_token', None)
            st.session_state.pop('user_name', None)          # {{ edit: Remove user_name on logout }}
            st.session_state.pop('email', None)              # {{ edit: Remove email on logout }}
            st.session_state.pop('phone', None)              # {{ edit: Remove phone on logout }}
            st.session_state.pop('organizations', None)      # {{ edit: Remove organizations on logout }}
            st.experimental_rerun()

        # Display chat history with step tracking
        if 'chat_history' in st.session_state:
            for message in st.session_state.chat_history:
                if message['role'] == 'user':
                    st.markdown(f"**You:** {message['content']}")
                    if message.get('step'):
                        st.markdown(f"*Step:* {message['step']}")
                else:
                    st.markdown(f"**EvalAssist:** {message['content']}")
                    if message.get('step'):
                        st.markdown(f"*Step:* {message['step']}")

        # Run the chatbot if authenticated
        run_chatbot()

if __name__ == "__main__":
    main()