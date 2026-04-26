import requests
import os
import sys
import base64
import json

# --- CONJUR CONFIGURATION ---
# Ensure this matches your log: https://nranktest.cyberark.cloud/api
CONJUR_URL = "https://nranktest.cyberark.cloud/api"
AUTHN_ID = "githubWeatherAuthenticator"
ACCOUNT = "conjur"

def get_github_jwt():
    """Fetches the OIDC JWT from the GitHub Runner environment."""
    request_url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
    request_token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    
    if not request_url or not request_token:
        print("Error: GitHub OIDC environment variables not found.")
        print("Make sure 'permissions: id-token: write' is in your YAML.")
        sys.exit(1)
        
    # We add 'audience=conjur' to match the authenticator expectations
    headers = {"Authorization": f"bearer {request_token}"}
    response = requests.get(f"{request_url}&audience=conjur", headers=headers)
    response.raise_for_status()
    return response.json()['value']

def get_conjur_token(jwt):
    """Exchanges the GitHub JWT for a Conjur Session Token."""
    # NO LOGIN ID IN THE URL when token-app-property is used!
    auth_url = f"{CONJUR_URL}/authn-jwt/{AUTHN_ID}/{ACCOUNT}/authenticate"
    
    print(f"Post to: {auth_url}") # Debugging
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "base64"
    }
    
    try:
        # Pass the JWT in the body
        response = requests.post(auth_url, data=f"jwt={jwt}", headers=headers, timeout=10)
        response.raise_for_status()
        # Conjur session tokens must be Base64 encoded for the Authorization header
        return base64.b64encode(response.text.encode()).decode()
    except Exception as e:
        print(f"Failed to authenticate with Conjur: {e}")
        # Print response text if available to see the real error
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
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
    print(f"Fetching weather for {city}...")
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    
    try:
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        print("\n--- WEATHER REPORT (VIA CONJUR CLOUD) ---")
        print(f"City: {data['name']}")
        print(f"Temp: {data['main']['temp']}°C")
        print(f"Sky:  {data['weather'][0]['description'].capitalize()}")
        print("------------------------------------------\n")
    except Exception as e:
        print(f"OpenWeather API Error: {e}")

if __name__ == "__main__":
    print("--- Starting Secretless Weather App ---")
    
    # 1. Get JWT from GitHub
    jwt = get_github_jwt()
    
    # 2. Exchange for Conjur Token
    token = get_conjur_token(jwt)
    
    # 3. Use your exact paths from Screenshot 1
    key_path = "data/vault/DSOWeatherApp/Website-GenericWebApp-10.0.0.1-weatherAPIKey/password"
    city_path = "data/vault/DSOWeatherApp/Website-GenericWebApp-UserSelectedCity-WeatherCity/password"
    
    api_key = get_secret(key_path, token)
    target_city = get_secret(city_path, token)
    
    # 4. Success!
    fetch_weather(target_city, api_key)
