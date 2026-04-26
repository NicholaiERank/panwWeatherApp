import requests
import os
import sys
import base64
import json

# --- CONFIG ---
CONJUR_URL = "https://nranktest.secretsmgr.cyberark.cloud/api"
AUTHN_ID = "githubWeatherAuthenticator"
ACCOUNT = "conjur"

def get_github_jwt():
    url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
    token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    # Audience must match your Authenticator config
    resp = requests.get(f"{url}&audience=conjur", headers={"Authorization": f"bearer {token}"})
    resp.raise_for_status()
    return resp.json()['value']

def get_conjur_token(jwt):
    jwt = jwt.strip()
    login_id = "host/data/weatherAppFetcher".replace("/", "%2F")
    auth_url = f"{CONJUR_URL}/authn-jwt/{AUTHN_ID}/{ACCOUNT}/{login_id}/authenticate"
    
    response = requests.post(auth_url, data=f"jwt={jwt}", timeout=10)
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        sys.exit(1)
    
    # We MUST base64 encode the token for the header
    return base64.b64encode(response.text.encode()).decode()

def get_secret(path, token):
    """Fetches secret and RAISE ERROR if it fails."""
    url = f"{CONJUR_URL}/secrets/{ACCOUNT}/variable/{path.replace('/', '%2F')}"
    headers = {"Authorization": f'Token token="{token}"'}
    
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"ERROR: Could not fetch secret [{path}]")
        print(f"Conjur says: {resp.status_code} - {resp.text}")
        print("FIX: Ensure 'weatherAppFetcher' is a member of the Delegation Group for this safe.")
        sys.exit(1)
    return resp.text

if __name__ == "__main__":
    print("--- 1. Authenticating with Conjur Cloud ---")
    jwt = get_github_jwt()
    token = get_conjur_token(jwt)
    print("Handshake successful!")
    
    print("\n--- 2. Fetching Secrets from Vault ---")
    # Using your exact paths from Screenshot 1
    api_key = get_secret("data/vault/DSOWeatherApp/Website-GenericWebApp-10.0.0.1-weatherAPIKey/password", token)
    city = get_secret("data/vault/DSOWeatherApp/Website-GenericWebApp-UserSelectedCity-WeatherCity/password", token)
    
    print(f"Retrieved target city: {city}")
    
    print("\n--- 3. Weather Report ---")
    weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    res = requests.get(weather_url)
    
    if res.status_code == 200:
        data = res.json()
        print(f"City: {data['name']} | Temp: {data['main']['temp']}°C | Sky: {data['weather'][0]['description']}")
    else:
        print(f"Weather API Error: {res.status_code} - {res.text}")
