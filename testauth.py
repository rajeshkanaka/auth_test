# To use the requests library, ensure it is installed in your environment.
# You can install it using the following command:
# pip install requests
import requests
import logging  # {{ edit: Import the logging module }}
import json  # {{ edit: Import json for better logging }}

API_BASE_URL = 'https://valuetest.waivit.net'
EMAIL = 'pratiksha.talekar@kanakasoftware.com'
PASSWORD = 'Admin1234!'

# {{ edit: Configure logging to write to testauth_log.log }}
logging.basicConfig(
    filename='testauth_log.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

def authenticate_user(email, password, session):
    """
    Authenticates the user with the ValTool API using a session.

    Args:
        email (str): User's email address.
        password (str): User's password.
        session (requests.Session): Session object to persist cookies.

    Returns:
        dict: JSON response containing authentication tokens.
    
    Raises:
        requests.HTTPError: If the authentication request fails.
    """
    url = f'{API_BASE_URL}/api/login'
    headers = {'Content-Type': 'application/json'}
    data = {'EMail': email, 'Password': password}
    response = session.post(url, json=data, headers=headers)
    response.raise_for_status()
    auth_data = response.json()
    
    # {{ edit: Log the complete API response }}
    logging.debug(f"Authentication Response: {json.dumps(auth_data, indent=2)}")
    
    return auth_data

def main():
    """
    Main function to authenticate and display tokens.
    """
    with requests.Session() as session:
        try:
            auth_data = authenticate_user(EMAIL, PASSWORD, session)
            auth_token = auth_data['waivUser']['meta']['token']  # {{ edit: Extract auth_token correctly }}
            
            # {{ edit: Log the complete API response for analysis }}
            logging.debug(f"Authentication Response: {auth_data}")
            
            # Print all cookies in the session
            all_cookies = session.cookies.get_dict()
            print("All Cookies:", all_cookies)
            
            # Attempt to retrieve 'test_token' from auth_data or cookies
            test_token = auth_data['waivUser']['meta'].get('test_token') or session.cookies.get('test_token') or session.cookies.get('evp-valuation')
            print(f"Auth Token: {auth_token}")
            print(f"Test Token: {test_token}")
        except requests.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err}")  # {{ edit: Log HTTP errors }}
            print(f"HTTP error occurred: {http_err}")
        except Exception as err:
            logging.error(f"An error occurred: {err}")  # {{ edit: Log general errors }}
            print(f"An error occurred: {err}")

if __name__ == '__main__':
    main()
