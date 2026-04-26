import requests
import os
import sys
import base64
import json

# --- CONJUR CLOUD CONFIGURATION ---
# Updated to the secretsmgr subdomain per your requirement
CONJUR_URL = "https://nranktest.secretsmgr.cyberark.cloud/api"
AUTHN_ID = "githubWeatherAuthenticator"
ACCOUNT = "conjur"

def get_github_jwt():
    """Fetches the OIDC JWT from the GitHub Runner environment."""
    request_url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
    request_token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    
    if not request_url or not request_token:
        print("Error: GitHub OIDC environment variables not found.")
        sys.exit(1)
        
    headers = {"Authorization": f"bearer {request_token}"}
    # Requesting audience 'conjur' to match authenticator config
    response = requests.get(f"{request_url}&audience=conjur", headers=headers)
    response.raise_for_status()
    return response.json()['value']

def get_conjur_token(jwt):
    """Exchanges the GitHub JWT for a Conjur Session Token."""
    jwt = jwt.strip()
    
    # URL structure for Conjur Cloud authn-jwt
    auth_url = f"{CONJUR_URL}/authn-jwt/{AUTHN_ID}/{ACCOUNT}/authenticate"
    
    # We use minimal headers to avoid CloudFront validation errors
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        # Pass the JWT in the body as 'jwt=<token>'
        response = requests.post(auth_url, data=f"jwt={jwt}", headers=headers, timeout=10)
        response.raise_for_status()
        
        # Conjur session tokens must be Base64 encoded for the Authorization header
        return base64.b64encode(response.text.encode()).decode()
    except Exception as e:
        print(f"Failed to authenticate with Conjur: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"Status Code: {e.response.status_code}")
             print(f"Response Body: {e.response.text}")
        sys.exit(1)

def get_secret(variable_path, conjur_token):
    """Retrieves a secret value from Conjur using the session token."""
    encoded_path = variable_path.replace("/", "%2F")
    url = f"{CONJUR_URL}/secrets/{ACCOUNT}/variable/{encoded_path}"
    
    headers = {"Authorization": f'Token token="{conjur_token}"'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.text

def fetch_weather(city, api_key):
    """Calls OpenWeather API and prints the report."""
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    
    try:
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        print("\n" + "="*40)
        print(f" WEATHER REPORT FOR: {data['name'].upper()}")
        print("="*40)
        print(f" Temperature: {data['main']['temp']}°C")
        print(f" Condition:   {data['weather'][0]['description'].capitalize()}")
        print(f" Source:      CyberArk Conjur Cloud (JWT)")
        print("="*40 + "\n")
    except Exception as e:
        print(f"OpenWeather API Error: {e}")

if __name__ == "__main__":
    print("--- Initializing Secretless Handshake ---")
    
    # 1. Get the JWT
    github_jwt = get_github_jwt()
    
    # 2. Exchange for Conjur Token
    conjur_session_token = get_conjur_token(github_jwt)
    
    # 3. Pull paths from Screenshot 1
    key_path = "data/vault/DSOWeatherApp/Website-GenericWebApp-10.0.0.1-weatherAPIKey/password"
    city_path = "data/vault/DSOWeatherApp/Website-GenericWebApp-UserSelectedCity-WeatherCity/password"
    
    api_key = get_secret(key_path, conjur_session_token)
    target_city = get_secret(city_path, conjur_session_token)
    
    # 4. Fetch the weather
    fetch_weather(target_city, api_key)
