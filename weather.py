import requests
import os
import sys
import base64
import json

# --- CONFIG ---
CONJUR_URL = "https://nranktest.secretsmgr.cyberark.cloud/api"
AUTHN_ID = "githubWeatherAuthenticator"
ACCOUNT = "conjur"

def decode_and_print_jwt(jwt):
    """Decodes the JWT payload to see what GitHub is actually sending."""
    try:
        # JWTs are [Header].[Payload].[Signature]
        parts = jwt.split('.')
        if len(parts) != 3:
            print("Invalid JWT format.")
            return
        
        payload = parts[1]
        # Fix base64 padding
        payload += '=' * (4 - len(payload) % 4)
        decoded = json.loads(base64.b64decode(payload).decode('utf-8'))
        
        print("\n" + "="*50)
        print("--- DEBUG: GITHUB JWT CLAIMS (The Passport) ---")
        print("="*50)
        # We care most about these three:
        print(f"ISS (Issuer):   {decoded.get('iss')}")
        print(f"AUD (Audience): {decoded.get('aud')}")
        print(f"WORKFLOW:       {decoded.get('workflow')}")
        print(f"REPO:           {decoded.get('repository')}")
        print("="*50 + "\n")
        return decoded
    except Exception as e:
        print(f"Could not decode JWT for debugging: {e}")

def get_github_jwt():
    url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
    token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    # Requesting 'conjur' as the audience
    headers = {"Authorization": f"bearer {token}"}
    resp = requests.get(f"{url}&audience=conjur", headers=headers)
    resp.raise_for_status()
    return resp.json()['value']

def get_conjur_token(jwt):
    jwt = jwt.strip()
    decode_and_print_jwt(jwt) # Show us the claims in the log!
    
    # We are using the "Direct Login" URL to remove any mapping ambiguity
    # This tells Conjur: "I am host/data/weatherAppFetcher, check my JWT."
    login_id = "host/data/weatherAppFetcher".replace("/", "%2F")
    auth_url = f"{CONJUR_URL}/authn-jwt/{AUTHN_ID}/{ACCOUNT}/{login_id}/authenticate"
    
    print(f"Attempting login to: {auth_url}")
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        response = requests.post(auth_url, data=f"jwt={jwt}", headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"--- AUTHENTICATION REJECTED ---")
            print(f"Status: {response.status_code}")
            print(f"Error:  {response.text if response.text else '[Empty Body - Check Issuer/Audience Mapping]'}")
            sys.exit(1)
            
        return base64.b64encode(response.text.encode()).decode()
    except Exception as e:
        print(f"Request failed: {e}")
        sys.exit(1)

def get_secret(path, token):
    url = f"{CONJUR_URL}/secrets/{ACCOUNT}/variable/{path.replace('/', '%2F')}"
    headers = {"Authorization": f'Token token="{token}"'}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"Secret Error: {resp.status_code} - {resp.text}")
        sys.exit(1)
    return resp.text

if __name__ == "__main__":
    print("--- Starting Secretless App ---")
    jwt = get_github_jwt()
    conjur_token = get_conjur_token(jwt)
    
    print("Handshake Success! Fetching secrets...")
    api_key = get_secret("data/vault/DSOWeatherApp/Website-GenericWebApp-10.0.0.1-weatherAPIKey/password", conjur_token)
    city = get_secret("data/vault/DSOWeatherApp/Website-GenericWebApp-UserSelectedCity-WeatherCity/password", conjur_token)
    
    print(f"\n--- Weather for {city} ---")
    w_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    data = requests.get(w_url).json()
    print(f"Temp: {data['main']['temp']}°C | Sky: {data['weather'][0]['description']}")
