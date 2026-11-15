import requests
import os
import sys
import base64
from urllib.parse import quote

# --- CONFIG ---
CONJUR_URL = os.environ.get("CONJUR_URL", "https://anzmislab.secretsmgr.cyberark.cloud/api")
AUTHN_ID = os.environ.get("CONJUR_AUTHN_ID", "githubWeatherAuthenticator")
ACCOUNT = "conjur"

def get_github_jwt():
    url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
    token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")

    resp = requests.get(f"{url}&audience=conjur", headers={"Authorization": f"bearer {token}"})
    resp.raise_for_status()
    return resp.json()['value']

def get_conjur_token(jwt):
    jwt = jwt.strip()
    auth_url = f"{CONJUR_URL}/authn-jwt/{AUTHN_ID}/{ACCOUNT}/authenticate"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
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
    encoded_path = quote(path, safe="")
    url = f"{CONJUR_URL}/secrets/{ACCOUNT}/variable/{encoded_path}"
    resp = requests.get(url, headers={"Authorization": f'Token token="{token}"'})
    if resp.status_code != 200:
        print(f"Secret Error [{path}]: {resp.status_code} - {resp.text}")
        sys.exit(1)
    return resp.text

if __name__ == "__main__":
    print("--- Starting Official Secretless Handshake ---")

    github_jwt = get_github_jwt()
    conjur_session = get_conjur_token(github_jwt)

    print("Login successful! Accessing vault...")

    # Updated Secret Paths
    api_key_path = "data/vault/DSOWeatherApp/Cloud Service-WebApplication-10.0.0.1-weatherAPIKey/password"
    city_path = "data/vault/DSOWeatherApp/Cloud Service-WebApplication-UserSelectedCity-WeatherCity/password"

    api_key = get_secret(api_key_path, conjur_session)
    city = get_secret(city_path, conjur_session)

    print(f"\n--- SUCCESS: Weather for {city} ---")
    weather_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    resp = requests.get(weather_url)
    data = resp.json()

    if resp.status_code != 200:
        print(f"OpenWeather Error ({resp.status_code}): {data}")
        sys.exit(1)

    print(f"Temperature: {data['main']['temp']}°C | Sky: {data['weather'][0]['description']}")
