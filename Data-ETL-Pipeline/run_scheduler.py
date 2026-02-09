#!/usr/bin/env python3
"""
Football Data ETL Scheduler Runner

Standalone script to run the scheduler for automated data collection.
Can be run as a daemon or service.

Usage:
    # Run in foreground (blocking)
    python run_scheduler.py

    # Run in background
    python run_scheduler.py --daemon

    # Run with custom schedule
    python run_scheduler.py --hour 3 --minute 0

    # Run once immediately then schedule
    python run_scheduler.py --run-now
"""

import os
import sys
import signal
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from scheduler.job_scheduler import JobScheduler, get_scheduler
from scheduler.jobs import (
    fotmob_daily_collection_job,
    fotmob_weekly_deep_job,
    daily_collection_job,
    priority_collection_job,
    update_current_season_job,
)
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scheduler.log')
    ]
)
logger = logging.getLogger(__name__)
console = Console()


def setup_daily_jobs(scheduler: JobScheduler, hour: int = 6, minute: int = 0):
    """
    Configure the standard daily jobs.

    Default schedule (all times in UTC):
    - 05:00 - FotMob daily collection (primary, all 8 leagues, no limit)
    - 06:00 - API-Football daily collection (secondary, 3 leagues, 100/day limit)
    - 12:00 - Priority collection (API-Football standings update)
    - 18:00 - Current season update (API-Football quick refresh)
    - Sunday 02:00 - FotMob weekly deep collection (squads + matches)
    """
    # FotMob daily - runs 1 hour before API-Football (no limit)
    scheduler.add_daily_job(
        job_func=fotmob_daily_collection_job,
        job_id='fotmob_daily',
        hour=max(hour - 1, 0),
        minute=minute,
        kwargs={
            'leagues': None,   # All 8 leagues
            'season': None,    # Current season
        }
    )
    console.print(f"[green]✓[/green] Scheduled fotmob_daily at {max(hour-1,0):02d}:{minute:02d} UTC (all 8 leagues)")

    # FotMob weekly deep - Sunday at 02:00 UTC
    scheduler.add_daily_job(
        job_func=fotmob_weekly_deep_job,
        job_id='fotmob_weekly_deep',
        hour=2,
        minute=0,
        kwargs={
            'season': None,
        }
    )
    console.print("[green]✓[/green] Scheduled fotmob_weekly_deep at 02:00 UTC (Sundays)")

    # API-Football daily collection - runs at specified hour
    scheduler.add_daily_job(
        job_func=daily_collection_job,
        job_id='api_football_daily',
        hour=hour,
        minute=minute,
        kwargs={
            'leagues': ['premier-league', 'la-liga', 'serie-a'],
            'season': 2024,
            'max_requests': 90
        }
    )
    console.print(f"[green]✓[/green] Scheduled api_football_daily at {hour:02d}:{minute:02d} UTC")

    # Priority collection - mid-day standings update
    scheduler.add_daily_job(
        job_func=priority_collection_job,
        job_id='priority_standings',
        hour=12,
        minute=0,
        kwargs={
            'priority_leagues': ['premier-league'],
            'collect_players': False
        }
    )
    console.print("[green]✓[/green] Scheduled priority_standings at 12:00 UTC")

    # Current season quick update - evening refresh
    scheduler.add_daily_job(
        job_func=update_current_season_job,
        job_id='current_season_update',
        hour=18,
        minute=0
    )
    console.print("[green]✓[/green] Scheduled current_season_update at 18:00 UTC")


def display_jobs(scheduler: JobScheduler):
    """Display all scheduled jobs in a table."""
    jobs = scheduler.get_jobs()

    table = Table(title="Scheduled Jobs", show_header=True)
    table.add_column("Job ID", style="cyan")
    table.add_column("Next Run", style="green")
    table.add_column("Trigger", style="yellow")
    table.add_column("Status", style="magenta")

    for job in jobs:
        next_run = job['next_run_time'].strftime('%Y-%m-%d %H:%M:%S') if job['next_run_time'] else 'N/A'
        status = 'Pending' if job['pending'] else 'Active'
        table.add_row(job['id'], next_run, job['trigger'], status)

    console.print(table)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    console.print("\n[yellow]Received shutdown signal. Stopping scheduler...[/yellow]")
    scheduler = get_scheduler()
    scheduler.shutdown(wait=True)
    console.print("[green]Scheduler stopped gracefully.[/green]")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description='Football Data ETL Scheduler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_scheduler.py                    # Run with defaults (6 AM UTC)
  python run_scheduler.py --hour 3           # Run daily at 3 AM UTC
  python run_scheduler.py --run-now          # Run immediately then schedule
  python run_scheduler.py --list-jobs        # List all scheduled jobs
  python run_scheduler.py --daemon           # Run in background mode
        """
    )

    parser.add_argument(
        '--hour',
        type=int,
        default=6,
        help='Hour for daily collection (0-23, default: 6)'
    )
    parser.add_argument(
        '--minute',
        type=int,
        default=0,
        help='Minute for daily collection (0-59, default: 0)'
    )
    parser.add_argument(
        '--run-now',
        action='store_true',
        help='Run collection immediately before starting scheduler'
    )
    parser.add_argument(
        '--list-jobs',
        action='store_true',
        help='List all scheduled jobs and exit'
    )
    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Run in background (daemon) mode'
    )
    parser.add_argument(
        '--timezone',
        default='UTC',
        help='Timezone for scheduling (default: UTC)'
    )

    args = parser.parse_args()

    # Warn about API key (not required - FotMob is primary and needs no key)
    if not os.getenv('API_FOOTBALL_KEY'):
        console.print("[yellow]WARNING: API_FOOTBALL_KEY not set - API-Football jobs will be skipped[/yellow]")
        console.print("FotMob jobs will run normally (no API key needed)\n")

    # Display header
    console.print(Panel.fit(
        "[bold blue]Football Data ETL Scheduler[/bold blue]\n"
        f"Timezone: {args.timezone}",
        border_style="blue"
    ))

    # Create scheduler (blocking mode for standalone operation)
    scheduler = get_scheduler(blocking=not args.daemon)

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Setup jobs
    setup_daily_jobs(scheduler, hour=args.hour, minute=args.minute)

    # Display current jobs
    display_jobs(scheduler)

    # List jobs only
    if args.list_jobs:
        return

    # Run immediately if requested
    if args.run_now:
        console.print("\n[bold cyan]Running immediate FotMob collection...[/bold cyan]")
        try:
            result = fotmob_daily_collection_job(
                leagues=['premier-league'],
                season=None,
            )
            console.print(f"[green]✓[/green] Immediate FotMob collection complete: "
                          f"{len(result.get('leagues_processed', []))} leagues, "
                          f"{result.get('total_teams', 0)} teams")
        except Exception as e:
            console.print(f"[red]✗[/red] Immediate collection failed: {e}")

    # Start scheduler
    console.print(f"\n[bold green]Starting scheduler...[/bold green]")
    console.print("Press Ctrl+C to stop\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        console.print("\n[yellow]Shutting down...[/yellow]")
        scheduler.shutdown()


if __name__ == '__main__':
    main()
