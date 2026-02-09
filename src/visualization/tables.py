"""
Data Table Visualization - visualization/tables.py

RESPONSIBILITIES:
-----------------
Create sortable, filterable data tables for player comparisons and results.

CRITICAL RULES:
--------------
- ACCEPT PREPARED DATA ONLY - No computation
- NO BUSINESS LOGIC - Pure visualization
- RETURN DASH DATATABLE CONFIGS - Reusable across app
- NO DASH CALLBACKS - Just configuration functions

USE CASES:
---------
1. Player comparison tables
2. Similarity search results
3. Metric leaderboards
4. Sortable player stats
"""

from typing import Dict, List, Optional, Any
import pandas as pd


# ============================================================================
# PLAYER COMPARISON TABLE
# ============================================================================

def create_player_comparison_table(
    players_data: List[Dict],
    columns: List[Dict],
    sort_column: Optional[str] = None,
    sort_direction: str = 'desc',
    page_size: int = 10,
    style: Optional[str] = 'striped'
) -> Dict:
    """
    Create comparison table for multiple players.

    Args:
        players_data: List of player dicts with metrics
        columns: List of column definitions:
            [
                {'id': 'name', 'name': 'Player Name', 'type': 'text'},
                {'id': 'goals_per90', 'name': 'Goals/90', 'type': 'numeric'},
                ...
            ]
        sort_column: Initial sort column ID
        sort_direction: 'asc' or 'desc'
        page_size: Rows per page
        style: 'striped', 'default', or None

    Returns:
        Dict with DataTable configuration:
        {
            'data': [...],
            'columns': [...],
            'sort_action': 'native',
            'filter_action': 'native',
            ...
        }

    Example:
        >>> players = [
        ...     {'name': 'Haaland', 'goals_per90': 1.2, 'age': 23},
        ...     {'name': 'Kane', 'goals_per90': 0.9, 'age': 30}
        ... ]
        >>> columns = [
        ...     {'id': 'name', 'name': 'Player', 'type': 'text'},
        ...     {'id': 'goals_per90', 'name': 'Goals/90', 'type': 'numeric'},
        ...     {'id': 'age', 'name': 'Age', 'type': 'numeric'}
        ... ]
        >>> config = create_player_comparison_table(players, columns)
    """
    # Style configurations
    style_data_conditional = []

    if style == 'striped':
        style_data_conditional.append({
            'if': {'row_index': 'odd'},
            'backgroundColor': 'rgb(248, 248, 248)'
        })

    # Header style
    style_header = {
        'backgroundColor': 'rgb(230, 230, 230)',
        'fontWeight': 'bold',
        'textAlign': 'left',
        'border': '1px solid black'
    }

    # Cell style
    style_cell = {
        'textAlign': 'left',
        'padding': '8px',
        'border': '1px solid lightgray',
        'fontSize': '14px'
    }

    # Data style
    style_data = {
        'border': '1px solid lightgray'
    }

    # Build configuration
    config = {
        'data': players_data,
        'columns': columns,
        'sort_action': 'native',
        'sort_mode': 'multi',
        'filter_action': 'native',
        'page_action': 'native',
        'page_current': 0,
        'page_size': page_size,
        'style_header': style_header,
        'style_cell': style_cell,
        'style_data': style_data,
        'style_data_conditional': style_data_conditional
    }

    # Add initial sort
    if sort_column:
        config['sort_by'] = [{'column_id': sort_column, 'direction': sort_direction}]

    return config


# ============================================================================
# SIMILARITY RESULTS TABLE
# ============================================================================

def create_similarity_results_table(
    similarity_results: List[Dict],
    include_columns: Optional[List[str]] = None,
    page_size: int = 10
) -> Dict:
    """
    Create table for similarity search results.

    Args:
        similarity_results: List of similarity result dicts:
            [
                {
                    'player_name': 'Kane',
                    'similarity_score': 0.92,
                    'role_similarity': 0.95,
                    'stats_similarity': 0.88,
                    'position': 'FW',
                    'age': 30,
                    'total_minutes': 2700
                },
                ...
            ]
        include_columns: Optional list of column IDs to include
        page_size: Rows per page

    Returns:
        DataTable configuration dict

    Example:
        >>> results = [
        ...     {
        ...         'player_name': 'Kane',
        ...         'similarity_score': 0.92,
        ...         'position': 'FW'
        ...     }
        ... ]
        >>> config = create_similarity_results_table(results)
    """
    # Define all available columns
    all_columns = [
        {'id': 'rank', 'name': 'Rank', 'type': 'numeric'},
        {'id': 'player_name', 'name': 'Player', 'type': 'text'},
        {'id': 'similarity_score', 'name': 'Overall Similarity', 'type': 'numeric'},
        {'id': 'role_similarity', 'name': 'Role Similarity', 'type': 'numeric'},
        {'id': 'stats_similarity', 'name': 'Stats Similarity', 'type': 'numeric'},
        {'id': 'position', 'name': 'Position', 'type': 'text'},
        {'id': 'age', 'name': 'Age', 'type': 'numeric'},
        {'id': 'total_minutes', 'name': 'Minutes', 'type': 'numeric'}
    ]

    # Filter columns if specified
    if include_columns:
        columns = [col for col in all_columns if col['id'] in include_columns]
    else:
        columns = all_columns

    # Add rank to data
    data_with_rank = []
    for i, result in enumerate(similarity_results, 1):
        result_copy = result.copy()
        result_copy['rank'] = i
        data_with_rank.append(result_copy)

    # Conditional formatting for similarity scores
    style_data_conditional = [
        # Highlight high similarity (>= 0.9) in green
        {
            'if': {
                'filter_query': '{similarity_score} >= 0.9',
                'column_id': 'similarity_score'
            },
            'backgroundColor': '#d4edda',
            'color': '#155724',
            'fontWeight': 'bold'
        },
        # Medium similarity (0.8-0.9) in yellow
        {
            'if': {
                'filter_query': '{similarity_score} >= 0.8 && {similarity_score} < 0.9',
                'column_id': 'similarity_score'
            },
            'backgroundColor': '#fff3cd',
            'color': '#856404'
        },
        # Lower similarity (< 0.8) in orange
        {
            'if': {
                'filter_query': '{similarity_score} < 0.8',
                'column_id': 'similarity_score'
            },
            'backgroundColor': '#f8d7da',
            'color': '#721c24'
        },
        # Striped rows
        {
            'if': {'row_index': 'odd'},
            'backgroundColor': 'rgb(248, 248, 248)'
        }
    ]

    return {
        'data': data_with_rank,
        'columns': columns,
        'sort_action': 'native',
        'sort_by': [{'column_id': 'rank', 'direction': 'asc'}],
        'filter_action': 'native',
        'page_action': 'native',
        'page_current': 0,
        'page_size': page_size,
        'style_header': {
            'backgroundColor': 'rgb(30, 30, 30)',
            'color': 'white',
            'fontWeight': 'bold',
            'textAlign': 'left',
            'border': '1px solid black'
        },
        'style_cell': {
            'textAlign': 'left',
            'padding': '10px',
            'border': '1px solid lightgray',
            'fontSize': '14px',
            'minWidth': '100px'
        },
        'style_data': {
            'border': '1px solid lightgray'
        },
        'style_data_conditional': style_data_conditional,
        'style_cell_conditional': [
            {
                'if': {'column_id': 'similarity_score'},
                'textAlign': 'center',
                'fontWeight': 'bold'
            },
            {
                'if': {'column_id': 'rank'},
                'width': '60px',
                'textAlign': 'center'
            }
        ]
    }


# ============================================================================
# METRIC LEADERBOARD TABLE
# ============================================================================

def create_leaderboard_table(
    players_data: List[Dict],
    metric_id: str,
    metric_display_name: str,
    top_n: Optional[int] = None,
    include_percentiles: bool = True,
    page_size: int = 20
) -> Dict:
    """
    Create leaderboard table for a specific metric.

    Args:
        players_data: List of player dicts with metrics
        metric_id: Metric ID to rank by (e.g., 'goals_per90')
        metric_display_name: Display name for metric
        top_n: Optional limit to top N players
        include_percentiles: Whether to include percentile column
        page_size: Rows per page

    Returns:
        DataTable configuration dict

    Example:
        >>> players = [
        ...     {'name': 'Haaland', 'goals_per90': 1.2, 'percentile': 99},
        ...     {'name': 'Kane', 'goals_per90': 0.9, 'percentile': 95}
        ... ]
        >>> config = create_leaderboard_table(
        ...     players, 'goals_per90', 'Goals per 90'
        ... )
    """
    # Sort data by metric (descending)
    sorted_data = sorted(
        players_data,
        key=lambda x: x.get(metric_id, 0),
        reverse=True
    )

    # Limit to top N if specified
    if top_n:
        sorted_data = sorted_data[:top_n]

    # Add rank
    data_with_rank = []
    for i, player in enumerate(sorted_data, 1):
        player_copy = player.copy()
        player_copy['rank'] = i
        data_with_rank.append(player_copy)

    # Define columns
    columns = [
        {'id': 'rank', 'name': 'Rank', 'type': 'numeric'},
        {'id': 'name', 'name': 'Player', 'type': 'text'},
        {'id': metric_id, 'name': metric_display_name, 'type': 'numeric'},
    ]

    if include_percentiles and players_data and 'percentile' in players_data[0]:
        columns.append({'id': 'percentile', 'name': 'Percentile', 'type': 'numeric'})

    # Add common columns if present
    optional_columns = [
        {'id': 'position', 'name': 'Position', 'type': 'text'},
        {'id': 'age', 'name': 'Age', 'type': 'numeric'},
        {'id': 'team', 'name': 'Team', 'type': 'text'},
        {'id': 'total_minutes', 'name': 'Minutes', 'type': 'numeric'}
    ]

    if players_data:
        for col in optional_columns:
            if col['id'] in players_data[0]:
                columns.append(col)

    # Conditional formatting
    style_data_conditional = [
        # Top 3 in gold/silver/bronze
        {
            'if': {'filter_query': '{rank} = 1'},
            'backgroundColor': '#FFD700',  # Gold
            'fontWeight': 'bold'
        },
        {
            'if': {'filter_query': '{rank} = 2'},
            'backgroundColor': '#C0C0C0'  # Silver
        },
        {
            'if': {'filter_query': '{rank} = 3'},
            'backgroundColor': '#CD7F32'  # Bronze
        },
        # Striped rows
        {
            'if': {'row_index': 'odd'},
            'backgroundColor': 'rgb(248, 248, 248)'
        }
    ]

    return {
        'data': data_with_rank,
        'columns': columns,
        'sort_action': 'native',
        'sort_by': [{'column_id': 'rank', 'direction': 'asc'}],
        'filter_action': 'native',
        'page_action': 'native',
        'page_current': 0,
        'page_size': page_size,
        'style_header': {
            'backgroundColor': 'rgb(30, 30, 30)',
            'color': 'white',
            'fontWeight': 'bold',
            'textAlign': 'left',
            'border': '1px solid black'
        },
        'style_cell': {
            'textAlign': 'left',
            'padding': '10px',
            'border': '1px solid lightgray',
            'fontSize': '14px'
        },
        'style_data': {
            'border': '1px solid lightgray'
        },
        'style_data_conditional': style_data_conditional,
        'style_cell_conditional': [
            {
                'if': {'column_id': 'rank'},
                'width': '60px',
                'textAlign': 'center',
                'fontWeight': 'bold'
            },
            {
                'if': {'column_id': metric_id},
                'textAlign': 'center',
                'fontWeight': 'bold',
                'color': '#1f77b4'
            }
        ]
    }


# ============================================================================
# DETAILED METRICS TABLE
# ============================================================================

def create_detailed_metrics_table(
    player_data: Dict,
    metric_categories: Optional[List[str]] = None,
    page_size: int = 15
) -> Dict:
    """
    Create detailed table showing all metrics for a single player.

    Args:
        player_data: Player dict with:
            {
                'name': 'Player Name',
                'metrics': {
                    'goals_per90': {'value': 1.2, 'percentile': 95},
                    'assists_per90': {'value': 0.3, 'percentile': 70},
                    ...
                },
                'categories': ['Shooting', 'Passing', ...]
            }
        metric_categories: Optional list of categories to include
        page_size: Rows per page

    Returns:
        DataTable configuration dict
    """
    # Extract metrics
    metrics = player_data.get('metrics', {})

    # Build table data
    table_data = []
    for metric_id, metric_info in metrics.items():
        if isinstance(metric_info, dict):
            value = metric_info.get('value', 0)
            percentile = metric_info.get('percentile', None)
            category = metric_info.get('category', 'Other')
        else:
            value = metric_info
            percentile = None
            category = 'Other'

        # Skip if filtering by category
        if metric_categories and category not in metric_categories:
            continue

        row = {
            'metric': metric_id.replace('_', ' ').title(),
            'value': value,
            'category': category
        }

        if percentile is not None:
            row['percentile'] = percentile

        table_data.append(row)

    # Define columns
    columns = [
        {'id': 'category', 'name': 'Category', 'type': 'text'},
        {'id': 'metric', 'name': 'Metric', 'type': 'text'},
        {'id': 'value', 'name': 'Value', 'type': 'numeric'}
    ]

    if any('percentile' in row for row in table_data):
        columns.append({'id': 'percentile', 'name': 'Percentile', 'type': 'numeric'})

    # Conditional formatting by percentile
    style_data_conditional = [
        # Elite (90+)
        {
            'if': {
                'filter_query': '{percentile} >= 90',
                'column_id': 'percentile'
            },
            'backgroundColor': '#d4edda',
            'color': '#155724',
            'fontWeight': 'bold'
        },
        # Good (75-90)
        {
            'if': {
                'filter_query': '{percentile} >= 75 && {percentile} < 90',
                'column_id': 'percentile'
            },
            'backgroundColor': '#d1ecf1',
            'color': '#0c5460'
        },
        # Average (50-75)
        {
            'if': {
                'filter_query': '{percentile} >= 50 && {percentile} < 75',
                'column_id': 'percentile'
            },
            'backgroundColor': '#fff3cd',
            'color': '#856404'
        },
        # Below average (< 50)
        {
            'if': {
                'filter_query': '{percentile} < 50',
                'column_id': 'percentile'
            },
            'backgroundColor': '#f8d7da',
            'color': '#721c24'
        },
        # Striped rows
        {
            'if': {'row_index': 'odd'},
            'backgroundColor': 'rgb(248, 248, 248)'
        }
    ]

    return {
        'data': table_data,
        'columns': columns,
        'sort_action': 'native',
        'filter_action': 'native',
        'page_action': 'native',
        'page_current': 0,
        'page_size': page_size,
        'style_header': {
            'backgroundColor': 'rgb(30, 30, 30)',
            'color': 'white',
            'fontWeight': 'bold',
            'textAlign': 'left',
            'border': '1px solid black'
        },
        'style_cell': {
            'textAlign': 'left',
            'padding': '10px',
            'border': '1px solid lightgray',
            'fontSize': '14px'
        },
        'style_data': {
            'border': '1px solid lightgray'
        },
        'style_data_conditional': style_data_conditional
    }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    """
    Example usage of table functions.
    """

    print("=" * 80)
    print("DATA TABLE EXAMPLES")
    print("=" * 80)

    # Example 1: Player comparison table
    print("\n[Example 1] Player Comparison Table")

    players = [
        {
            'name': 'Haaland',
            'goals_per90': 1.2,
            'assists_per90': 0.3,
            'age': 23,
            'position': 'FW'
        },
        {
            'name': 'Kane',
            'goals_per90': 0.9,
            'assists_per90': 0.5,
            'age': 30,
            'position': 'FW'
        }
    ]

    columns = [
        {'id': 'name', 'name': 'Player', 'type': 'text'},
        {'id': 'goals_per90', 'name': 'Goals/90', 'type': 'numeric'},
        {'id': 'assists_per90', 'name': 'Assists/90', 'type': 'numeric'},
        {'id': 'age', 'name': 'Age', 'type': 'numeric'},
        {'id': 'position', 'name': 'Position', 'type': 'text'}
    ]

    config1 = create_player_comparison_table(players, columns)
    print(f"Created comparison table with {len(players)} players")

    # Example 2: Similarity results table
    print("\n[Example 2] Similarity Results Table")

    sim_results = [
        {
            'player_name': 'Kane',
            'similarity_score': 0.92,
            'role_similarity': 0.95,
            'stats_similarity': 0.88,
            'position': 'FW',
            'age': 30
        },
        {
            'player_name': 'Lewandowski',
            'similarity_score': 0.87,
            'role_similarity': 0.90,
            'stats_similarity': 0.83,
            'position': 'FW',
            'age': 35
        }
    ]

    config2 = create_similarity_results_table(sim_results)
    print(f"Created similarity results table with {len(sim_results)} players")

    # Example 3: Leaderboard table
    print("\n[Example 3] Metric Leaderboard")

    config3 = create_leaderboard_table(
        players,
        'goals_per90',
        'Goals per 90',
        top_n=10
    )
    print("Created leaderboard table")

    print("\n" + "=" * 80)
    print("All data tables created successfully!")
