from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import qa_data
import difflib
import logging
from chatbot import IntelligentChatbot
import asyncio
import re
import traceback  # {{ edit: Import traceback for detailed error logging }}
import os  # {{ edit: Import os for accessing environment variables }}

router = APIRouter()

# Configure logging to capture DEBUG level and add traceback
logging.basicConfig(
    level=logging.DEBUG,  # {{ edit: Set logging level to DEBUG }}
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("chatbot_debug.log"),  # {{ edit: Log to a separate debug file }}
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    user_question: str
    chat_history: list

class ChatResponse(BaseModel):
    response: str
    step: str

def find_best_match(user_question, qa_dict):
    """Finds the best match for the user query in qa_dict."""
    questions = list(qa_dict.keys())
    user_question_normalized = user_question.strip().lower()

    # Exact match (case-insensitive)
    if user_question_normalized in (q.lower() for q in questions):
        # Retrieve the original case question
        original_question = next(q for q in questions if q.lower() == user_question_normalized)
        return qa_dict[original_question], 'exact'

    # Partial match using difflib for fuzzy matching
    matches = difflib.get_close_matches(user_question_normalized, (q.lower() for q in questions), n=1, cutoff=0.6)
    if matches:
        matched_question = next(q for q in questions if q.lower() == matches[0])
        return qa_dict[matched_question], 'partial'

    return None, 'no_match'

def is_us_property_related(user_question):
    keywords = [
        'property', 'real estate', 'us market', 'waivio', 'autoval', 
        'fastr', 'inspection', 'avm', 'appraisal', 'valuation',
        'mortgage', 'home', 'loan', 'housing', 'estate', 'comp',
        'comparable', 'rent', 'land', 'broker', 'agent',
        'valuation', 'market trends', 'equity', 'mortgage rates'
    ]
    pattern = r'\b(' + '|'.join(re.escape(k) for k in keywords) + r')\b'
    return re.search(pattern, user_question.lower()) is not None

def get_next_step(current_step, user_question):
    """
    Determines the next step based on the current step and user question.
    """
    step_mapping = {
        'greeting': 'info_gathering',
        'info_gathering': 'conclusion',
        'conclusion': 'end'
    }
    return step_mapping.get(current_step, 'conclusion')

import asyncio  # Ensure asyncio is imported for asynchronous operations

# Remove or comment out the synchronous OpenAI import
# from openai import OpenAI

# Add import for AsyncOpenAI
from openai import AsyncOpenAI



# Initialize a single instance of IntelligentChatbot to be reused
chatbot_instance = IntelligentChatbot()

async def generate_intelligent_response(user_question):
    """
    Generates an intelligent response using OpenAI's GPT model asynchronously.
    """
    try:
        response = await chatbot_instance.client.chat.completions.create(
            model=chatbot_instance.model,
            messages=[
                {"role": "system", "content": "You are EvalAssist, an expert assistant for WAIV, specializing in the US property market."},
                {"role": "user", "content": user_question}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating intelligent response: {e}")
        logger.debug(traceback.format_exc())  # Log full traceback
        raise

def handle_user_query_backend(user_question, chat_history):
    try:
        answer, match_type = find_best_match(user_question, qa_data.qa_dict)
        if match_type == 'exact':
            next_step = get_next_step(chat_history[-1]['step'] if chat_history else 'greeting', user_question)
            return answer, next_step
        elif match_type == 'partial':
            dataset_answer = answer
            intelligent_response = asyncio.run(generate_intelligent_response(user_question))
            combined_response = f"{dataset_answer}\n\n{intelligent_response}"
            next_step = get_next_step(chat_history[-1]['step'] if chat_history else 'greeting', user_question)
            return combined_response, next_step  # {{ edit: Combine dataset and intelligent responses }}
        elif is_us_property_related(user_question):
            intelligent_response = asyncio.run(generate_intelligent_response(user_question))
            next_step = get_next_step(chat_history[-1]['step'] if chat_history else 'greeting', user_question)
            return intelligent_response, next_step
        else:
            return "I'm sorry, I can only assist with questions related to the US property market and WAIV services.", 'end'
    except Exception as e:
        logger.error(f"Error in handle_user_query_backend: {e}")
        logger.debug(traceback.format_exc())  # {{ edit: Log full traceback }}
        raise

@router.post("/chat")
async def chat(request: ChatRequest):
    user_question = request.user_question
    chat_history = request.chat_history

    try:
        response, next_step = handle_user_query_backend(user_question, chat_history)
        return ChatResponse(response=response, step=next_step)
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        logger.debug(traceback.format_exc())  # {{ edit: Log full traceback at DEBUG level }}
        raise HTTPException(status_code=500, detail="Internal Server Error")


