from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import requests
import logging
from dotenv import load_dotenv
import os
import json  # {{ edit: Import json for better logging }}

router = APIRouter()

# Load environment variables
load_dotenv()
API_BASE_URL = os.getenv('VALTOOL_API_URL')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    auth_token: str
    test_token: str
    user_name: str  # {{ edit: Added user_name to AuthResponse }}
    email: str       # {{ edit: Added email to AuthResponse }}
    phone: str       # {{ edit: Added phone to AuthResponse }}
    organizations: list  # {{ edit: Added organizations to AuthResponse }}

@router.post("/login", response_model=AuthResponse)
def login(auth: AuthRequest):
    url = f"{API_BASE_URL}/api/login"
    headers = {'Content-Type': 'application/json'}
    data = {'EMail': auth.email, 'Password': auth.password}
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        auth_data = response.json()
        
        # {{ edit: Log the entire auth_data for debugging }}
        logger.debug(f"Authentication Response: {json.dumps(auth_data, indent=2)}")
        
        # {{ edit: Extract auth_token from waivUser.meta.token }}
        auth_token = auth_data.get('waivUser', {}).get('meta', {}).get('token', 'N/A')
        
        # {{ edit: Extract test_token from waivUser.meta.test_token if available }}
        test_token = auth_data.get('waivUser', {}).get('meta', {}).get('test_token', 'N/A')
        
        # {{ edit: Extract user details from waivUser.data }}
        user_data = auth_data.get('waivUser', {}).get('data', {})
        user_name = user_data.get('name', 'N/A')
        email = user_data.get('email', 'N/A')
        phone = user_data.get('phone', 'N/A')
        
        # {{ edit: Extract organization names from waivOrgs.data }}
        waiv_orgs = auth_data.get('waivOrgs', {}).get('data', [])
        organizations = [org.get('name', 'N/A') for org in waiv_orgs]
        
        logger.info(f"User {auth.email} authenticated successfully.")
        return AuthResponse(
            auth_token=auth_token,
            test_token=test_token,
            user_name=user_name,
            email=email,
            phone=phone,
            organizations=organizations
        )
    except requests.HTTPError as http_err:
        logger.error(f"HTTP error during authentication for user {auth.email}: {http_err}")
        raise HTTPException(status_code=response.status_code, detail="Authentication failed.")
    except Exception as err:
        logger.error(f"Unexpected error during authentication for user {auth.email}: {err}")
        raise HTTPException(status_code=500, detail="Internal server error.")


