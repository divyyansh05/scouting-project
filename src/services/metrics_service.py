"""
Metrics Service - services/metrics_service.py

RESPONSIBILITIES:
-----------------
Compute derived football metrics from raw SQL data.
All computations are deterministic Python functions.

CRITICAL RULES:
--------------
- NO SCRAPING - Only use data from database
- NO SQL WRITES - Read-only operations via utils/db.py
- NO LLM USAGE - All metrics computed with explicit formulas
- ALL FORMULAS DOCUMENTED - Every metric has clear docstring

INPUT:
------
- Raw player match statistics from database
- Minutes played
- Event counts (goals, passes, tackles, etc.)

OUTPUT:
-------
- Per 90 metrics (goals per 90, passes per 90, etc.)
- Season aggregates (total goals, total minutes, etc.)
- Percentile rankings within cohorts
- Age-adjusted metrics (optional)

ARCHITECTURE:
------------
    Raw SQL Data (via db.py)
        |
    Validate metrics (via validation.py)
        |
    Compute metrics (pure Python functions)
        |
    Return structured results (dicts/DataFrames)
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Union
from datetime import datetime

# Import our layers
from utils.db import fetch_dataframe, fetch_single_value
from utils.validation import (
    validate_requested_metrics,
    get_metric_metadata,
    get_minimum_minutes_required,
    is_higher_better
)

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

# Default minimum minutes for meaningful analysis
DEFAULT_MIN_MINUTES = 450  # ~5 full matches

# Minutes per full match
MINUTES_PER_MATCH = 90


# ============================================================================
# DATA FETCHING FUNCTIONS
# ============================================================================

def fetch_player_match_stats(
    player_id: int,
    season: Optional[str] = None,
    competition: Optional[str] = None
) -> pd.DataFrame:
    """
    Fetch raw match statistics for a player.

    This is the PRIMARY DATA SOURCE for all metric computations.

    Args:
        player_id: Player identifier
        season: Optional season filter (e.g., "2023-24")
        competition: Optional competition filter (e.g., "Premier League")

    Returns:
        DataFrame with columns:
        - match_id, match_date, competition
        - minutes_played
        - goals, assists, shots, shots_on_target
        - passes_attempted, passes_completed
        - tackles, interceptions, blocks
        - carries, dribbles_attempted, dribbles_completed
        - fouls_committed, fouls_drawn, yellow_cards, red_cards
        - aerial_duels_attempted, aerial_duels_won
        - etc.

    Example:
        >>> df = fetch_player_match_stats(player_id=123, season="2023-24")
        >>> print(df.columns)
        ['match_id', 'minutes_played', 'goals', 'assists', ...]
    """
    query = """
        SELECT
            ps.match_id,
            m.match_date,
            m.competition,
            m.season,
            ps.minutes_played,

            -- Shooting
            ps.goals,
            ps.assists,
            ps.shots,
            ps.shots_on_target,
            ps.xg,
            ps.xag,

            -- Passing
            ps.passes_attempted,
            ps.passes_completed,
            ps.progressive_passes,
            ps.key_passes,
            ps.passes_into_final_third,
            ps.passes_into_penalty_area,
            ps.crosses,
            ps.crosses_completed,

            -- Defending
            ps.tackles,
            ps.tackles_won,
            ps.interceptions,
            ps.blocks,
            ps.clearances,
            ps.aerial_duels_attempted,
            ps.aerial_duels_won,
            ps.dribbled_past,

            -- Possession
            ps.touches,
            ps.carries,
            ps.progressive_carries,
            ps.dribbles_attempted,
            ps.dribbles_completed,
            ps.dispossessed,
            ps.miscontrols,

            -- Discipline
            ps.fouls_committed,
            ps.fouls_drawn,
            ps.yellow_cards,
            ps.red_cards

        FROM player_match_stats ps
        JOIN matches m ON ps.match_id = m.match_id
        WHERE ps.player_id = %s
    """

    params = [player_id]

    if season:
        query += " AND m.season = %s"
        params.append(season)

    if competition:
        query += " AND m.competition = %s"
        params.append(competition)

    query += " ORDER BY m.match_date"

    df = fetch_dataframe(query, params=tuple(params), parse_dates=['match_date'])

    logger.info(
        f"Fetched {len(df)} matches for player {player_id}"
        + (f" in season {season}" if season else "")
        + (f" in {competition}" if competition else "")
    )

    return df


def fetch_player_info(player_id: int) -> Dict:
    """
    Fetch basic player information.

    Args:
        player_id: Player identifier

    Returns:
        Dict with player information (name, position, age, etc.)
    """
    query = """
        SELECT
            player_id,
            name,
            position,
            age,
            date_of_birth,
            current_team
        FROM players
        WHERE player_id = %s
    """

    df = fetch_dataframe(query, params=(player_id,))

    if df.empty:
        raise ValueError(f"Player {player_id} not found in database")

    return df.iloc[0].to_dict()


# ============================================================================
# CORE METRIC COMPUTATION FUNCTIONS
# ============================================================================

def compute_per90(
    total_value: float,
    total_minutes: float,
    per_minutes: int = 90
) -> float:
    """
    Convert counting statistic to per-90-minutes rate.

    FORMULA: (total_value / total_minutes) * per_minutes

    Args:
        total_value: Sum of raw statistic (e.g., total goals)
        total_minutes: Total minutes played
        per_minutes: Convert to per N minutes (default: 90)

    Returns:
        Rate per specified minutes

    Example:
        >>> compute_per90(total_value=15, total_minutes=1800)
        0.75  # 15 goals in 1800 minutes = 0.75 goals per 90

    Edge Cases:
        >>> compute_per90(10, 0)
        0.0  # Zero minutes = zero rate
    """
    if total_minutes <= 0:
        return 0.0

    return (total_value / total_minutes) * per_minutes


def compute_percentage(
    successes: float,
    attempts: float
) -> float:
    """
    Compute percentage from successes and attempts.

    FORMULA: (successes / attempts) * 100

    Args:
        successes: Number of successful events
        attempts: Number of total attempts

    Returns:
        Percentage (0-100)

    Example:
        >>> compute_percentage(successes=70, attempts=100)
        70.0  # 70% success rate

    Edge Cases:
        >>> compute_percentage(10, 0)
        0.0  # Zero attempts = 0%
    """
    if attempts <= 0:
        return 0.0

    return (successes / attempts) * 100


def compute_ratio(
    numerator: float,
    denominator: float
) -> float:
    """
    Compute simple ratio.

    FORMULA: numerator / denominator

    Args:
        numerator: Top of ratio
        denominator: Bottom of ratio

    Returns:
        Ratio value

    Example:
        >>> compute_ratio(15, 10)
        1.5
    """
    if denominator <= 0:
        return 0.0

    return numerator / denominator


# ============================================================================
# AGGREGATE COMPUTATION FUNCTIONS
# ============================================================================

def compute_basic_aggregates(df: pd.DataFrame) -> Dict:
    """
    Compute basic aggregate statistics from match data.

    Args:
        df: DataFrame with match-level statistics

    Returns:
        Dict with aggregate totals:
        - total_minutes: Sum of minutes played
        - matches_played: Count of matches
        - total_[stat]: Sum of each counting stat

    Example:
        >>> df = fetch_player_match_stats(player_id=123)
        >>> agg = compute_basic_aggregates(df)
        >>> print(agg['total_goals'])
        15
    """
    if df.empty:
        return {}

    # Counting stats to aggregate
    counting_stats = [
        'goals', 'assists', 'shots', 'shots_on_target',
        'passes_attempted', 'passes_completed',
        'progressive_passes', 'key_passes',
        'tackles', 'tackles_won', 'interceptions', 'blocks',
        'clearances', 'aerial_duels_attempted', 'aerial_duels_won',
        'touches', 'carries', 'progressive_carries',
        'dribbles_attempted', 'dribbles_completed',
        'fouls_committed', 'fouls_drawn',
        'yellow_cards', 'red_cards',
        'xg', 'xag'
    ]

    aggregates = {
        'total_minutes': df['minutes_played'].sum(),
        'matches_played': len(df),
        'matches_started': (df['minutes_played'] >= 45).sum(),  # Heuristic
    }

    # Sum all counting stats
    for stat in counting_stats:
        if stat in df.columns:
            aggregates[f'total_{stat}'] = df[stat].sum()

    return aggregates


def compute_all_per90_metrics(aggregates: Dict) -> Dict:
    """
    Compute all per-90 metrics from aggregates.

    FORMULAS: For each counting stat, divide by minutes and multiply by 90.

    Args:
        aggregates: Dict from compute_basic_aggregates()

    Returns:
        Dict with per90 metrics:
        - goals_per90, assists_per90, shots_per90, etc.

    Example:
        >>> agg = {'total_goals': 15, 'total_minutes': 1800}
        >>> per90 = compute_all_per90_metrics(agg)
        >>> print(per90['goals_per90'])
        0.75
    """
    total_minutes = aggregates.get('total_minutes', 0)

    if total_minutes <= 0:
        logger.warning("Cannot compute per90 metrics: zero minutes played")
        return {}

    per90_metrics = {}

    # All metrics to convert to per90
    metrics_to_convert = [
        'goals', 'assists', 'shots', 'shots_on_target',
        'passes_attempted', 'passes_completed',
        'progressive_passes', 'key_passes',
        'passes_into_final_third', 'passes_into_penalty_area',
        'crosses', 'crosses_completed',
        'tackles', 'tackles_won', 'interceptions', 'blocks',
        'clearances', 'aerial_duels_attempted', 'aerial_duels_won',
        'touches', 'carries', 'progressive_carries',
        'dribbles_attempted', 'dribbles_completed',
        'dispossessed', 'miscontrols', 'dribbled_past',
        'fouls_committed', 'fouls_drawn',
        'yellow_cards', 'red_cards',
        'xg', 'xag'
    ]

    for metric in metrics_to_convert:
        total_key = f'total_{metric}'
        per90_key = f'{metric}_per90'

        if total_key in aggregates:
            per90_metrics[per90_key] = compute_per90(
                aggregates[total_key],
                total_minutes
            )

    return per90_metrics


def compute_percentage_metrics(aggregates: Dict) -> Dict:
    """
    Compute percentage-based metrics from aggregates.

    FORMULAS:
    - pass_completion_pct = (passes_completed / passes_attempted) * 100
    - shot_on_target_pct = (shots_on_target / shots) * 100
    - conversion_rate = (goals / shots) * 100
    - tackle_success_pct = (tackles_won / tackles) * 100
    - dribble_success_pct = (dribbles_completed / dribbles_attempted) * 100
    - aerial_duel_success_pct = (aerial_duels_won / aerial_duels_attempted) * 100
    - cross_completion_pct = (crosses_completed / crosses) * 100

    Args:
        aggregates: Dict from compute_basic_aggregates()

    Returns:
        Dict with percentage metrics
    """
    percentage_metrics = {}

    # Pass completion
    if 'total_passes_attempted' in aggregates:
        percentage_metrics['pass_completion_pct'] = compute_percentage(
            aggregates.get('total_passes_completed', 0),
            aggregates.get('total_passes_attempted', 0)
        )

    # Shot on target percentage
    if 'total_shots' in aggregates:
        percentage_metrics['shot_on_target_pct'] = compute_percentage(
            aggregates.get('total_shots_on_target', 0),
            aggregates.get('total_shots', 0)
        )

    # Conversion rate (goals / shots)
    if 'total_shots' in aggregates:
        percentage_metrics['conversion_rate'] = compute_percentage(
            aggregates.get('total_goals', 0),
            aggregates.get('total_shots', 0)
        )

    # Tackle success
    if 'total_tackles' in aggregates:
        percentage_metrics['tackles_won_pct'] = compute_percentage(
            aggregates.get('total_tackles_won', 0),
            aggregates.get('total_tackles', 0)
        )

    # Dribble success
    if 'total_dribbles_attempted' in aggregates:
        percentage_metrics['dribble_success_pct'] = compute_percentage(
            aggregates.get('total_dribbles_completed', 0),
            aggregates.get('total_dribbles_attempted', 0)
        )

    # Aerial duel success
    if 'total_aerial_duels_attempted' in aggregates:
        percentage_metrics['aerial_duels_won_pct'] = compute_percentage(
            aggregates.get('total_aerial_duels_won', 0),
            aggregates.get('total_aerial_duels_attempted', 0)
        )

    # Cross completion
    if 'total_crosses' in aggregates:
        percentage_metrics['cross_completion_pct'] = compute_percentage(
            aggregates.get('total_crosses_completed', 0),
            aggregates.get('total_crosses', 0)
        )

    return percentage_metrics


def compute_derived_metrics(aggregates: Dict, per90_metrics: Dict) -> Dict:
    """
    Compute derived metrics that combine multiple stats.

    FORMULAS:
    - xg_overperformance = total_goals - total_xg
    - defensive_actions_per90 = tackles_per90 + interceptions_per90 + blocks_per90
    - non_penalty_goals = total_goals - total_penalties (if available)

    Args:
        aggregates: Dict from compute_basic_aggregates()
        per90_metrics: Dict from compute_all_per90_metrics()

    Returns:
        Dict with derived metrics
    """
    derived = {}

    # xG overperformance (finishing quality)
    if 'total_goals' in aggregates and 'total_xg' in aggregates:
        derived['xg_overperformance'] = (
            aggregates['total_goals'] - aggregates['total_xg']
        )

    # Defensive actions per 90
    if all(k in per90_metrics for k in ['tackles_per90', 'interceptions_per90', 'blocks_per90']):
        derived['defensive_actions_per90'] = (
            per90_metrics['tackles_per90'] +
            per90_metrics['interceptions_per90'] +
            per90_metrics['blocks_per90']
        )

    # Non-penalty goals (if penalty data available)
    if 'total_goals' in aggregates and 'total_penalties_scored' in aggregates:
        derived['non_penalty_goals'] = (
            aggregates['total_goals'] - aggregates.get('total_penalties_scored', 0)
        )

    # Goal contributions (goals + assists)
    if 'total_goals' in aggregates and 'total_assists' in aggregates:
        derived['total_goal_contributions'] = (
            aggregates['total_goals'] + aggregates['total_assists']
        )

        if 'total_minutes' in aggregates and aggregates['total_minutes'] > 0:
            derived['goal_contributions_per90'] = compute_per90(
                derived['total_goal_contributions'],
                aggregates['total_minutes']
            )

    return derived


# ============================================================================
# MAIN COMPUTATION FUNCTIONS
# ============================================================================

def compute_player_season_metrics(
    player_id: int,
    season: Optional[str] = None,
    competition: Optional[str] = None,
    min_minutes: int = DEFAULT_MIN_MINUTES
) -> Dict:
    """
    Compute comprehensive metrics for a player in a season.

    This is the PRIMARY FUNCTION for getting player metrics.

    Args:
        player_id: Player identifier
        season: Optional season filter (e.g., "2023-24")
        competition: Optional competition filter
        min_minutes: Minimum minutes threshold for valid analysis

    Returns:
        Dict with structure:
        {
            'player_info': {...},
            'aggregates': {...},
            'per90_metrics': {...},
            'percentage_metrics': {...},
            'derived_metrics': {...},
            'meets_minimum': bool
        }

    Example:
        >>> metrics = compute_player_season_metrics(
        ...     player_id=123,
        ...     season="2023-24",
        ...     min_minutes=450
        ... )
        >>> print(metrics['per90_metrics']['goals_per90'])
        0.75
        >>> print(metrics['percentage_metrics']['pass_completion_pct'])
        87.3
    """
    logger.info(
        f"Computing metrics for player {player_id}"
        + (f" in season {season}" if season else "")
        + (f" in {competition}" if competition else "")
    )

    # Step 1: Fetch player info
    try:
        player_info = fetch_player_info(player_id)
    except ValueError as e:
        logger.error(f"Failed to fetch player info: {e}")
        return {'error': str(e)}

    # Step 2: Fetch match data
    df = fetch_player_match_stats(
        player_id=player_id,
        season=season,
        competition=competition
    )

    if df.empty:
        logger.warning(f"No match data found for player {player_id}")
        return {
            'player_info': player_info,
            'aggregates': {},
            'per90_metrics': {},
            'percentage_metrics': {},
            'derived_metrics': {},
            'meets_minimum': False,
            'error': 'No match data found'
        }

    # Step 3: Compute aggregates
    aggregates = compute_basic_aggregates(df)

    # Step 4: Check minimum minutes threshold
    total_minutes = aggregates.get('total_minutes', 0)
    meets_minimum = total_minutes >= min_minutes

    if not meets_minimum:
        logger.warning(
            f"Player {player_id} has only {total_minutes} minutes "
            f"(minimum: {min_minutes})"
        )

    # Step 5: Compute per90 metrics
    per90_metrics = compute_all_per90_metrics(aggregates)

    # Step 6: Compute percentage metrics
    percentage_metrics = compute_percentage_metrics(aggregates)

    # Step 7: Compute derived metrics
    derived_metrics = compute_derived_metrics(aggregates, per90_metrics)

    # Step 8: Combine all results
    result = {
        'player_info': player_info,
        'aggregates': aggregates,
        'per90_metrics': per90_metrics,
        'percentage_metrics': percentage_metrics,
        'derived_metrics': derived_metrics,
        'meets_minimum': meets_minimum,
        'min_minutes_threshold': min_minutes
    }

    logger.info(
        f"Successfully computed {len(per90_metrics) + len(percentage_metrics) + len(derived_metrics)} "
        f"metrics for player {player_id}"
    )

    return result


def compute_player_metrics_multiple_seasons(
    player_id: int,
    seasons: List[str],
    min_minutes: int = DEFAULT_MIN_MINUTES
) -> Dict[str, Dict]:
    """
    Compute metrics for a player across multiple seasons.

    Args:
        player_id: Player identifier
        seasons: List of season strings (e.g., ["2022-23", "2023-24"])
        min_minutes: Minimum minutes threshold per season

    Returns:
        Dict mapping season -> metrics dict

    Example:
        >>> metrics = compute_player_metrics_multiple_seasons(
        ...     player_id=123,
        ...     seasons=["2022-23", "2023-24"]
        ... )
        >>> print(metrics["2023-24"]['per90_metrics']['goals_per90'])
        0.75
    """
    results = {}

    for season in seasons:
        logger.info(f"Computing metrics for season {season}")
        results[season] = compute_player_season_metrics(
            player_id=player_id,
            season=season,
            min_minutes=min_minutes
        )

    return results


# ============================================================================
# TEAM AGGREGATE FUNCTIONS
# ============================================================================

def compute_team_aggregates(
    team_id: int,
    season: str,
    min_minutes: int = DEFAULT_MIN_MINUTES
) -> Dict:
    """
    Compute aggregate statistics for all players on a team.

    Args:
        team_id: Team identifier
        season: Season string (e.g., "2023-24")
        min_minutes: Minimum minutes for player to be included

    Returns:
        Dict with structure:
        {
            'team_info': {...},
            'players': [
                {
                    'player_id': int,
                    'name': str,
                    'position': str,
                    'metrics': {...}
                },
                ...
            ],
            'team_totals': {...},
            'team_averages': {...}
        }
    """
    logger.info(f"Computing team aggregates for team {team_id} in season {season}")

    # Step 1: Get all players on team
    query = """
        SELECT DISTINCT p.player_id, p.name, p.position
        FROM players p
        WHERE p.current_team = (SELECT name FROM teams WHERE team_id = %s)
    """

    players_df = fetch_dataframe(query, params=(team_id,))

    if players_df.empty:
        logger.warning(f"No players found for team {team_id}")
        return {'error': 'No players found'}

    # Step 2: Compute metrics for each player
    player_metrics = []

    for _, player_row in players_df.iterrows():
        player_id = player_row['player_id']

        metrics = compute_player_season_metrics(
            player_id=player_id,
            season=season,
            min_minutes=min_minutes
        )

        if metrics.get('meets_minimum', False):
            player_metrics.append({
                'player_id': player_id,
                'name': player_row['name'],
                'position': player_row['position'],
                'metrics': metrics
            })

    # Step 3: Compute team totals
    team_totals = {}
    if player_metrics:
        # Sum aggregates across all players
        for player_data in player_metrics:
            agg = player_data['metrics'].get('aggregates', {})
            for key, value in agg.items():
                if key.startswith('total_'):
                    team_totals[key] = team_totals.get(key, 0) + value

    # Step 4: Compute team averages
    team_averages = {}
    if player_metrics:
        num_players = len(player_metrics)
        for player_data in player_metrics:
            per90 = player_data['metrics'].get('per90_metrics', {})
            for key, value in per90.items():
                team_averages[key] = team_averages.get(key, 0) + value / num_players

    return {
        'team_id': team_id,
        'season': season,
        'num_players': len(player_metrics),
        'players': player_metrics,
        'team_totals': team_totals,
        'team_averages': team_averages
    }


# ============================================================================
# PERCENTILE RANKING FUNCTIONS
# ============================================================================

def compute_percentile_rank(
    value: float,
    cohort_values: List[float],
    higher_is_better: bool = True
) -> float:
    """
    Compute percentile rank of a value within a cohort.

    FORMULA: Rank value among cohort and convert to 0-100 scale.

    Args:
        value: Player's metric value
        cohort_values: List of metric values from comparison cohort
        higher_is_better: If True, higher values get higher percentiles

    Returns:
        Percentile rank (0-100)

    Example:
        >>> cohort = [1.0, 2.0, 3.0, 4.0, 5.0]
        >>> compute_percentile_rank(4.0, cohort, higher_is_better=True)
        80.0  # 4.0 is at 80th percentile
    """
    if not cohort_values or len(cohort_values) == 0:
        return 50.0  # Default to median if no cohort

    cohort_array = np.array(cohort_values)

    # Count how many values are below the target value
    if higher_is_better:
        below_count = np.sum(cohort_array < value)
    else:
        below_count = np.sum(cohort_array > value)

    # Compute percentile
    percentile = (below_count / len(cohort_array)) * 100

    return percentile


def compute_percentiles_for_player(
    player_metrics: Dict,
    cohort_metrics: List[Dict],
    metrics_to_rank: List[str]
) -> Dict[str, float]:
    """
    Compute percentile rankings for player metrics within a cohort.

    Args:
        player_metrics: Dict with player's per90_metrics
        cohort_metrics: List of dicts with per90_metrics from cohort
        metrics_to_rank: List of metric names to compute percentiles for

    Returns:
        Dict mapping metric_name -> percentile_rank

    Example:
        >>> percentiles = compute_percentiles_for_player(
        ...     player_metrics={'per90_metrics': {'goals_per90': 0.8}},
        ...     cohort_metrics=[...],  # Other players
        ...     metrics_to_rank=['goals_per90']
        ... )
        >>> print(percentiles['goals_per90'])
        75.0  # Player is at 75th percentile for goals
    """
    per90 = player_metrics.get('per90_metrics', {})
    percentiles = {}

    for metric_name in metrics_to_rank:
        if metric_name not in per90:
            continue

        player_value = per90[metric_name]

        # Extract cohort values
        cohort_values = [
            p.get('per90_metrics', {}).get(metric_name, 0)
            for p in cohort_metrics
            if metric_name in p.get('per90_metrics', {})
        ]

        if not cohort_values:
            continue

        # Get whether higher is better from registry
        higher_better = is_higher_better(metric_name)

        # Compute percentile
        percentiles[f'{metric_name}_percentile'] = compute_percentile_rank(
            player_value,
            cohort_values,
            higher_is_better=higher_better
        )

    return percentiles


# ============================================================================
# VALIDATION AND ERROR HANDLING
# ============================================================================

def validate_minimum_minutes(
    total_minutes: float,
    min_minutes: int,
    metric_name: str
) -> bool:
    """
    Validate that player has minimum minutes for meaningful metric.

    Args:
        total_minutes: Player's total minutes
        min_minutes: Required minimum minutes
        metric_name: Name of metric being computed

    Returns:
        True if player meets minimum, False otherwise
    """
    if total_minutes < min_minutes:
        logger.warning(
            f"Player has {total_minutes} minutes (minimum {min_minutes} required) "
            f"for metric {metric_name}"
        )
        return False

    return True


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    """
    Example usage of metrics service.

    NOTE: Requires database connection and valid player IDs.
    """

    # Initialize database
    from utils.db import startup_db, shutdown_db
    startup_db()

    try:
        print("=" * 80)
        print("METRICS SERVICE - EXAMPLE USAGE")
        print("=" * 80)

        # Example 1: Compute metrics for single player/season
        print("\n[Example 1] Player Season Metrics")
        print("-" * 40)

        metrics = compute_player_season_metrics(
            player_id=123,  # Replace with actual player ID
            season="2023-24",
            min_minutes=450
        )

        if 'error' not in metrics:
            print(f"Player: {metrics['player_info']['name']}")
            print(f"Total Minutes: {metrics['aggregates']['total_minutes']}")
            print(f"Goals per 90: {metrics['per90_metrics'].get('goals_per90', 0):.2f}")
            print(f"Pass Completion: {metrics['percentage_metrics'].get('pass_completion_pct', 0):.1f}%")

        # Example 2: Multiple seasons
        print("\n[Example 2] Multiple Seasons")
        print("-" * 40)

        multi_season = compute_player_metrics_multiple_seasons(
            player_id=123,
            seasons=["2022-23", "2023-24"]
        )

        for season, data in multi_season.items():
            if 'error' not in data:
                goals_per90 = data['per90_metrics'].get('goals_per90', 0)
                print(f"{season}: {goals_per90:.2f} goals per 90")

        print("\n" + "=" * 80)

    finally:
        shutdown_db()
