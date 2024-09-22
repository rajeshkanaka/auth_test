import asyncio
import os
import logging
from typing import List, Dict, Tuple
import streamlit as st
import aiohttp
from openai import AsyncOpenAI
import spacy  # Install spaCy and download the English model
import tiktoken  # Add this import for token counting
import qa_data
import difflib

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("chatbot_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv('VALTOOL_API_URL')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Check for required environment variables
if not API_BASE_URL or not OPENAI_API_KEY:
    logger.error("Missing required environment variables. Please check your .env file.")
    raise EnvironmentError("Missing required environment variables")

nlp = spacy.load('en_core_web_sm')



def num_tokens_from_messages(messages, model="gpt-3.5-turbo"):
    """Returns the number of tokens used by a list of messages."""
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = 0
    for message in messages:
        content = message.get('content', '')
        num_tokens += len(encoding.encode(content))
    return num_tokens

class ContextManager:
    def __init__(self):
        self.dialogue_state = {}
        self.current_topic = None
        self.user_id = None
        self.topic_mapping = {
            "market": "market",
            "valuation": "valuation",
            "inspection": "inspection",
            "transaction": "transaction",
            "financing": "financing",
            "ownership": "ownership",
            "investment": "investment",
            "legal": "legal",
            "professional": "professional",
            "platform": "platform"
        }

    def update_context(self, user_input, intents):
        detected_topic = self._determine_topic(intents)
        if detected_topic != self.current_topic:
            # Handle topic shift
            self.current_topic = detected_topic

    def _determine_topic(self, intents):
        # Implement logic to determine the topic based on intents
        if not intents:
            return self.current_topic  # Remain on the current topic if no new intents found
        # Example logic
        for intent in intents:
            if intent in self.topic_mapping:
                return self.topic_mapping[intent]
        return 'general'

    def get_context(self):
        # Return relevant context for the conversation
        # For now, we can return an empty list or implement if needed
        return []

class IntelligentChatbot:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.model = "gpt-3.5-turbo"  # Use appropriate model name
        self.max_history_length = 10
        self.us_property_topics = {
            "market": ["market", "trends", "housing market", "real estate market"],
            "valuation": ["evaluation", "appraisal", "value", "estimate", "AVM", "FASTR", "AVV", "BPO", "CMA"],
            "inspection": ["inspection", "home inspection", "property inspection", "condition", "inspector"],
            "transaction": ["buying", "selling", "offer", "contract", "negotiation", "closing"],
            "financing": ["mortgage", "rates", "loan", "credit", "pre-approval", "down payment", "refinance"],
            "ownership": ["property tax", "homeowner's insurance", "insurance", "repair", "maintenance", "HOA"],
            "investment": ["investment", "rental", "REIT", "investor", "rental property", "income property"],
            "legal": ["title", "deed", "lien", "zoning", "permit", "occupancy"],
            "professional": ["broker", "agent", "appraiser", "inspector", "attorney"],
            "platform": ["Waivit", "Waiv"]  # Keep platform-specific terms separate
        }
        # Create sets for faster lookup
        self.all_keywords_set = {keyword.lower() for keywords in self.us_property_topics.values() for keyword in keywords}
        self.keyword_to_category = {keyword.lower(): category for category, keywords in self.us_property_topics.items() for keyword in keywords}
        self.intent_keywords = set(self.us_property_topics.keys())
        self.context_manager = ContextManager()
        self.qa_dict = qa_data.qa_dict

    def find_best_match(self, user_question):
        """Finds the best match for the user query in qa_dict."""
        questions = list(self.qa_dict.keys())
        user_question_normalized = user_question.strip().lower()

        # Exact match (case-insensitive)
        if user_question_normalized in (q.lower() for q in questions):
            original_question = next(q for q in questions if q.lower() == user_question_normalized)
            return self.qa_dict[original_question], 'exact'

        # Partial match using difflib for fuzzy matching
        matches = difflib.get_close_matches(user_question_normalized, (q.lower() for q in questions), n=1, cutoff=0.6)
        if matches:
            matched_question = next(q for q in questions if q.lower() == matches[0])
            return self.qa_dict[matched_question], 'partial'

        return None, 'no_match'

    async def generate_response(self, user_question: str, chat_history: List[Dict[str, str]]) -> Tuple[str, str]:
        # Check for exact or partial match in qa_dict
        answer, match_type = self.find_best_match(user_question)
        
        if match_type == 'exact':
            return answer, "qa_exact_match"
        elif match_type == 'partial':
            # Build messages using the existing method to ensure correct format
            messages = self._build_messages(user_question, chat_history)
            generated_response = await self._generate_openai_response(messages)
            combined_response = f"{answer}\n\nAdditional information:\n{generated_response}"
            return combined_response, "qa_partial_match"
        
        # If no match, proceed with existing generation logic
        if not self._is_relevant_question(user_question):
            return self._generate_fenced_response(), "off_topic_response"

        intents = self._extract_intents(user_question)
        self.context_manager.update_context(user_question, intents)

        messages = self._build_messages(user_question, chat_history)

        response = await self._generate_openai_response(messages)
        return response, "chatbot_response"

    async def _generate_openai_response(self, messages: List[Dict[str, str]]):
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )

            chatbot_response = response.choices[0].message.content
            return chatbot_response

        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return "I apologize, but I'm having trouble processing your request. Can I assist you with anything else about the US property market or WAIV services?", "error_response"

    def _build_messages(self, user_question: str, chat_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        # Token limit for the model (e.g., 4096 for gpt-3.5-turbo)
        max_tokens = 4096
        token_budget = max_tokens - 500  # Reserve tokens for response and current input

        messages = [{"role": "system", "content": self._get_system_prompt()}]

        # Include chat history while respecting token limit
        reversed_history = chat_history[-self.max_history_length:][::-1]  # Start from the most recent message
        for message in reversed_history:
            role = message.get('role')
            content = message.get('content')
            if role and content:
                # Ensure the role is one of the allowed values
                if role not in ['system', 'user', 'assistant']:
                    role = 'user'  # Default to user if role is unknown
                
                temp_messages = messages + [{"role": role, "content": content}]
                total_tokens = num_tokens_from_messages(temp_messages, model=self.model)
                if total_tokens <= token_budget:
                    messages.append({"role": role, "content": content})
                else:
                    break  # Stop adding history if token limit is reached

        # Reverse messages to maintain chronological order
        messages = messages[:1] + messages[1:][::-1]  # Keep system prompt at the start

        # Add the current user question
        messages.append({"role": "user", "content": user_question})

        # Log the messages for debugging
        logger.debug(f"Built messages: {messages}")

        return messages

    def _is_relevant_question(self, question: str) -> bool:
        question_lower = question.lower()
        for keyword in self.all_keywords_set:
            if keyword in question_lower:
                category = self.keyword_to_category.get(keyword, "unknown")
                logger.debug(f"Keyword '{keyword}' matched in category '{category}'.")
                return True
        return False

    def _generate_fenced_response(self) -> str:
        return (
            "I specialize in the US Property Market and WAIV services, including evaluations, inspections, and market trends. "
            "While I may not have accurate information about other topics, I'd be happy to assist you with "
            "any questions related to real estate in the United States or WAIV services. What would you like to know?"
        )

    def _get_system_prompt(self) -> str:
        prompt = f"""
        You are EvalAssist, an expert assistant for WAIV, specializing in the US property market.
        Current Topic: {self.context_manager.current_topic}
        Provide accurate, up-to-date information with a professional yet friendly tone.
        Be sure to consider the user's previous questions and intents: {self.context_manager.dialogue_state}
        """
        return prompt.strip()

    def _extract_intents(self, user_question):
        doc = nlp(user_question)
        intents = []
        for token in doc:
            # Check if the lemma of the token matches any intent keyword
            if token.lemma_.lower() in self.intent_keywords:
                intents.append(token.lemma_.lower())
        return intents

chatbot = IntelligentChatbot()

async def handle_user_query_frontend(user_question: str, chat_history: List[Dict[str, str]]) -> Tuple[str, str]:
    # First, try to generate a response locally
    response_text, next_step = await chatbot.generate_response(user_question, chat_history)

    return response_text, next_step

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

    if prompt := st.chat_input("Ask me anything about the US property market or WAIV services:"):
        with st.chat_message("user"):
            st.markdown(prompt)
            st.markdown(f"*Step:* user_input")

        # Send user input to backend and get response and step
        with st.spinner("Thinking..."):
            response_text, next_step = asyncio.run(handle_user_query_frontend(prompt, st.session_state.chat_history))

        with st.chat_message("assistant"):
            st.markdown(response_text)
            st.markdown(f"*Step:* {next_step}")

        # Add feedback buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👍 Helpful"):
                st.success("Thank you for your feedback!")
                # Here you could log positive feedback
        with col2:
            if st.button("👎 Not Helpful"):
                st.error("We're sorry the response wasn't helpful. We'll work on improving.")
                # Here you could log negative feedback

        # Update chat history
        st.session_state.chat_history.append({"role": "user", "content": prompt, "step": "user_input"})
        st.session_state.chat_history.append({"role": "assistant", "content": response_text, "step": next_step})