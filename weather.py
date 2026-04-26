import requests
import os
import sys
import base64

# --- CONFIG ---
CONJUR_URL = "https://nranktest.secretsmgr.cyberark.cloud/api"
AUTHN_ID = "githubWeatherAuthenticator"
ACCOUNT = "conjur"

def get_github_jwt():
    url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
    token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    resp = requests.get(f"{url}&audience=conjur", headers={"Authorization": f"bearer {token}"})
    resp.raise_for_status()
    return resp.json()['value']

def get_conjur_token(jwt):
    jwt = jwt.strip()
    
    # --- UPDATED PATH ---
    # Since you followed the doc, the path is now data/github-apps/
    login_id = "host/data/github-apps/weatherAppFetcher".replace("/", "%2F")
    auth_url = f"{CONJUR_URL}/authn-jwt/{AUTHN_ID}/{ACCOUNT}/{login_id}/authenticate"
    
    print(f"Handshaking for: {login_id}")
    
    try:
        response = requests.post(auth_url, data=f"jwt={jwt}", timeout=10)
        if response.status_code != 200:
            print(f"Auth Failed ({response.status_code}): {response.text}")
            sys.exit(1)
        return base64.b64encode(response.text.encode()).decode()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def get_secret(path, token):
    url = f"{CONJUR_URL}/secrets/{ACCOUNT}/variable/{path.replace('/', '%2F')}"
    resp = requests.get(url, headers={"Authorization": f'Token token="{token}"'})
    return resp.text

if __name__ == "__main__":
    print("--- Secretless Weather App ---")
    jwt = get_github_jwt()
    token = get_conjur_token(jwt)
    
    # These paths stay the same as they are in your Safe
    api_key = get_secret("data/vault/DSOWeatherApp/Website-GenericWebApp-10.0.0.1-weatherAPIKey/password", token)
    city = get_secret("data/vault/DSOWeatherApp/Website-GenericWebApp-UserSelectedCity-WeatherCity/password", token)
    
    w_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    data = requests.get(w_url).json()
    print(f"\nSUCCESS: It is {data['main']['temp']}°C in {data['name']}.")
