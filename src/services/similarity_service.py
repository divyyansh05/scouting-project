"""
Similarity Service - services/similarity_service.py

RESPONSIBILITIES:
-----------------
Find players who are similar to a target player based on:
1. Role vectors (WHERE they operate) - from role_service.py
2. Statistical profiles (WHAT they do) - from metrics_service.py

CRITICAL DISTINCTIONS:
---------------------
- metrics_service.py: Computes WHAT players do (goals, passes, tackles)
- role_service.py: Computes WHERE players operate (position, zones)
- similarity_service.py: Finds HOW SIMILAR players are to each other

SIMILARITY APPROACH:
-------------------
Uses COSINE SIMILARITY to compare players:
- Cosine similarity ranges from -1 to 1
- 1 = identical vectors (same direction)
- 0 = orthogonal vectors (no similarity)
- -1 = opposite vectors (rarely occurs with our data)

WHY COSINE SIMILARITY?
---------------------
1. Scale-invariant: Measures direction, not magnitude
2. Works well with high-dimensional vectors
3. Interpretable: 0.9+ = very similar, 0.5-0.7 = somewhat similar
4. Standard in recommendation systems

CRITICAL RULES:
--------------
- NO STORAGE - Similarity computed on-demand
- NO VISUALIZATION - Returns data only, no charts
- DETERMINISTIC - Same inputs always produce same outputs
- IDENTITY CHECK - Player compared to self must have similarity = 1.0
- NO LLM USAGE - Pure mathematical computations
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from utils.db import fetch_dataframe
from services.role_service import build_role_vector, validate_role_vector
from services.metrics_service import compute_player_season_metrics

logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SimilarityResult:
    """Result of a similarity comparison."""
    player_id: int
    player_name: str
    similarity_score: float
    role_similarity: float
    stats_similarity: float
    combined_similarity: float
    position: str
    age: int
    total_minutes: float

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'player_id': self.player_id,
            'player_name': self.player_name,
            'similarity_score': self.similarity_score,
            'role_similarity': self.role_similarity,
            'stats_similarity': self.stats_similarity,
            'combined_similarity': self.combined_similarity,
            'position': self.position,
            'age': self.age,
            'total_minutes': self.total_minutes
        }


# ============================================================================
# POSITION COMPATIBILITY
# ============================================================================

# Define which positions are compatible for similarity comparisons
POSITION_COMPATIBILITY = {
    'GK': ['GK'],  # Goalkeepers only similar to goalkeepers
    'DF': ['DF', 'DM'],  # Defenders can be similar to defensive mids
    'DM': ['DF', 'DM', 'MF'],  # Defensive mids bridge defense and midfield
    'MF': ['DM', 'MF', 'AM'],  # Central midfielders
    'AM': ['MF', 'AM', 'FW'],  # Attacking mids bridge midfield and attack
    'FW': ['AM', 'FW'],  # Forwards can be similar to attacking mids

    # Specific sub-positions
    'CB': ['CB', 'DF', 'DM'],
    'LB': ['LB', 'LWB', 'DF'],
    'RB': ['RB', 'RWB', 'DF'],
    'LWB': ['LB', 'LWB', 'LM'],
    'RWB': ['RB', 'RWB', 'RM'],
    'CM': ['CM', 'MF', 'DM', 'AM'],
    'LM': ['LM', 'LW', 'MF'],
    'RM': ['RM', 'RW', 'MF'],
    'LW': ['LW', 'LM', 'AM', 'FW'],
    'RW': ['RW', 'RM', 'AM', 'FW'],
    'ST': ['ST', 'CF', 'FW'],
    'CF': ['CF', 'ST', 'FW', 'AM']
}


def are_positions_compatible(pos1: str, pos2: str) -> bool:
    """
    Check if two positions are compatible for similarity comparison.

    Args:
        pos1: Position 1 (e.g., "MF")
        pos2: Position 2 (e.g., "AM")

    Returns:
        True if positions are compatible for comparison

    Example:
        >>> are_positions_compatible("MF", "AM")
        True
        >>> are_positions_compatible("GK", "FW")
        False
    """
    # Default to basic position if not in compatibility map
    if pos1 not in POSITION_COMPATIBILITY:
        pos1 = pos1[:2] if len(pos1) > 2 else pos1

    compatible = POSITION_COMPATIBILITY.get(pos1, [pos1])
    return pos2 in compatible


# ============================================================================
# SIMILARITY COMPUTATION FUNCTIONS
# ============================================================================

def cosine_similarity(vector1: np.ndarray, vector2: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.

    FORMULA:
        cosine_similarity = (A · B) / (||A|| × ||B||)

        Where:
        - A · B is the dot product
        - ||A|| is the L2 norm (magnitude) of A

    Args:
        vector1: First vector (numpy array)
        vector2: Second vector (numpy array)

    Returns:
        Cosine similarity score (0 to 1 for our use case)

    Example:
        >>> v1 = np.array([1, 2, 3])
        >>> v2 = np.array([1, 2, 3])
        >>> cosine_similarity(v1, v2)
        1.0  # Identical vectors

        >>> v1 = np.array([1, 0])
        >>> v2 = np.array([0, 1])
        >>> cosine_similarity(v1, v2)
        0.0  # Orthogonal vectors
    """
    if vector1 is None or vector2 is None:
        return 0.0

    # Ensure same dimensions
    if len(vector1) != len(vector2):
        logger.warning(
            f"Vector dimension mismatch: {len(vector1)} vs {len(vector2)}"
        )
        return 0.0

    # Compute dot product
    dot_product = np.dot(vector1, vector2)

    # Compute magnitudes
    norm1 = np.linalg.norm(vector1)
    norm2 = np.linalg.norm(vector2)

    # Avoid division by zero
    if norm1 == 0 or norm2 == 0:
        return 0.0

    # Compute cosine similarity
    similarity = dot_product / (norm1 * norm2)

    # Clamp to [0, 1] range (should already be in this range for our data)
    similarity = np.clip(similarity, 0.0, 1.0)

    return float(similarity)


def euclidean_distance(vector1: np.ndarray, vector2: np.ndarray) -> float:
    """
    Compute Euclidean distance between two vectors.

    FORMULA:
        distance = sqrt(Σ(A_i - B_i)²)

    Args:
        vector1: First vector
        vector2: Second vector

    Returns:
        Euclidean distance (lower = more similar)

    Note:
        This is provided for reference but we use cosine similarity
        as the primary metric.
    """
    if vector1 is None or vector2 is None:
        return float('inf')

    if len(vector1) != len(vector2):
        return float('inf')

    return float(np.linalg.norm(vector1 - vector2))


def normalize_vector(vector: np.ndarray) -> np.ndarray:
    """
    Normalize a vector to unit length.

    FORMULA:
        normalized = vector / ||vector||

    Args:
        vector: Input vector

    Returns:
        Normalized vector
    """
    if vector is None:
        return None

    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector

    return vector / norm


# ============================================================================
# VECTOR CONSTRUCTION FOR SIMILARITY
# ============================================================================

def build_stats_vector(player_metrics: Dict, selected_metrics: List[str]) -> np.ndarray:
    """
    Build a statistical vector from player metrics.

    This converts the per90 metrics dict into a numpy array suitable
    for similarity comparison.

    Args:
        player_metrics: Dict from compute_player_season_metrics()
        selected_metrics: List of metric names to include

    Returns:
        Numpy array of metric values

    Example:
        >>> metrics = {'per90_metrics': {'goals_per90': 0.8, 'assists_per90': 0.3}}
        >>> vec = build_stats_vector(metrics, ['goals_per90', 'assists_per90'])
        >>> print(vec)
        [0.8, 0.3]
    """
    per90_metrics = player_metrics.get('per90_metrics', {})

    vector_components = []
    for metric_name in selected_metrics:
        value = per90_metrics.get(metric_name, 0.0)
        vector_components.append(value)

    return np.array(vector_components)


def build_combined_vector(
    role_vector: np.ndarray,
    stats_vector: np.ndarray,
    role_weight: float = 0.6,
    stats_weight: float = 0.4
) -> np.ndarray:
    """
    Combine role and stats vectors into a single vector.

    FORMULA:
        combined = [role_vector * role_weight, stats_vector * stats_weight]

        This concatenates the weighted vectors.

    Args:
        role_vector: Role vector (20 dimensions)
        stats_vector: Stats vector (N dimensions)
        role_weight: Weight for role similarity (default: 0.6)
        stats_weight: Weight for stats similarity (default: 0.4)

    Returns:
        Combined vector

    Example:
        >>> role = np.array([60, 25, 10])
        >>> stats = np.array([0.8, 0.3])
        >>> combined = build_combined_vector(role, stats, 0.6, 0.4)
        >>> print(len(combined))
        5  # 3 role + 2 stats
    """
    # Weight the vectors
    weighted_role = role_vector * role_weight
    weighted_stats = stats_vector * stats_weight

    # Concatenate
    combined = np.concatenate([weighted_role, weighted_stats])

    return combined


# ============================================================================
# CANDIDATE POOL FILTERING
# ============================================================================

def get_candidate_pool(
    season: str,
    position: Optional[str] = None,
    min_minutes: int = 450,
    league: Optional[str] = None,
    age_min: Optional[int] = None,
    age_max: Optional[int] = None,
    exclude_player_id: Optional[int] = None
) -> pd.DataFrame:
    """
    Get pool of candidate players for similarity comparison.

    Args:
        season: Season string (e.g., "2023-24")
        position: Optional position filter
        min_minutes: Minimum minutes played
        league: Optional league filter
        age_min: Minimum age
        age_max: Maximum age
        exclude_player_id: Player ID to exclude (usually the target player)

    Returns:
        DataFrame with candidate players
    """
    query = """
        SELECT DISTINCT
            p.player_id,
            p.name,
            p.position,
            p.age,
            p.current_team,
            SUM(ps.minutes_played) as total_minutes
        FROM players p
        JOIN player_match_stats ps ON p.player_id = ps.player_id
        JOIN matches m ON ps.match_id = m.match_id
        WHERE m.season = %s
    """

    params = [season]

    if league:
        query += " AND m.competition = %s"
        params.append(league)

    if age_min:
        query += " AND p.age >= %s"
        params.append(age_min)

    if age_max:
        query += " AND p.age <= %s"
        params.append(age_max)

    if exclude_player_id:
        query += " AND p.player_id != %s"
        params.append(exclude_player_id)

    query += """
        GROUP BY p.player_id, p.name, p.position, p.age, p.current_team
        HAVING SUM(ps.minutes_played) >= %s
    """
    params.append(min_minutes)

    # Position filtering (if specified)
    if position:
        query += " AND ("
        compatible_positions = POSITION_COMPATIBILITY.get(position, [position])
        position_clauses = ["p.position = %s" for _ in compatible_positions]
        query += " OR ".join(position_clauses)
        query += ")"
        params.extend(compatible_positions)

    query += " ORDER BY total_minutes DESC"

    df = fetch_dataframe(query, params=tuple(params))

    logger.info(
        f"Found {len(df)} candidate players for season {season}"
        + (f" in position {position}" if position else "")
    )

    return df


# ============================================================================
# MAIN SIMILARITY FUNCTIONS
# ============================================================================

def find_similar_players(
    player_id: int,
    season: str,
    n_similar: int = 10,
    filters: Optional[Dict] = None,
    role_weight: float = 0.6,
    stats_weight: float = 0.4,
    selected_metrics: Optional[List[str]] = None
) -> List[SimilarityResult]:
    """
    Find players most similar to the target player.

    This is the PRIMARY FUNCTION of the similarity service.

    ALGORITHM:
    1. Build role vector for target player
    2. Build stats vector for target player
    3. Get candidate pool (filtered by position, minutes, etc.)
    4. For each candidate:
       a. Build their role and stats vectors
       b. Compute cosine similarity
    5. Sort by similarity score
    6. Return top N

    Args:
        player_id: Target player identifier
        season: Season string (e.g., "2023-24")
        n_similar: Number of similar players to return
        filters: Optional filters dict:
            {
                'min_minutes': int,
                'league': str,
                'age_min': int,
                'age_max': int,
                'position': str
            }
        role_weight: Weight for role similarity (default: 0.6)
        stats_weight: Weight for stats similarity (default: 0.4)
        selected_metrics: List of metric names for stats vector
            If None, uses default set

    Returns:
        List of SimilarityResult objects, sorted by similarity (highest first)

    Example:
        >>> similar = find_similar_players(
        ...     player_id=123,
        ...     season="2023-24",
        ...     n_similar=10,
        ...     filters={'min_minutes': 900, 'position': 'FW'}
        ... )
        >>> for result in similar[:3]:
        ...     print(f"{result.player_name}: {result.similarity_score:.3f}")
        Player A: 0.945
        Player B: 0.912
        Player C: 0.887
    """
    logger.info(f"Finding similar players to {player_id} in season {season}")

    # Parse filters
    if filters is None:
        filters = {}

    min_minutes = filters.get('min_minutes', 450)
    league = filters.get('league')
    age_min = filters.get('age_min')
    age_max = filters.get('age_max')
    position_filter = filters.get('position')

    # Default metrics for stats vector
    if selected_metrics is None:
        selected_metrics = [
            'goals_per90',
            'assists_per90',
            'xg_per90',
            'shots_per90',
            'passes_completed_per90',
            'progressive_passes_per90',
            'key_passes_per90',
            'tackles_per90',
            'interceptions_per90',
            'dribbles_completed_per90'
        ]

    # Step 1: Build target player vectors
    logger.info("Building vectors for target player...")

    target_role_result = build_role_vector(player_id, season, min_minutes=min_minutes)
    target_metrics = compute_player_season_metrics(player_id, season, min_minutes=min_minutes)

    if target_role_result['vector'] is None:
        logger.error(f"Failed to build role vector for player {player_id}")
        return []

    if not target_metrics.get('meets_minimum', False):
        logger.warning(
            f"Target player {player_id} has insufficient minutes: "
            f"{target_metrics.get('aggregates', {}).get('total_minutes', 0)}"
        )

    target_role_vector = target_role_result['vector']
    target_stats_vector = build_stats_vector(target_metrics, selected_metrics)
    target_position = target_metrics['player_info']['position']

    # Override position filter with target player's position if not specified
    if position_filter is None:
        position_filter = target_position

    # Step 2: Get candidate pool
    logger.info("Getting candidate pool...")

    candidates_df = get_candidate_pool(
        season=season,
        position=position_filter,
        min_minutes=min_minutes,
        league=league,
        age_min=age_min,
        age_max=age_max,
        exclude_player_id=player_id  # Don't include target player
    )

    if candidates_df.empty:
        logger.warning("No candidates found matching filters")
        return []

    # Step 3: Compute similarities
    logger.info(f"Computing similarities for {len(candidates_df)} candidates...")

    similarities = []

    for _, candidate in candidates_df.iterrows():
        candidate_id = candidate['player_id']

        try:
            # Build candidate vectors
            candidate_role_result = build_role_vector(
                candidate_id, season, min_minutes=min_minutes
            )
            candidate_metrics = compute_player_season_metrics(
                candidate_id, season, min_minutes=min_minutes
            )

            if candidate_role_result['vector'] is None:
                continue

            candidate_role_vector = candidate_role_result['vector']
            candidate_stats_vector = build_stats_vector(
                candidate_metrics, selected_metrics
            )

            # Check position compatibility
            candidate_position = candidate_metrics['player_info']['position']
            if not are_positions_compatible(target_position, candidate_position):
                logger.debug(
                    f"Skipping {candidate['name']}: "
                    f"incompatible position {candidate_position}"
                )
                continue

            # Compute role similarity
            role_sim = cosine_similarity(target_role_vector, candidate_role_vector)

            # Compute stats similarity
            stats_sim = cosine_similarity(target_stats_vector, candidate_stats_vector)

            # Compute combined similarity
            combined_sim = (role_sim * role_weight) + (stats_sim * stats_weight)

            # Create result
            result = SimilarityResult(
                player_id=candidate_id,
                player_name=candidate['name'],
                similarity_score=combined_sim,
                role_similarity=role_sim,
                stats_similarity=stats_sim,
                combined_similarity=combined_sim,
                position=candidate_position,
                age=candidate['age'],
                total_minutes=candidate['total_minutes']
            )

            similarities.append(result)

        except Exception as e:
            logger.error(
                f"Failed to compute similarity for player {candidate_id}: {e}"
            )
            continue

    # Step 4: Sort by similarity
    similarities.sort(key=lambda x: x.similarity_score, reverse=True)

    # Step 5: Return top N
    top_n = similarities[:n_similar]

    logger.info(
        f"Found {len(similarities)} similar players, returning top {len(top_n)}"
    )

    return top_n


def similarity_score_breakdown(
    player1_id: int,
    player2_id: int,
    season: str,
    selected_metrics: Optional[List[str]] = None
) -> Dict:
    """
    Get detailed breakdown of similarity between two players.

    Args:
        player1_id: First player identifier
        player2_id: Second player identifier
        season: Season string
        selected_metrics: List of metric names for stats comparison

    Returns:
        Dict with detailed breakdown:
        {
            'overall_similarity': float,
            'role_similarity': float,
            'stats_similarity': float,
            'role_component_similarities': Dict,
            'stats_component_similarities': Dict,
            'player1_info': Dict,
            'player2_info': Dict
        }

    Example:
        >>> breakdown = similarity_score_breakdown(123, 456, "2023-24")
        >>> print(f"Overall: {breakdown['overall_similarity']:.3f}")
        >>> print(f"Role: {breakdown['role_similarity']:.3f}")
        >>> print(f"Stats: {breakdown['stats_similarity']:.3f}")
        Overall: 0.887
        Role: 0.912
        Stats: 0.845
    """
    if selected_metrics is None:
        selected_metrics = [
            'goals_per90', 'assists_per90', 'xg_per90',
            'shots_per90', 'passes_completed_per90',
            'progressive_passes_per90', 'key_passes_per90',
            'tackles_per90', 'interceptions_per90',
            'dribbles_completed_per90'
        ]

    # Build vectors for both players
    player1_role = build_role_vector(player1_id, season)
    player1_metrics = compute_player_season_metrics(player1_id, season)

    player2_role = build_role_vector(player2_id, season)
    player2_metrics = compute_player_season_metrics(player2_id, season)

    if player1_role['vector'] is None or player2_role['vector'] is None:
        return {'error': 'Failed to build role vectors'}

    # Compute overall similarities
    role_sim = cosine_similarity(player1_role['vector'], player2_role['vector'])

    player1_stats = build_stats_vector(player1_metrics, selected_metrics)
    player2_stats = build_stats_vector(player2_metrics, selected_metrics)
    stats_sim = cosine_similarity(player1_stats, player2_stats)

    overall_sim = (role_sim * 0.6) + (stats_sim * 0.4)

    # Component-wise similarities
    role_components = {}
    for i, component_name in enumerate(player1_role['components'].keys()):
        val1 = player1_role['components'][component_name]
        val2 = player2_role['components'][component_name]

        # Compute similarity for this component (simple normalized difference)
        if val1 == 0 and val2 == 0:
            component_sim = 1.0
        else:
            max_val = max(abs(val1), abs(val2), 1)
            diff = abs(val1 - val2)
            component_sim = 1.0 - (diff / max_val)

        role_components[component_name] = {
            'player1_value': val1,
            'player2_value': val2,
            'similarity': component_sim
        }

    # Stats component similarities
    stats_components = {}
    for i, metric_name in enumerate(selected_metrics):
        val1 = player1_stats[i] if i < len(player1_stats) else 0
        val2 = player2_stats[i] if i < len(player2_stats) else 0

        if val1 == 0 and val2 == 0:
            component_sim = 1.0
        else:
            max_val = max(abs(val1), abs(val2), 1)
            diff = abs(val1 - val2)
            component_sim = 1.0 - (diff / max_val)

        stats_components[metric_name] = {
            'player1_value': val1,
            'player2_value': val2,
            'similarity': component_sim
        }

    return {
        'overall_similarity': overall_sim,
        'role_similarity': role_sim,
        'stats_similarity': stats_sim,
        'role_component_similarities': role_components,
        'stats_component_similarities': stats_components,
        'player1_info': player1_metrics.get('player_info', {}),
        'player2_info': player2_metrics.get('player_info', {})
    }


# ============================================================================
# VALIDATION AND TESTING
# ============================================================================

def validate_similarity_score(similarity: float) -> bool:
    """
    Validate a similarity score.

    Args:
        similarity: Similarity score to validate

    Returns:
        True if valid (0 <= similarity <= 1)
    """
    return 0.0 <= similarity <= 1.0


def test_identity_similarity(player_id: int, season: str) -> bool:
    """
    Test that a player has similarity 1.0 with themselves.

    This is a critical sanity check for the similarity algorithm.

    Args:
        player_id: Player to test
        season: Season string

    Returns:
        True if identity check passes (similarity ≈ 1.0)

    Example:
        >>> passed = test_identity_similarity(123, "2023-24")
        >>> assert passed, "Identity check failed!"
    """
    # Build vectors
    role_result = build_role_vector(player_id, season)
    metrics = compute_player_season_metrics(player_id, season)

    if role_result['vector'] is None:
        logger.error("Failed to build vector for identity test")
        return False

    vector = role_result['vector']

    # Compute similarity with itself
    similarity = cosine_similarity(vector, vector)

    # Should be exactly 1.0
    if abs(similarity - 1.0) > 0.001:  # Allow tiny floating point error
        logger.error(
            f"Identity check FAILED: similarity = {similarity} (expected 1.0)"
        )
        return False

    logger.info(f"Identity check PASSED: similarity = {similarity}")
    return True


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    """
    Example usage of similarity service.
    """

    from utils.db import startup_db, shutdown_db
    startup_db()

    try:
        print("=" * 80)
        print("SIMILARITY SERVICE - EXAMPLE USAGE")
        print("=" * 80)

        # Example 1: Find similar players
        print("\n[Example 1] Find Similar Players")
        print("-" * 40)

        similar = find_similar_players(
            player_id=123,
            season="2023-24",
            n_similar=5,
            filters={'min_minutes': 900}
        )

        print(f"Found {len(similar)} similar players:\n")
        for i, result in enumerate(similar, 1):
            print(f"{i}. {result.player_name}")
            print(f"   Overall: {result.similarity_score:.3f}")
            print(f"   Role: {result.role_similarity:.3f}")
            print(f"   Stats: {result.stats_similarity:.3f}")
            print(f"   Position: {result.position}, Age: {result.age}")
            print()

        # Example 2: Detailed breakdown
        if len(similar) > 0:
            print("\n[Example 2] Similarity Breakdown")
            print("-" * 40)

            breakdown = similarity_score_breakdown(
                player1_id=123,
                player2_id=similar[0].player_id,
                season="2023-24"
            )

            print(f"Comparing Player 123 with {similar[0].player_name}")
            print(f"Overall: {breakdown['overall_similarity']:.3f}")
            print(f"Role: {breakdown['role_similarity']:.3f}")
            print(f"Stats: {breakdown['stats_similarity']:.3f}")

        # Example 3: Identity test
        print("\n[Example 3] Identity Test")
        print("-" * 40)

        passed = test_identity_similarity(123, "2023-24")
        if passed:
            print("Identity check PASSED")
        else:
            print("Identity check FAILED")

        print("\n" + "=" * 80)

    finally:
        shutdown_db()
