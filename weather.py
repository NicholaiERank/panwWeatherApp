import requests
import os
import sys
import base64

# --- CONFIG ---
CONJUR_URL = "https://anzmislab.secretsmgr.cyberark.cloud/api"
AUTHN_ID = "githubWeatherAuthenticator"
ACCOUNT = "conjur"

def get_github_jwt():
    url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
    token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    
    # CRITICAL: This must match the 'Audience' field in your Authenticator GUI
    # If you left Audience blank in the GUI, remove '&audience=conjur'
    resp = requests.get(f"{url}&audience=conjur", headers={"Authorization": f"bearer {token}"})
    resp.raise_for_status()
    return resp.json()['value']

def get_conjur_token(jwt):
    jwt = jwt.strip()
    
    # THE OFFICIAL URL: No host ID allowed in the path when using mapping
    auth_url = f"{CONJUR_URL}/authn-jwt/{AUTHN_ID}/{ACCOUNT}/authenticate"
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        # We send the JWT in the body
        response = requests.post(auth_url, data=f"jwt={jwt}", headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"Auth Failed ({response.status_code})")
            print(f"Bouncer Response: {response.text}")
            sys.exit(1)
            
        return base64.b64encode(response.text.encode()).decode()
    except Exception as e:
        print(f"Connection Error: {e}")
        sys.exit(1)

def get_secret(path, token):
    url = f"{CONJUR_URL}/secrets/{ACCOUNT}/variable/{path.replace('/', '%2F')}"
    resp = requests.get(url, headers={"Authorization": f'Token token="{token}"'})
    if resp.status_code != 200:
        print(f"Secret Error [{path}]: {resp.status_code}")
        sys.exit(1)
    return resp.text

if __name__ == "__main__":
    print("--- Starting Official Secretless Handshake ---")
    
    github_jwt = get_github_jwt()
    conjur_session = get_conjur_token(github_jwt)
    
    print("Login successful! Accessing vault...")

    # Secret Paths
    api_key_path = "data/vault/DSOWeatherApp/Website-GenericWebApp-10.0.0.1-weatherAPIKey/password"
    city_path = "data/vault/DSOWeatherApp/Website-GenericWebApp-UserSelectedCity-WeatherCity/password"
    
    api_key = get_secret(api_key_path, conjur_session)
    city = get_secret(city_path, conjur_session)
    
    print(f"\n--- SUCCESS: Weather for {city} ---")
    weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    data = requests.get(weather_url).json()
    print(f"Temperature: {data['main']['temp']}°C | Sky: {data['weather'][0]['description']}")
