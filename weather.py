import requests
import os
import sys
import base64
import json

# --- CONFIG ---
# Ensure this matches your subdomain exactly
CONJUR_URL = "https://nranktest.secretsmgr.cyberark.cloud/api"
AUTHN_ID = "githubWeatherAuthenticator"
ACCOUNT = "conjur"

def get_github_jwt():
    """Fetches the OIDC JWT from the GitHub Runner environment."""
    url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
    token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    
    if not url or not token:
        print("Error: GitHub OIDC variables missing. Check your YAML 'permissions'.")
        sys.exit(1)
        
    # We request audience 'conjur' to match the Authenticator configuration
    headers = {"Authorization": f"bearer {token}"}
    resp = requests.get(f"{url}&audience=conjur", headers=headers)
    resp.raise_for_status()
    return resp.json()['value']

def get_conjur_token(jwt):
    """Exchanges the GitHub JWT for a Conjur Session Token."""
    jwt = jwt.strip()
    
    # THE "SHORT" URL: We do NOT put the host ID in the URL path.
    # Conjur finds the identity 'weatherAppFetcher' via the 'workflow' claim in the token.
    auth_url = f"{CONJUR_URL}/authn-jwt/{AUTHN_ID}/{ACCOUNT}/authenticate"
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    try:
        # Send the JWT in the body as 'jwt=VALUE'
        response = requests.post(auth_url, data=f"jwt={jwt}", headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"--- LOGIN FAILED ---")
            print(f"Status: {response.status_code}")
            print(f"Body:   {response.text}")
            print(f"URL Attempted: {auth_url}")
            sys.exit(1)
            
        # The response text IS the token. We base64 encode it for the 'Token token=' header.
        return base64.b64encode(response.text.encode()).decode()
    except Exception as e:
        print(f"Handshake failed: {e}")
        sys.exit(1)

def get_secret(path, token):
    """Fetches a secret. Errors here mean the 'Delegation Group' is likely missing the workload."""
    encoded_path = path.replace('/', '%2F')
    url = f"{CONJUR_URL}/secrets/{ACCOUNT}/variable/{encoded_path}"
    
    headers = {"Authorization": f'Token token="{token}"'}
    resp = requests.get(url, headers=headers)
    
    if resp.status_code != 200:
        print(f"--- SECRET FETCH FAILED ---")
        print(f"Path:   {path}")
        print(f"Status: {resp.status_code}")
        print(f"Error:  {resp.text}")
        sys.exit(1)
    return resp.text

if __name__ == "__main__":
    print("--- 1. Authenticating with Conjur Cloud (Secretless) ---")
    github_jwt = get_github_jwt()
    conjur_session = get_conjur_token(github_jwt)
    print("Handshake successful! Logged in.")
    
    print("\n--- 2. Pulling API Keys from Vault ---")
    # Paths from your synced Safe
    api_key = get_secret("data/vault/DSOWeatherApp/Website-GenericWebApp-10.0.0.1-weatherAPIKey/password", conjur_session)
    city = get_secret("data/vault/DSOWeatherApp/Website-GenericWebApp-UserSelectedCity-WeatherCity/password", conjur_session)
    
    print(f"Target City: {city}")
    
    print("\n--- 3. Weather Report ---")
    weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    w_res = requests.get(weather_url)
    
    if w_res.status_code == 200:
        data = w_res.json()
        print(f"SUCCESS!")
        print(f"Current weather in {data['name']}: {data['main']['temp']}°C, {data['weather'][0]['description']}.")
    else:
        print(f"Weather API error: {w_res.status_code}")
