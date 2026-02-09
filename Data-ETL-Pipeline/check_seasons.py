"""
Check available seasons for Premier League.
"""
import requests
import json
import os

API_KEY = "7652e15016e34d8d84c4e7528be0af2c"
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY,
}

def check_seasons():
    # ID 39 is Premier League
    url = f"{BASE_URL}/leagues?id=39"
    try:
        response = requests.get(url, headers=HEADERS)
        data = response.json()
        
        if data['results'] > 0:
            league = data['response'][0]
            seasons = league['seasons']
            print(f"League: {league['league']['name']}")
            print(f"Country: {league['country']['name']}")
            print(f"Available Seasons: {len(seasons)}")
            print(f"First Season: {seasons[0]['year']}")
            print(f"Last Season: {seasons[-1]['year']}")
            print(f"Current Season: {[s['year'] for s in seasons if s['current']][0]}")
            
            # Check reliability of recent season
            latest = seasons[-1]
            print("\nLatest Season Coverage:")
            print(f"Year: {latest['year']}")
            print(f"Events: {latest['coverage']['fixtures']['events']}")
            print(f"Lineups: {latest['coverage']['fixtures']['lineups']}")
            print(f"Statistics: {latest['coverage']['fixtures']['statistics_fixtures']}")
            print(f"Player Stats: {latest['coverage']['fixtures']['statistics_players']}")
        else:
            print("No data found.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_seasons()
