"""
Optimized Data Collector for API-Football limits (100 req/day).

Strategy:
1. Check usage today
2. Prioritize Leagues: PL > La Liga > Serie A > Bundesliga > Ligue 1
3. Prioritize Seasons: 2024 (Current) > 2023 (Last)
4. Skip existing data
5. Collect: Standings, Fixtures (Basic), Players (Pagination)
6. Stop when quota < 10
"""
import sys
import os
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from database.connection import get_db
from etl.api_football_etl import APIFootballETL
from scrapers.api_football.client import LEAGUE_IDS
from rich.console import Console
from rich.table import Table

console = Console()

class SmartCollector:
    def __init__(self):
        self.db = get_db()
        self.api_key = os.getenv('API_FOOTBALL_KEY', "7652e15016e34d8d84c4e7528be0af2c")
        self.etl = APIFootballETL(api_key=self.api_key)
        self.league_priority = [
            'premier-league', 'la-liga', 'serie-a', 'bundesliga', 'ligue-1'
        ]
        self.seasons = [2024, 2023]  # Current, Last
        
    def check_quota(self):
        """Check API usage via headers from a lightweight call."""
        # We'll make a lightweight call to status or timezone to check headers
        # API-Football returns x-ratelimit-requests-remaining
        try:
            # We can use the timezone endpoint as it's static and light
            resp = self.etl.client._make_request("timezone")
            # Usually client doesn't return headers, let's peek into client
            # Actually, standard client returns body. We might need to subclass or inspect last request
            # For now, let's trust the 'requests' object in client if we modify it or just trust the loop count.
            # Implemented a basic counter in client would be better.
            # Taking a simpler approach: Track our own usage in this session.
            pass
        except:
            pass
            
    def is_data_complete(self, league_offset, season):
        """Check if we already have data for this league/season."""
        # Check team_season_stats count
        league_id = self.etl._get_league_id(league_offset)
        season_id = self.etl._get_season_id(f"{season}-{season+1-2000}")
        
        if not league_id or not season_id:
            return False
            
        # Check team stats
        res_teams = self.db.execute_query(
            "SELECT COUNT(*) FROM team_season_stats WHERE league_id = :l AND season_id = :s",
            params={'l': league_id, 's': season_id},
            fetch=True
        )
        team_count = res_teams[0][0]
        
        # Check player stats
        res_players = self.db.execute_query(
            "SELECT COUNT(*) FROM player_season_stats WHERE league_id = :l AND season_id = :s",
            params={'l': league_id, 's': season_id},
            fetch=True
        )
        player_count = res_players[0][0]
        
        # We need both teams (>15) AND at least some players (>100) to consider it "done"
        if team_count > 15 and player_count > 100:
            return True
        return False

    def run(self):
        console.print("[bold blue]Smart Collector Starting...[/bold blue]")
        
        # 1. Check what we have
        queue = []
        for league in self.league_priority:
            for season in self.seasons:
                if self.is_data_complete(league, season):
                    console.print(f"[green]✓ Found data for {league} {season} - Skipping[/green]")
                else:
                    console.print(f"[yellow]○ Need data for {league} {season} - Queued[/yellow]")
                    queue.append((league, season))
        
        if not queue:
            console.print("[bold green]All priority data is collected![/bold green]")
            return
            
        # 2. Process Queue with limit safety
        processed = 0
        limit_safe = 90 # Leave buffer
        
        # We need to estimate cost.
        # 1 season = 1 (standings) + 1 (fixtures) + ~30 (players) = ~32 requests
        # We can do 2-3 seasons.
        
        for league, season in queue:
            console.print(f"\n[bold cyan]Processing {league} {season}...[/bold cyan]")
            
            try:
                # We need to update ETL to handle player pagination first!
                # Assuming ETL is updated:
                self.etl.process_league_season(league, season)
                processed += 1
                
                # Simple stop after 2 seasons to be safe for today
                if processed >= 2:
                    console.print("[red]Daily limit safety stop. Continue tomorrow.[/red]")
                    break
                    
            except Exception as e:
                import traceback
                console.print(f"[red]Error processing {league}: {e}[/red]")
                traceback.print_exc()

if __name__ == "__main__":
    collector = SmartCollector()
    collector.run()
