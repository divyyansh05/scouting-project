"""
Role Service - services/role_service.py

RESPONSIBILITIES:
-----------------
Convert raw positional/spatial data into role vectors.
Role vectors describe WHERE and HOW a player operates on the pitch.

CRITICAL DISTINCTIONS:
---------------------
- metrics_service.py: WHAT the player does (goals, passes, tackles)
- role_service.py: WHERE the player operates (position, zones, spatial behavior)
- similarity_service.py: HOW SIMILAR players are to each other

ROLE VECTOR PHILOSOPHY:
----------------------
A role vector is a numerical fingerprint of a player's spatial behavior.
Two players with similar role vectors operate in similar areas and ways,
regardless of their statistical output.

Example:
- Player A: Left Winger, hugs touchline, runs in behind
- Player B: Left Winger, cuts inside, dribbles centrally
- Same position, different roles -> different vectors

VERSIONING:
----------
Role vector formula may evolve over time. Version string ensures:
- We know which formula was used
- Old vectors can't be compared to new vectors
- Changes are tracked and documented

CRITICAL RULES:
--------------
- NO STORAGE - Vectors computed on-demand, not persisted
- NO SIMILARITY - Similarity computation is in similarity_service.py
- DETERMINISTIC - Same input always produces same vector
- EXPLAINABLE - Every vector component has clear meaning
- VERSIONED - Vector formula has version identifier
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from utils.db import fetch_dataframe
from services.metrics_service import compute_player_season_metrics

logger = logging.getLogger(__name__)


# ============================================================================
# VERSION MANAGEMENT
# ============================================================================

# CURRENT ROLE VECTOR VERSION
# Increment this when vector formula changes
ROLE_VECTOR_VERSION = "v1.0.0"

# Version history and changes
VERSION_HISTORY = {
    "v1.0.0": {
        "date": "2024-12-21",
        "dimensions": 20,
        "components": [
            "Average X position (0-100)",
            "Average Y position (0-100)",
            "Positional spread X (variance)",
            "Positional spread Y (variance)",
            "Attacking third presence %",
            "Middle third presence %",
            "Defensive third presence %",
            "Left zone presence %",
            "Center zone presence %",
            "Right zone presence %",
            "Forward pass tendency %",
            "Backward pass tendency %",
            "Lateral pass tendency %",
            "Progressive carry tendency %",
            "Touches in box per 90",
            "Deep completions per 90",
            "High regains per 90",
            "Width (avg distance from center)",
            "Verticality (progressive distance per action)",
            "Involvement (touches per 90 normalized)"
        ],
        "description": "Initial role vector implementation based on spatial data"
    }
}


def get_role_vector_version() -> str:
    """
    Get current role vector version.

    Returns:
        Version string (e.g., "v1.0.0")

    Example:
        >>> version = get_role_vector_version()
        >>> print(version)
        'v1.0.0'
    """
    return ROLE_VECTOR_VERSION


def get_version_info(version: str = None) -> Dict:
    """
    Get detailed information about a role vector version.

    Args:
        version: Version string (default: current version)

    Returns:
        Dict with version metadata

    Example:
        >>> info = get_version_info("v1.0.0")
        >>> print(info['dimensions'])
        20
        >>> print(info['components'][0])
        'Average X position (0-100)'
    """
    if version is None:
        version = ROLE_VECTOR_VERSION

    return VERSION_HISTORY.get(version, {})


# ============================================================================
# DATA FETCHING FUNCTIONS
# ============================================================================

def fetch_player_positional_data(
    player_id: int,
    season: Optional[str] = None,
    competition: Optional[str] = None
) -> pd.DataFrame:
    """
    Fetch raw positional/spatial data for a player.

    This data describes WHERE the player operates, not WHAT they produce.

    Args:
        player_id: Player identifier
        season: Optional season filter
        competition: Optional competition filter

    Returns:
        DataFrame with columns:
        - match_id, match_date
        - avg_x, avg_y (average position on pitch, 0-100 scale)
        - touches_in_zones (JSON or separate columns)
        - passes_by_direction (forward, backward, lateral counts)
        - carries_progressive (progressive carry count)
        - touches_in_box
        - deep_completions (passes into final third)
        - high_regains (regains in attacking third)

    Note:
        Pitch coordinates:
        - X: 0 (own goal) to 100 (opponent goal)
        - Y: 0 (left touchline) to 100 (right touchline)
        - Center: X=50, Y=50
    """
    query = """
        SELECT
            ps.match_id,
            m.match_date,
            m.competition,
            m.season,

            -- Average position (normalized 0-100)
            ps.avg_x_position,
            ps.avg_y_position,

            -- Positional variance (how much they move)
            ps.x_position_variance,
            ps.y_position_variance,

            -- Zone presence (attacking, middle, defensive thirds)
            ps.touches_attacking_third,
            ps.touches_middle_third,
            ps.touches_defensive_third,

            -- Width zones (left, center, right)
            ps.touches_left_zone,
            ps.touches_center_zone,
            ps.touches_right_zone,

            -- Pass directions
            ps.passes_forward,
            ps.passes_backward,
            ps.passes_lateral,

            -- Progressive actions
            ps.progressive_carries,
            ps.progressive_passes,

            -- Key spatial metrics
            ps.touches_in_box,
            ps.deep_completions,  -- Passes into final third
            ps.high_regains,  -- Ball regains in attacking third

            -- Total touches for normalization
            ps.touches,
            ps.minutes_played

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

    if df.empty:
        logger.warning(f"No positional data found for player {player_id}")
    else:
        logger.info(
            f"Fetched positional data for {len(df)} matches for player {player_id}"
        )

    return df


# ============================================================================
# VECTOR COMPONENT COMPUTATION FUNCTIONS
# ============================================================================

def compute_average_position(df: pd.DataFrame) -> Tuple[float, float]:
    """
    Compute player's average position on pitch.

    FORMULA:
        avg_x = weighted_mean(avg_x_position, weights=minutes_played)
        avg_y = weighted_mean(avg_y_position, weights=minutes_played)

    Args:
        df: DataFrame with positional data

    Returns:
        Tuple of (avg_x, avg_y) in range 0-100

    Interpretation:
        X: 0 (own goal) to 100 (opponent goal)
        Y: 0 (left) to 100 (right)

        X=62 -> Primarily in attacking half
        Y=22 -> Primarily on left side
    """
    if df.empty or df['minutes_played'].sum() == 0:
        return 50.0, 50.0  # Default to center

    weights = df['minutes_played']

    avg_x = np.average(df['avg_x_position'], weights=weights)
    avg_y = np.average(df['avg_y_position'], weights=weights)

    # Ensure in valid range
    avg_x = np.clip(avg_x, 0, 100)
    avg_y = np.clip(avg_y, 0, 100)

    return float(avg_x), float(avg_y)


def compute_positional_spread(df: pd.DataFrame) -> Tuple[float, float]:
    """
    Compute variance in player's position (how much they roam).

    FORMULA:
        spread_x = weighted_variance(x_position_variance, weights=minutes)
        spread_y = weighted_variance(y_position_variance, weights=minutes)

    Args:
        df: DataFrame with positional data

    Returns:
        Tuple of (spread_x, spread_y)

    Interpretation:
        Low spread (0-5): Stays in fixed position (e.g., target striker)
        Medium spread (5-15): Moderate movement (e.g., box-to-box midfielder)
        High spread (15+): Roams widely (e.g., free roam attacking mid)
    """
    if df.empty or df['minutes_played'].sum() == 0:
        return 10.0, 10.0  # Default moderate spread

    weights = df['minutes_played']

    spread_x = np.average(df['x_position_variance'], weights=weights)
    spread_y = np.average(df['y_position_variance'], weights=weights)

    return float(spread_x), float(spread_y)


def compute_zone_distribution(df: pd.DataFrame) -> Dict[str, float]:
    """
    Compute percentage of touches in each zone.

    FORMULA:
        zone_% = (total_touches_in_zone / total_touches) * 100

    Args:
        df: DataFrame with zone touch data

    Returns:
        Dict with zone percentages:
        {
            'attacking_third': 0-100,
            'middle_third': 0-100,
            'defensive_third': 0-100,
            'left_zone': 0-100,
            'center_zone': 0-100,
            'right_zone': 0-100
        }

    Interpretation:
        Attacking third % > 60: Forward/winger
        Middle third % > 60: Central midfielder
        Defensive third % > 60: Defender/defensive mid

        Left zone % > 50: Left-sided player
        Center zone % > 50: Central player
        Right zone % > 50: Right-sided player
    """
    if df.empty:
        return {
            'attacking_third': 33.3,
            'middle_third': 33.3,
            'defensive_third': 33.3,
            'left_zone': 33.3,
            'center_zone': 33.3,
            'right_zone': 33.3
        }

    # Sum touches across all matches
    total_touches = df['touches'].sum()

    if total_touches == 0:
        return {
            'attacking_third': 33.3,
            'middle_third': 33.3,
            'defensive_third': 33.3,
            'left_zone': 33.3,
            'center_zone': 33.3,
            'right_zone': 33.3
        }

    # Vertical zones (thirds)
    attacking_touches = df['touches_attacking_third'].sum()
    middle_touches = df['touches_middle_third'].sum()
    defensive_touches = df['touches_defensive_third'].sum()

    # Horizontal zones (width)
    left_touches = df['touches_left_zone'].sum()
    center_touches = df['touches_center_zone'].sum()
    right_touches = df['touches_right_zone'].sum()

    return {
        'attacking_third': (attacking_touches / total_touches) * 100,
        'middle_third': (middle_touches / total_touches) * 100,
        'defensive_third': (defensive_touches / total_touches) * 100,
        'left_zone': (left_touches / total_touches) * 100,
        'center_zone': (center_touches / total_touches) * 100,
        'right_zone': (right_touches / total_touches) * 100
    }


def compute_pass_direction_distribution(df: pd.DataFrame) -> Dict[str, float]:
    """
    Compute percentage of passes in each direction.

    FORMULA:
        direction_% = (passes_in_direction / total_passes) * 100

    Args:
        df: DataFrame with pass direction data

    Returns:
        Dict with direction percentages:
        {
            'forward': 0-100,
            'backward': 0-100,
            'lateral': 0-100
        }

    Interpretation:
        Forward % > 50: Progressive passer
        Backward % > 40: Safe/recycling passer
        Lateral % > 40: Horizontal distributor
    """
    if df.empty:
        return {'forward': 33.3, 'backward': 33.3, 'lateral': 33.3}

    total_passes = (
        df['passes_forward'].sum() +
        df['passes_backward'].sum() +
        df['passes_lateral'].sum()
    )

    if total_passes == 0:
        return {'forward': 33.3, 'backward': 33.3, 'lateral': 33.3}

    return {
        'forward': (df['passes_forward'].sum() / total_passes) * 100,
        'backward': (df['passes_backward'].sum() / total_passes) * 100,
        'lateral': (df['passes_lateral'].sum() / total_passes) * 100
    }


def compute_progressive_tendency(df: pd.DataFrame) -> float:
    """
    Compute how progressive a player's actions are.

    FORMULA:
        progressive_tendency = (progressive_carries + progressive_passes) / touches
        Normalized to 0-100 scale

    Args:
        df: DataFrame with carry/pass data

    Returns:
        Progressive tendency score (0-100)

    Interpretation:
        0-20: Conservative, safe player
        20-40: Balanced
        40-60: Progressive
        60-100: Highly aggressive/progressive
    """
    if df.empty:
        return 30.0  # Default to moderate

    total_progressive = (
        df['progressive_carries'].sum() +
        df['progressive_passes'].sum()
    )
    total_touches = df['touches'].sum()

    if total_touches == 0:
        return 30.0

    # Raw ratio
    ratio = total_progressive / total_touches

    # Scale to 0-100 (assuming max ~0.3 progressive actions per touch)
    tendency = min(ratio * 333.33, 100.0)

    return float(tendency)


def compute_spatial_metrics_per90(
    df: pd.DataFrame,
    total_minutes: float
) -> Dict[str, float]:
    """
    Compute per-90 spatial metrics.

    Args:
        df: DataFrame with spatial data
        total_minutes: Total minutes played

    Returns:
        Dict with per90 spatial metrics:
        {
            'touches_in_box_per90': float,
            'deep_completions_per90': float,
            'high_regains_per90': float
        }
    """
    if df.empty or total_minutes <= 0:
        return {
            'touches_in_box_per90': 0.0,
            'deep_completions_per90': 0.0,
            'high_regains_per90': 0.0
        }

    return {
        'touches_in_box_per90': (df['touches_in_box'].sum() / total_minutes) * 90,
        'deep_completions_per90': (df['deep_completions'].sum() / total_minutes) * 90,
        'high_regains_per90': (df['high_regains'].sum() / total_minutes) * 90
    }


def compute_width_score(avg_y: float) -> float:
    """
    Compute how wide a player operates.

    FORMULA:
        width = abs(avg_y - 50)

        Where avg_y is 0 (left) to 100 (right), and 50 is center

    Args:
        avg_y: Average Y position (0-100)

    Returns:
        Width score (0-50)
        0 = plays centrally
        50 = plays on extreme wing

    Interpretation:
        0-10: Central player
        10-25: Inside forward / half-space
        25-40: Wide midfielder
        40-50: Touchline hugger
    """
    return abs(avg_y - 50.0)


def compute_verticality_score(
    progressive_tendency: float,
    avg_x: float
) -> float:
    """
    Compute how vertically the player plays.

    FORMULA:
        verticality = progressive_tendency * (avg_x / 100)

        Combines how progressive they are with how advanced their position is

    Args:
        progressive_tendency: Progressive action tendency (0-100)
        avg_x: Average X position (0-100)

    Returns:
        Verticality score (0-100)

    Interpretation:
        High verticality = Advanced position + progressive actions
        Low verticality = Deep position or conservative play
    """
    return (progressive_tendency * (avg_x / 100.0))


def compute_involvement_score(
    touches_per90: float,
    position_type: str = "outfield"
) -> float:
    """
    Compute how involved a player is in the game.

    FORMULA:
        involvement = min(touches_per90 / expected_touches_per90, 100)

        Where expected touches varies by position type

    Args:
        touches_per90: Touches per 90 minutes
        position_type: "goalkeeper", "defender", "midfielder", "forward", "outfield"

    Returns:
        Involvement score (0-100)

    Interpretation:
        0-30: Low involvement (target striker, etc.)
        30-60: Moderate involvement
        60-100: High involvement (playmaker, etc.)
    """
    # Expected touches per 90 by position
    expected_touches = {
        'goalkeeper': 30,
        'defender': 60,
        'midfielder': 80,
        'forward': 50,
        'outfield': 65  # Default
    }

    expected = expected_touches.get(position_type, 65)

    # Normalize
    involvement = min((touches_per90 / expected) * 100, 100.0)

    return float(involvement)


# ============================================================================
# MAIN ROLE VECTOR CONSTRUCTION
# ============================================================================

def build_role_vector(
    player_id: int,
    season: Optional[str] = None,
    competition: Optional[str] = None,
    min_minutes: int = 450
) -> Dict:
    """
    Build complete role vector for a player.

    This is the PRIMARY FUNCTION of the role service.

    A role vector is a numerical representation of WHERE and HOW
    a player operates on the pitch.

    Args:
        player_id: Player identifier
        season: Optional season filter
        competition: Optional competition filter
        min_minutes: Minimum minutes for valid vector

    Returns:
        Dict with structure:
        {
            'player_id': int,
            'season': str,
            'vector': numpy.ndarray,  # 20-dimensional vector
            'vector_version': str,  # e.g., "v1.0.0"
            'components': Dict,  # Breakdown of vector components
            'metadata': Dict,  # Additional info
            'meets_minimum': bool,
            'total_minutes': float
        }

    Example:
        >>> result = build_role_vector(player_id=123, season="2023-24")
        >>> print(result['vector'])
        [62.3, 22.1, 8.5, 12.3, 65.2, 28.1, 6.7, ...]
        >>> print(result['components']['avg_x'])
        62.3  # Plays in attacking half
        >>> print(result['components']['left_zone_pct'])
        78.5  # Left-sided player
    """
    logger.info(
        f"Building role vector for player {player_id}"
        + (f" in season {season}" if season else "")
    )

    # Step 1: Fetch positional data
    df = fetch_player_positional_data(
        player_id=player_id,
        season=season,
        competition=competition
    )

    if df.empty:
        logger.warning(f"No positional data for player {player_id}")
        return {
            'player_id': player_id,
            'season': season,
            'vector': None,
            'vector_version': ROLE_VECTOR_VERSION,
            'components': {},
            'metadata': {'error': 'No positional data found'},
            'meets_minimum': False,
            'total_minutes': 0
        }

    # Step 2: Check minimum minutes
    total_minutes = df['minutes_played'].sum()
    meets_minimum = total_minutes >= min_minutes

    if not meets_minimum:
        logger.warning(
            f"Player {player_id} has only {total_minutes} minutes "
            f"(minimum: {min_minutes})"
        )

    # Step 3: Compute vector components

    # Position (2 components)
    avg_x, avg_y = compute_average_position(df)

    # Positional spread (2 components)
    spread_x, spread_y = compute_positional_spread(df)

    # Zone distribution (6 components)
    zones = compute_zone_distribution(df)

    # Pass direction distribution (3 components)
    pass_dirs = compute_pass_direction_distribution(df)

    # Progressive tendency (1 component)
    progressive_tendency = compute_progressive_tendency(df)

    # Spatial metrics per 90 (3 components)
    spatial_per90 = compute_spatial_metrics_per90(df, total_minutes)

    # Derived metrics (3 components)
    width = compute_width_score(avg_y)
    verticality = compute_verticality_score(progressive_tendency, avg_x)

    # Get touches per 90 for involvement
    # We need to fetch metrics for this
    try:
        metrics = compute_player_season_metrics(player_id, season)
        touches_per90 = metrics.get('per90_metrics', {}).get('touches_per90', 60)
    except Exception:
        touches_per90 = 60  # Default

    involvement = compute_involvement_score(touches_per90)

    # Step 4: Assemble vector components (order matters!)
    components = {
        # Position and spread (4 components)
        'avg_x': avg_x,
        'avg_y': avg_y,
        'spread_x': spread_x,
        'spread_y': spread_y,

        # Vertical zones (3 components)
        'attacking_third_pct': zones['attacking_third'],
        'middle_third_pct': zones['middle_third'],
        'defensive_third_pct': zones['defensive_third'],

        # Horizontal zones (3 components)
        'left_zone_pct': zones['left_zone'],
        'center_zone_pct': zones['center_zone'],
        'right_zone_pct': zones['right_zone'],

        # Pass directions (3 components)
        'forward_pass_pct': pass_dirs['forward'],
        'backward_pass_pct': pass_dirs['backward'],
        'lateral_pass_pct': pass_dirs['lateral'],

        # Progressive tendency (1 component)
        'progressive_tendency': progressive_tendency,

        # Spatial per 90s (3 components)
        'touches_in_box_per90': spatial_per90['touches_in_box_per90'],
        'deep_completions_per90': spatial_per90['deep_completions_per90'],
        'high_regains_per90': spatial_per90['high_regains_per90'],

        # Derived metrics (3 components)
        'width': width,
        'verticality': verticality,
        'involvement': involvement
    }

    # Step 5: Create numpy vector (20 dimensions)
    vector = np.array([
        components['avg_x'],
        components['avg_y'],
        components['spread_x'],
        components['spread_y'],
        components['attacking_third_pct'],
        components['middle_third_pct'],
        components['defensive_third_pct'],
        components['left_zone_pct'],
        components['center_zone_pct'],
        components['right_zone_pct'],
        components['forward_pass_pct'],
        components['backward_pass_pct'],
        components['lateral_pass_pct'],
        components['progressive_tendency'],
        components['touches_in_box_per90'],
        components['deep_completions_per90'],
        components['high_regains_per90'],
        components['width'],
        components['verticality'],
        components['involvement']
    ])

    # Step 6: Assemble result
    result = {
        'player_id': player_id,
        'season': season,
        'competition': competition,
        'vector': vector,
        'vector_version': ROLE_VECTOR_VERSION,
        'vector_dimensions': len(vector),
        'components': components,
        'metadata': {
            'matches_analyzed': len(df),
            'computation_date': datetime.now().isoformat(),
            'vector_description': 'Spatial role vector describing player position and behavior'
        },
        'meets_minimum': meets_minimum,
        'total_minutes': total_minutes,
        'min_minutes_threshold': min_minutes
    }

    logger.info(
        f"Built role vector for player {player_id}: "
        f"{len(vector)} dimensions, {total_minutes:.0f} minutes analyzed"
    )

    return result


def explain_role_vector(role_vector_result: Dict) -> str:
    """
    Generate human-readable explanation of a role vector.

    Args:
        role_vector_result: Dict returned by build_role_vector()

    Returns:
        Human-readable explanation string

    Example:
        >>> result = build_role_vector(123, "2023-24")
        >>> explanation = explain_role_vector(result)
        >>> print(explanation)
        This player operates primarily in the attacking half (x=62.3),
        on the left side (y=22.1). They are a progressive player with
        high forward pass tendency (58.2%) and frequent touches in the
        box (3.2 per 90). Their role is best described as an
        "Advanced Left Winger / Inside Forward".
    """
    if not role_vector_result or role_vector_result.get('vector') is None:
        return "Insufficient data to explain role vector."

    comp = role_vector_result['components']

    # Analyze position
    avg_x = comp['avg_x']
    avg_y = comp['avg_y']

    # Determine horizontal position
    if avg_y < 30:
        horizontal = "left side"
    elif avg_y > 70:
        horizontal = "right side"
    else:
        horizontal = "central areas"

    # Determine vertical position
    if avg_x < 40:
        vertical = "defensive areas"
    elif avg_x > 60:
        vertical = "attacking areas"
    else:
        vertical = "middle areas"

    # Determine role characteristics
    characteristics = []

    if comp['progressive_tendency'] > 50:
        characteristics.append("progressive")
    if comp['forward_pass_pct'] > 50:
        characteristics.append("forward-passing")
    if comp['width'] > 25:
        characteristics.append("wide")
    if comp['touches_in_box_per90'] > 2:
        characteristics.append("box-active")
    if comp['high_regains_per90'] > 1:
        characteristics.append("high-pressing")

    explanation = (
        f"This player operates primarily in the {vertical} "
        f"(x={avg_x:.1f}), on the {horizontal} (y={avg_y:.1f}). "
    )

    if characteristics:
        explanation += (
            f"They are a {', '.join(characteristics)} player. "
        )

    # Add key stats
    explanation += (
        f"Key behaviors: {comp['forward_pass_pct']:.1f}% forward passes, "
        f"{comp['touches_in_box_per90']:.1f} touches in box per 90, "
        f"{comp['progressive_tendency']:.1f} progressive tendency score."
    )

    return explanation


# ============================================================================
# BATCH PROCESSING
# ============================================================================

def build_role_vectors_batch(
    player_ids: List[int],
    season: str,
    min_minutes: int = 450
) -> Dict[int, Dict]:
    """
    Build role vectors for multiple players.

    Args:
        player_ids: List of player identifiers
        season: Season string
        min_minutes: Minimum minutes threshold

    Returns:
        Dict mapping player_id -> role_vector_result

    Example:
        >>> player_ids = [1, 2, 3, 4, 5]
        >>> vectors = build_role_vectors_batch(player_ids, "2023-24")
        >>> for pid, result in vectors.items():
        ...     if result['meets_minimum']:
        ...         print(f"Player {pid}: {result['vector'][:3]}")
    """
    results = {}

    for player_id in player_ids:
        try:
            result = build_role_vector(
                player_id=player_id,
                season=season,
                min_minutes=min_minutes
            )
            results[player_id] = result
        except Exception as e:
            logger.error(f"Failed to build vector for player {player_id}: {e}")
            results[player_id] = {
                'player_id': player_id,
                'vector': None,
                'error': str(e)
            }

    logger.info(f"Built role vectors for {len(results)} players")

    return results


# ============================================================================
# VALIDATION
# ============================================================================

def validate_role_vector(vector: np.ndarray, version: str) -> bool:
    """
    Validate a role vector.

    Args:
        vector: Numpy array role vector
        version: Version string

    Returns:
        True if valid, False otherwise
    """
    if vector is None:
        return False

    if not isinstance(vector, np.ndarray):
        return False

    version_info = get_version_info(version)
    if not version_info:
        logger.warning(f"Unknown vector version: {version}")
        return False

    expected_dims = version_info.get('dimensions', 20)
    if len(vector) != expected_dims:
        logger.warning(
            f"Vector has {len(vector)} dimensions, expected {expected_dims}"
        )
        return False

    # Check for NaN or inf
    if np.any(np.isnan(vector)) or np.any(np.isinf(vector)):
        logger.warning("Vector contains NaN or inf values")
        return False

    return True


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    """
    Example usage of role service.
    """

    from utils.db import startup_db, shutdown_db
    startup_db()

    try:
        print("=" * 80)
        print("ROLE SERVICE - EXAMPLE USAGE")
        print("=" * 80)

        # Example 1: Build single role vector
        print("\n[Example 1] Build Role Vector")
        print("-" * 40)

        result = build_role_vector(
            player_id=123,
            season="2023-24",
            min_minutes=450
        )

        if result['vector'] is not None:
            print(f"Vector dimensions: {result['vector_dimensions']}")
            print(f"Version: {result['vector_version']}")
            print(f"Meets minimum: {result['meets_minimum']}")
            print(f"Total minutes: {result['total_minutes']:.0f}")
            print(f"\nVector (first 5 components):")
            print(result['vector'][:5])
            print(f"\nExplanation:")
            print(explain_role_vector(result))

        # Example 2: Get version info
        print("\n[Example 2] Version Information")
        print("-" * 40)

        version = get_role_vector_version()
        info = get_version_info(version)
        print(f"Current version: {version}")
        print(f"Dimensions: {info['dimensions']}")
        print(f"Released: {info['date']}")

        print("\n" + "=" * 80)

    finally:
        shutdown_db()
