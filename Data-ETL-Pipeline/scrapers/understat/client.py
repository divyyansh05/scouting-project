"""
Understat Client

Scrapes advanced xG metrics from understat.com:
- xG (expected goals)
- xA (expected assists)
- npxG (non-penalty xG)
- xGChain (xG from possessions involved in)
- xGBuildup (xGChain excluding shots/key passes)

Note: This is web scraping and should be used responsibly with rate limiting.
"""

import logging
import time
import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# Understat league name mappings
LEAGUE_MAPPINGS = {
    'premier-league': 'EPL',
    'la-liga': 'La_liga',
    'serie-a': 'Serie_A',
    'bundesliga': 'Bundesliga',
    'ligue-1': 'Ligue_1',
    'rfpl': 'RFPL',  # Russian Premier League
}

# Reverse mapping
UNDERSTAT_TO_LEAGUE = {v: k for k, v in LEAGUE_MAPPINGS.items()}


class UnderstatClient:
    """
    Client for scraping Understat.com

    Provides access to advanced xG metrics not available from other sources:
    - xA (Expected Assists)
    - npxG (Non-penalty xG)
    - xGChain
    - xGBuildup
    """

    BASE_URL = "https://understat.com"

    def __init__(self, rate_limit_delay: float = 2.0):
        """
        Initialize Understat client.

        Args:
            rate_limit_delay: Seconds to wait between requests (default 2s)
        """
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://understat.com/',
        })

        # Statistics
        self.total_requests = 0
        self.failed_requests = 0

    def _rate_limit(self):
        """Enforce rate limiting."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _get_page(self, url: str) -> Optional[str]:
        """
        Fetch a page with rate limiting and error handling.

        Returns HTML content or None on failure.
        """
        self._rate_limit()
        self.total_requests += 1

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            self.failed_requests += 1
            return None

    def _extract_json_var(self, html: str, var_name: str) -> Optional[Any]:
        """
        Extract JSON data from JavaScript variable in page.

        Understat embeds data in script tags like:
        var playersData = JSON.parse('...');
        """
        pattern = rf"var {var_name}\s*=\s*JSON\.parse\('(.+?)'\)"
        match = re.search(pattern, html)

        if not match:
            # Try alternative pattern
            pattern = rf'{var_name}\s*=\s*JSON\.parse\("(.+?)"\)'
            match = re.search(pattern, html)

        if match:
            try:
                # Decode escaped characters
                json_str = match.group(1)
                json_str = json_str.encode().decode('unicode_escape')
                return json.loads(json_str)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(f"Failed to parse JSON for {var_name}: {e}")
                return None

        return None

    def get_league_players(self, league: str, season: int) -> List[Dict]:
        """
        Get all players with xG stats for a league/season.

        Args:
            league: League key (e.g., 'premier-league', 'la-liga')
            season: Season start year (e.g., 2024 for 2024/25)

        Returns:
            List of player dicts with xG, xA, npxG, etc.
        """
        understat_league = LEAGUE_MAPPINGS.get(league)
        if not understat_league:
            logger.error(f"Unknown league: {league}")
            return []

        url = f"{self.BASE_URL}/league/{understat_league}/{season}"
        logger.info(f"Fetching league players: {url}")

        html = self._get_page(url)
        if not html:
            return []

        players_data = self._extract_json_var(html, 'playersData')
        if not players_data:
            logger.warning(f"No player data found for {league} {season}")
            return []

        players = []
        for player in players_data:
            players.append({
                'understat_id': int(player.get('id', 0)),
                'name': player.get('player_name', ''),
                'team': player.get('team_title', ''),
                'position': player.get('position', ''),
                'games': int(player.get('games', 0)),
                'minutes': int(player.get('time', 0)),
                'goals': int(player.get('goals', 0)),
                'assists': int(player.get('assists', 0)),
                'shots': int(player.get('shots', 0)),
                'key_passes': int(player.get('key_passes', 0)),
                'xg': float(player.get('xG', 0)),
                'xa': float(player.get('xA', 0)),
                'npxg': float(player.get('npxG', 0)),
                'xg_chain': float(player.get('xGChain', 0)),
                'xg_buildup': float(player.get('xGBuildup', 0)),
                'npg': int(player.get('npg', 0)),  # Non-penalty goals
                'yellow_cards': int(player.get('yellow_cards', 0)),
                'red_cards': int(player.get('red_cards', 0)),
            })

        logger.info(f"Found {len(players)} players for {league} {season}")
        return players

    def get_league_teams(self, league: str, season: int) -> List[Dict]:
        """
        Get all teams with xG stats for a league/season.

        Args:
            league: League key (e.g., 'premier-league')
            season: Season start year

        Returns:
            List of team dicts with xG, xGA, npxG, etc.
        """
        understat_league = LEAGUE_MAPPINGS.get(league)
        if not understat_league:
            logger.error(f"Unknown league: {league}")
            return []

        url = f"{self.BASE_URL}/league/{understat_league}/{season}"
        logger.info(f"Fetching league teams: {url}")

        html = self._get_page(url)
        if not html:
            return []

        teams_data = self._extract_json_var(html, 'teamsData')
        if not teams_data:
            logger.warning(f"No team data found for {league} {season}")
            return []

        teams = []
        for team_id, team in teams_data.items():
            # Team data has 'history' array with per-match data
            history = team.get('history', [])

            # Aggregate stats
            total_xg = sum(float(m.get('xG', 0)) for m in history)
            total_xga = sum(float(m.get('xGA', 0)) for m in history)
            total_npxg = sum(float(m.get('npxG', 0)) for m in history)
            total_npxga = sum(float(m.get('npxGA', 0)) for m in history)
            total_scored = sum(int(m.get('scored', 0)) for m in history)
            total_missed = sum(int(m.get('missed', 0)) for m in history)  # Conceded
            ppda = sum(float(m.get('ppda', {}).get('att', 0)) for m in history)
            ppda_def = sum(float(m.get('ppda', {}).get('def', 0)) for m in history)
            deep = sum(int(m.get('deep', 0)) for m in history)
            deep_allowed = sum(int(m.get('deep_allowed', 0)) for m in history)

            teams.append({
                'understat_id': int(team_id),
                'name': team.get('title', ''),
                'matches': len(history),
                'goals_for': total_scored,
                'goals_against': total_missed,
                'xg': round(total_xg, 2),
                'xga': round(total_xga, 2),
                'npxg': round(total_npxg, 2),
                'npxga': round(total_npxga, 2),
                'xg_diff': round(total_xg - total_xga, 2),
                'npxg_diff': round(total_npxg - total_npxga, 2),
                'ppda_att': ppda,
                'ppda_def': ppda_def,
                'ppda': round(ppda / ppda_def, 2) if ppda_def > 0 else 0,
                'deep': deep,  # Passes within 20m of goal
                'deep_allowed': deep_allowed,
            })

        logger.info(f"Found {len(teams)} teams for {league} {season}")
        return teams

    def get_player_details(self, player_id: int) -> Optional[Dict]:
        """
        Get detailed stats for a specific player.

        Args:
            player_id: Understat player ID

        Returns:
            Dict with player info, season stats, and match history
        """
        url = f"{self.BASE_URL}/player/{player_id}"
        logger.info(f"Fetching player details: {url}")

        html = self._get_page(url)
        if not html:
            return None

        # Extract different data types
        groups_data = self._extract_json_var(html, 'groupsData')
        matches_data = self._extract_json_var(html, 'matchesData')
        shots_data = self._extract_json_var(html, 'shotsData')

        # Parse player name from page title
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.find('title')
        player_name = title.text.split('|')[0].strip() if title else 'Unknown'

        return {
            'understat_id': player_id,
            'name': player_name,
            'seasons': groups_data or {},
            'matches': matches_data or [],
            'shots': shots_data or [],
        }

    def get_player_matches(self, player_id: int) -> List[Dict]:
        """
        Get per-match stats for a player.

        Args:
            player_id: Understat player ID

        Returns:
            List of match dicts with xG, xA per match
        """
        details = self.get_player_details(player_id)
        if not details:
            return []

        matches = []
        for match in details.get('matches', []):
            matches.append({
                'understat_match_id': int(match.get('id', 0)),
                'date': match.get('date'),
                'home_team': match.get('h_team'),
                'away_team': match.get('a_team'),
                'home_goals': int(match.get('h_goals', 0)),
                'away_goals': int(match.get('a_goals', 0)),
                'goals': int(match.get('goals', 0)),
                'assists': int(match.get('assists', 0)),
                'shots': int(match.get('shots', 0)),
                'key_passes': int(match.get('key_passes', 0)),
                'minutes': int(match.get('time', 0)),
                'xg': float(match.get('xG', 0)),
                'xa': float(match.get('xA', 0)),
                'npxg': float(match.get('npxG', 0)),
                'xg_chain': float(match.get('xGChain', 0)),
                'xg_buildup': float(match.get('xGBuildup', 0)),
                'position': match.get('position'),
            })

        return matches

    def get_match_details(self, match_id: int) -> Optional[Dict]:
        """
        Get detailed stats for a specific match.

        Args:
            match_id: Understat match ID

        Returns:
            Dict with shots data and player performances
        """
        url = f"{self.BASE_URL}/match/{match_id}"
        logger.info(f"Fetching match details: {url}")

        html = self._get_page(url)
        if not html:
            return None

        # Extract data
        shots_data = self._extract_json_var(html, 'shotsData')
        roster_data = self._extract_json_var(html, 'rostersData')
        match_info = self._extract_json_var(html, 'match_info')

        return {
            'understat_match_id': match_id,
            'info': match_info or {},
            'shots': shots_data or {},
            'rosters': roster_data or {},
        }

    def get_team_matches(self, team_id: int, season: int) -> List[Dict]:
        """
        Get all matches for a team in a season.

        Args:
            team_id: Understat team ID
            season: Season start year

        Returns:
            List of match dicts with xG data
        """
        url = f"{self.BASE_URL}/team/{team_id}/{season}"
        logger.info(f"Fetching team matches: {url}")

        html = self._get_page(url)
        if not html:
            return []

        dates_data = self._extract_json_var(html, 'datesData')
        if not dates_data:
            return []

        matches = []
        for match in dates_data:
            is_home = match.get('side') == 'h'
            matches.append({
                'understat_match_id': int(match.get('id', 0)),
                'date': match.get('datetime'),
                'is_home': is_home,
                'opponent': match.get('title'),
                'result': match.get('result'),
                'goals_for': int(match.get('scored', 0)),
                'goals_against': int(match.get('missed', 0)),
                'xg': float(match.get('xG', 0)),
                'xga': float(match.get('xGA', 0)),
                'npxg': float(match.get('npxG', 0)),
                'npxga': float(match.get('npxGA', 0)),
                'ppda_att': float(match.get('ppda', {}).get('att', 0)),
                'ppda_def': float(match.get('ppda', {}).get('def', 0)),
                'deep': int(match.get('deep', 0)),
                'deep_allowed': int(match.get('deep_allowed', 0)),
            })

        return matches

    def get_available_seasons(self, league: str) -> List[int]:
        """
        Get available seasons for a league.

        Returns list of season start years (e.g., [2014, 2015, ..., 2024])
        """
        understat_league = LEAGUE_MAPPINGS.get(league)
        if not understat_league:
            return []

        # Understat has data from 2014/15 season onwards
        # Get current page and extract available seasons
        url = f"{self.BASE_URL}/league/{understat_league}"
        html = self._get_page(url)

        if not html:
            # Return default range
            return list(range(2014, datetime.now().year + 1))

        # Parse available seasons from dropdown
        soup = BeautifulSoup(html, 'html.parser')
        seasons = []

        # Look for season selector
        select = soup.find('select', {'name': 'season'})
        if select:
            for option in select.find_all('option'):
                try:
                    seasons.append(int(option.get('value', 0)))
                except ValueError:
                    pass

        return sorted(seasons) if seasons else list(range(2014, datetime.now().year + 1))

    def get_statistics(self) -> Dict:
        """Return client statistics."""
        return {
            'total_requests': self.total_requests,
            'failed_requests': self.failed_requests,
            'success_rate': (self.total_requests - self.failed_requests) / max(self.total_requests, 1) * 100
        }
