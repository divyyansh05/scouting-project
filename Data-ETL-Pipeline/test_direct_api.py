"""
Test API Key against Direct API-Football Endpoint.
"""
import requests
import json

API_KEY = "7652e15016e34d8d84c4e7528be0af2c"
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY,
}

def test_connection():
    url = f"{BASE_URL}/status"
    try:
        print(f"Testing connection to {url}...")
        response = requests.get(url, headers=HEADERS)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("\nSUCCESS! Key works with Direct API.")
            return True
        else:
            print("\nFAILED with Direct API.")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_connection()
