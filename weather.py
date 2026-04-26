import requests
import os
import sys
import base64
import json

# --- CONFIG ---
CONJUR_URL = "https://nranktest.secretsmgr.cyberark.cloud/api"
AUTHN_ID = "githubWeatherAuthenticator"
ACCOUNT = "conjur"

def debug_jwt(jwt):
    """Decodes and prints the JWT claims so we can see the 'Passport' details."""
    try:
        payload = jwt.split('.')[1]
        payload += '=' * (4 - len(payload) % 4) # Fix padding
        decoded = json.loads(base64.b64decode(payload).decode('utf-8'))
        print("\n--- DEBUG: GITHUB JWT CLAIMS ---")
        for key, value in decoded.items():
            print(f"{key}: {value}")
        print("--------------------------------\n")
        return decoded
    except:
        print("Could not decode JWT for debugging.")

def get_github_jwt():
    url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
    token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    resp = requests.get(f"{url}&audience=conjur", headers={"Authorization": f"bearer {token}"})
    resp.raise_for_status()
    return resp.json()['value']

def get_conjur_token(jwt):
    jwt = jwt.strip()
    debug_jwt(jwt) # Print the claims to the log!
    
    # CLEAN URL - Let Conjur find the host via token-app-property
    auth_url = f"{CONJUR_URL}/authn-jwt/{AUTHN_ID}/{ACCOUNT}/authenticate"
    
    try:
        # Standard POST with the JWT in the body
        response = requests.post(auth_url, data=f"jwt={jwt}", timeout=10)
        
        if response.status_code == 401:
            print(f"401 ERROR: Bouncer says: {response.text}")
            print("Check if 'workflow' in the DEBUG list above matches your Workload ID exactly.")
            sys.exit(1)
            
        response.raise_for_status()
        return base64.b64encode(response.text.encode()).decode()
    except Exception as e:
        print(f"Auth Failed: {e}")
        sys.exit(1)

# ... (Rest of your get_secret and main functions remain the same)
