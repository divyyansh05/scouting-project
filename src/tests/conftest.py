"""
Pytest Configuration and Fixtures

Provides shared fixtures for all tests including:
- Mock database connections
- Sample player data
- Metrics registry fixtures
- Role vector fixtures
"""

import pytest
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from unittest.mock import Mock, MagicMock


# ============================================================
# Sample Data Fixtures
# ============================================================

@pytest.fixture
def sample_player_data() -> pd.DataFrame:
    """
    Provides sample player data for testing.

    Returns:
        DataFrame with realistic player statistics
    """
    return pd.DataFrame({
        'player_id': [1, 2, 3, 4, 5],
        'player_name': ['Player A', 'Player B', 'Player C', 'Player D', 'Player E'],
        'team_name': ['Team 1', 'Team 1', 'Team 2', 'Team 2', 'Team 3'],
        'competition': ['Premier League', 'Premier League', 'La Liga', 'La Liga', 'Bundesliga'],
        'season': ['2023/2024'] * 5,
        'position': ['Central Midfield', 'Central Midfield', 'Attacking Midfield', 'Centre-Forward', 'Left Winger'],
        'age': [25, 28, 23, 30, 22],
        'minutes_played': [2500, 2800, 2200, 3000, 1800],
        'goals': [5, 3, 8, 15, 10],
        'assists': [8, 12, 10, 5, 7],
        'xg': [4.5, 2.8, 7.2, 14.0, 9.5],
        'xa': [7.5, 11.0, 9.0, 4.5, 6.5],
        'passes_completed': [1800, 2100, 1500, 800, 1200],
        'pass_accuracy': [0.88, 0.91, 0.85, 0.78, 0.82],
        'progressive_passes': [120, 150, 180, 50, 100],
        'progressive_carries': [80, 60, 120, 100, 150],
        'tackles_won': [45, 55, 30, 20, 25],
        'interceptions': [40, 50, 25, 15, 20],
        'aerial_duels_won': [30, 25, 20, 60, 15],
        'dribbles_completed': [40, 25, 60, 45, 80],
    })


@pytest.fixture
def sample_role_vectors() -> Dict[int, np.ndarray]:
    """
    Provides sample role vectors for testing.

    Role vectors are 20-dimensional capturing:
    - Position encoding (dims 0-3)
    - Spread metrics (dims 4-7)
    - Zone preferences (dims 8-15)
    - Pass directions (dims 16-19)

    Returns:
        Dictionary mapping player_id to role vector
    """
    return {
        1: np.array([0.8, 0.2, 0.0, 0.0,  # Central Midfield
                     0.6, 0.7, 0.5, 0.4,  # Spread
                     0.3, 0.6, 0.8, 0.5, 0.4, 0.3, 0.2, 0.1,  # Zones
                     0.4, 0.5, 0.6, 0.5]),  # Pass directions
        2: np.array([0.7, 0.3, 0.0, 0.0,  # Similar CM
                     0.5, 0.8, 0.6, 0.3,
                     0.4, 0.7, 0.7, 0.4, 0.3, 0.4, 0.2, 0.1,
                     0.5, 0.4, 0.5, 0.6]),
        3: np.array([0.5, 0.5, 0.3, 0.0,  # Attacking Mid
                     0.7, 0.6, 0.8, 0.5,
                     0.2, 0.4, 0.6, 0.8, 0.7, 0.5, 0.3, 0.2,
                     0.3, 0.6, 0.7, 0.4]),
        4: np.array([0.2, 0.3, 0.7, 0.5,  # Centre-Forward
                     0.4, 0.3, 0.9, 0.6,
                     0.1, 0.2, 0.4, 0.6, 0.9, 0.8, 0.5, 0.3,
                     0.2, 0.4, 0.8, 0.3]),
        5: np.array([0.3, 0.2, 0.5, 0.8,  # Left Winger
                     0.8, 0.5, 0.7, 0.9,
                     0.1, 0.3, 0.5, 0.7, 0.6, 0.8, 0.9, 0.4,
                     0.6, 0.3, 0.5, 0.7]),
    }


@pytest.fixture
def sample_metrics_registry() -> Dict[str, Any]:
    """
    Provides sample metrics registry for testing.

    Returns:
        Dictionary with metric definitions
    """
    return {
        'version': '1.0.0',
        'metrics': {
            'goals': {
                'display_name': 'Goals',
                'category': 'attacking',
                'aggregation': 'sum',
                'per_90': True,
                'description': 'Total goals scored',
                'unit': 'count'
            },
            'assists': {
                'display_name': 'Assists',
                'category': 'attacking',
                'aggregation': 'sum',
                'per_90': True,
                'description': 'Total assists',
                'unit': 'count'
            },
            'xg': {
                'display_name': 'Expected Goals (xG)',
                'category': 'attacking',
                'aggregation': 'sum',
                'per_90': True,
                'description': 'Expected goals based on shot quality',
                'unit': 'xG'
            },
            'pass_accuracy': {
                'display_name': 'Pass Accuracy',
                'category': 'passing',
                'aggregation': 'mean',
                'per_90': False,
                'description': 'Percentage of successful passes',
                'unit': 'percentage'
            },
            'tackles_won': {
                'display_name': 'Tackles Won',
                'category': 'defending',
                'aggregation': 'sum',
                'per_90': True,
                'description': 'Successful tackles',
                'unit': 'count'
            },
        },
        'forbidden_metrics': [
            'made_up_stat',
            'hallucinated_metric',
            'fake_xg',
        ],
        'categories': ['attacking', 'passing', 'defending', 'possession', 'physical'],
    }


@pytest.fixture
def sample_stats_vectors() -> Dict[int, np.ndarray]:
    """
    Provides sample normalized stats vectors for testing.

    Returns:
        Dictionary mapping player_id to stats vector
    """
    return {
        1: np.array([0.33, 0.67, 0.32, 0.68, 0.88, 0.60, 0.50, 0.55, 0.45, 0.50]),
        2: np.array([0.20, 1.00, 0.20, 1.00, 0.91, 0.75, 0.40, 0.69, 0.63, 0.31]),
        3: np.array([0.53, 0.83, 0.51, 0.82, 0.85, 0.90, 0.80, 0.31, 0.31, 0.75]),
        4: np.array([1.00, 0.42, 1.00, 0.41, 0.78, 0.25, 0.67, 0.25, 0.19, 0.56]),
        5: np.array([0.67, 0.58, 0.68, 0.59, 0.82, 0.50, 1.00, 0.31, 0.25, 1.00]),
    }


# ============================================================
# Mock Fixtures
# ============================================================

@pytest.fixture
def mock_db_connection():
    """
    Provides a mock database connection for testing.

    Returns:
        Mock database connection object
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
    return mock_conn


@pytest.fixture
def mock_connection_pool(mock_db_connection):
    """
    Provides a mock connection pool for testing.

    Returns:
        Mock connection pool object
    """
    mock_pool = MagicMock()
    mock_pool.getconn.return_value = mock_db_connection
    mock_pool.putconn = Mock()
    return mock_pool


@pytest.fixture
def mock_llm_client():
    """
    Provides a mock LLM client for testing.

    Returns:
        Mock LLM client object
    """
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"metrics": ["goals", "assists"], "filters": {}}')]
    mock_client.messages.create.return_value = mock_response
    return mock_client


# ============================================================
# Position Fixtures
# ============================================================

@pytest.fixture
def position_groups() -> Dict[str, List[str]]:
    """
    Provides position group mappings for testing.

    Returns:
        Dictionary mapping position groups to positions
    """
    return {
        'goalkeeper': ['Goalkeeper'],
        'defender': ['Centre-Back', 'Left-Back', 'Right-Back'],
        'midfielder': ['Central Midfield', 'Defensive Midfield', 'Attacking Midfield'],
        'winger': ['Left Winger', 'Right Winger'],
        'forward': ['Centre-Forward', 'Second Striker'],
    }


@pytest.fixture
def position_compatibility() -> Dict[str, List[str]]:
    """
    Provides position compatibility mapping for testing.

    Returns:
        Dictionary mapping positions to compatible positions
    """
    return {
        'Central Midfield': ['Central Midfield', 'Defensive Midfield', 'Attacking Midfield'],
        'Attacking Midfield': ['Attacking Midfield', 'Central Midfield', 'Second Striker', 'Left Winger', 'Right Winger'],
        'Centre-Forward': ['Centre-Forward', 'Second Striker'],
        'Left Winger': ['Left Winger', 'Right Winger', 'Attacking Midfield'],
        'Right Winger': ['Right Winger', 'Left Winger', 'Attacking Midfield'],
        'Defensive Midfield': ['Defensive Midfield', 'Central Midfield', 'Centre-Back'],
        'Centre-Back': ['Centre-Back', 'Defensive Midfield'],
        'Left-Back': ['Left-Back', 'Left Winger'],
        'Right-Back': ['Right-Back', 'Right Winger'],
        'Goalkeeper': ['Goalkeeper'],
    }


# ============================================================
# Query Fixtures
# ============================================================

@pytest.fixture
def sample_parsed_queries() -> List[Dict[str, Any]]:
    """
    Provides sample parsed queries for testing.

    Returns:
        List of parsed query dictionaries
    """
    return [
        {
            'query_type': 'metric_search',
            'metrics': ['goals', 'xg'],
            'filters': {'position': 'Centre-Forward', 'min_minutes': 900},
            'sort_by': 'goals',
            'sort_order': 'desc',
            'limit': 20,
        },
        {
            'query_type': 'similarity_search',
            'player_name': 'Player A',
            'filters': {'competition': 'Premier League'},
            'limit': 10,
        },
        {
            'query_type': 'comparison',
            'players': ['Player A', 'Player B'],
            'metrics': ['goals', 'assists', 'xg', 'xa'],
        },
    ]


@pytest.fixture
def sample_natural_language_queries() -> List[str]:
    """
    Provides sample natural language queries for testing.

    Returns:
        List of natural language query strings
    """
    return [
        "Show me the top strikers by goals per 90",
        "Find players similar to Kevin De Bruyne",
        "Compare Haaland and Kane on attacking metrics",
        "Which midfielders have the best progressive passes?",
        "Top 10 young wingers under 23 with most assists",
    ]


# ============================================================
# Utility Functions
# ============================================================

def create_test_dataframe(n_players: int = 10, seed: int = 42) -> pd.DataFrame:
    """
    Creates a test DataFrame with random player data.

    Args:
        n_players: Number of players to generate
        seed: Random seed for reproducibility

    Returns:
        DataFrame with random player data
    """
    np.random.seed(seed)

    positions = ['Central Midfield', 'Centre-Forward', 'Left Winger', 'Centre-Back', 'Goalkeeper']
    teams = ['Team A', 'Team B', 'Team C', 'Team D', 'Team E']

    return pd.DataFrame({
        'player_id': range(1, n_players + 1),
        'player_name': [f'Player {i}' for i in range(1, n_players + 1)],
        'team_name': np.random.choice(teams, n_players),
        'position': np.random.choice(positions, n_players),
        'age': np.random.randint(18, 35, n_players),
        'minutes_played': np.random.randint(500, 3500, n_players),
        'goals': np.random.randint(0, 20, n_players),
        'assists': np.random.randint(0, 15, n_players),
        'xg': np.random.uniform(0, 18, n_players).round(2),
        'xa': np.random.uniform(0, 12, n_players).round(2),
    })
