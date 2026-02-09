"""
Radar Chart Visualization - visualization/radar.py

RESPONSIBILITIES:
-----------------
Create radar (spider) charts for player metric comparison.

CRITICAL RULES:
--------------
- ACCEPT PREPARED DATA ONLY - No computation
- NO BUSINESS LOGIC - Pure visualization
- RETURN PLOTLY FIGURES - Reusable across app
- NO DASH CALLBACKS - Just functions that return figures

ARCHITECTURE:
------------
    Pre-computed data (from services/)
        |
    create_radar_chart(data)
        |
    Plotly figure object
        |
    Display in Dash (later)

USE CASES:
---------
1. Single player profile radar
2. Multi-player comparison radar
3. Player vs role template overlay
4. Position-specific metric radars
"""

import plotly.graph_objects as go
import numpy as np
from typing import Dict, List, Optional, Tuple


# ============================================================================
# COLOR SCHEMES
# ============================================================================

DEFAULT_COLORS = [
    '#1f77b4',  # Blue
    '#ff7f0e',  # Orange
    '#2ca02c',  # Green
    '#d62728',  # Red
    '#9467bd',  # Purple
    '#8c564b',  # Brown
    '#e377c2',  # Pink
    '#7f7f7f',  # Gray
    '#bcbd22',  # Olive
    '#17becf'   # Cyan
]


# ============================================================================
# SINGLE PLAYER RADAR
# ============================================================================

def create_player_radar(
    player_name: str,
    metrics: Dict[str, float],
    categories: List[str],
    title: Optional[str] = None,
    fill_color: str = '#1f77b4',
    line_color: str = '#1f77b4',
    height: int = 500,
    width: int = 500
) -> go.Figure:
    """
    Create radar chart for a single player.

    Args:
        player_name: Player name for legend
        metrics: Dict mapping metric_id to percentile value (0-100)
        categories: List of metric display names (in order)
        title: Optional chart title
        fill_color: Fill color for radar area
        line_color: Line color for radar perimeter
        height: Chart height in pixels
        width: Chart width in pixels

    Returns:
        Plotly Figure object

    Example:
        >>> metrics = {
        ...     'goals_per90': 85,
        ...     'assists_per90': 72,
        ...     'xg_per90': 88,
        ...     'shots_per90': 80,
        ...     'key_passes_per90': 75
        ... }
        >>> categories = ['Goals', 'Assists', 'xG', 'Shots', 'Key Passes']
        >>> fig = create_player_radar('Erling Haaland', metrics, categories)
    """
    # Extract values in category order
    # Categories should match the keys in metrics dict
    metric_keys = list(metrics.keys())
    values = [metrics[key] for key in metric_keys]

    # Close the radar (duplicate first value at end)
    values_closed = values + [values[0]]
    categories_closed = categories + [categories[0]]

    # Create figure
    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill='toself',
        fillcolor=fill_color,
        line=dict(color=line_color, width=2),
        opacity=0.6,
        name=player_name
    ))

    # Update layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickmode='linear',
                tick0=0,
                dtick=20,
                gridcolor='lightgray'
            ),
            angularaxis=dict(
                gridcolor='lightgray'
            )
        ),
        showlegend=True,
        title=title or f"{player_name} - Metric Percentiles",
        height=height,
        width=width,
        font=dict(size=12)
    )

    return fig


# ============================================================================
# MULTI-PLAYER COMPARISON RADAR
# ============================================================================

def create_comparison_radar(
    players_data: List[Dict],
    categories: List[str],
    title: Optional[str] = None,
    height: int = 600,
    width: int = 600,
    show_legend: bool = True
) -> go.Figure:
    """
    Create radar chart comparing multiple players.

    Args:
        players_data: List of dicts, each with:
            {
                'name': 'Player Name',
                'metrics': {'metric_id': percentile_value, ...},
                'color': '#hex' (optional)
            }
        categories: List of metric display names
        title: Optional chart title
        height: Chart height
        width: Chart width
        show_legend: Whether to show legend

    Returns:
        Plotly Figure object

    Example:
        >>> players = [
        ...     {
        ...         'name': 'Haaland',
        ...         'metrics': {'goals_per90': 95, 'assists_per90': 60}
        ...     },
        ...     {
        ...         'name': 'Kane',
        ...         'metrics': {'goals_per90': 88, 'assists_per90': 82}
        ...     }
        ... ]
        >>> categories = ['Goals per 90', 'Assists per 90']
        >>> fig = create_comparison_radar(players, categories)
    """
    fig = go.Figure()

    # Add trace for each player
    for i, player in enumerate(players_data):
        player_name = player['name']
        metrics = player['metrics']
        color = player.get('color', DEFAULT_COLORS[i % len(DEFAULT_COLORS)])

        # Extract values
        metric_keys = list(metrics.keys())
        values = [metrics[key] for key in metric_keys]

        # Close the radar
        values_closed = values + [values[0]]
        categories_closed = categories + [categories[0]]

        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=categories_closed,
            fill='toself',
            fillcolor=color,
            line=dict(color=color, width=2),
            opacity=0.4,
            name=player_name
        ))

    # Update layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickmode='linear',
                tick0=0,
                dtick=20,
                gridcolor='lightgray'
            ),
            angularaxis=dict(
                gridcolor='lightgray'
            )
        ),
        showlegend=show_legend,
        title=title or "Player Comparison",
        height=height,
        width=width,
        font=dict(size=12),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.1
        )
    )

    return fig


# ============================================================================
# PLAYER VS ROLE TEMPLATE RADAR
# ============================================================================

def create_player_vs_template_radar(
    player_name: str,
    player_metrics: Dict[str, float],
    template_name: str,
    template_values: Dict[str, float],
    categories: List[str],
    title: Optional[str] = None,
    height: int = 600,
    width: int = 600
) -> go.Figure:
    """
    Create radar comparing player to role template.

    Shows how well a player matches a specific role profile.

    Args:
        player_name: Player name
        player_metrics: Player's metric percentiles
        template_name: Role template name (e.g., "Defensive Midfielder")
        template_values: Template's ideal percentile values
        categories: Metric display names
        title: Optional chart title
        height: Chart height
        width: Chart width

    Returns:
        Plotly Figure object

    Example:
        >>> player_metrics = {'tackles_per90': 88, 'interceptions_per90': 85}
        >>> template_values = {'tackles_per90': 90, 'interceptions_per90': 90}
        >>> fig = create_player_vs_template_radar(
        ...     'Rodri', player_metrics,
        ...     'Defensive Midfielder', template_values,
        ...     ['Tackles per 90', 'Interceptions per 90']
        ... )
    """
    fig = go.Figure()

    # Extract player values
    player_keys = list(player_metrics.keys())
    player_values = [player_metrics[key] for key in player_keys]
    player_values_closed = player_values + [player_values[0]]
    categories_closed = categories + [categories[0]]

    # Extract template values
    template_vals = [template_values[key] for key in player_keys]
    template_vals_closed = template_vals + [template_vals[0]]

    # Add template (dashed line)
    fig.add_trace(go.Scatterpolar(
        r=template_vals_closed,
        theta=categories_closed,
        fill='toself',
        fillcolor='rgba(150, 150, 150, 0.2)',
        line=dict(color='gray', width=2, dash='dash'),
        opacity=0.5,
        name=f"{template_name} (Template)"
    ))

    # Add player (solid line)
    fig.add_trace(go.Scatterpolar(
        r=player_values_closed,
        theta=categories_closed,
        fill='toself',
        fillcolor='rgba(31, 119, 180, 0.3)',
        line=dict(color='#1f77b4', width=3),
        opacity=0.7,
        name=player_name
    ))

    # Update layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickmode='linear',
                tick0=0,
                dtick=20,
                gridcolor='lightgray'
            ),
            angularaxis=dict(
                gridcolor='lightgray'
            )
        ),
        showlegend=True,
        title=title or f"{player_name} vs {template_name} Template",
        height=height,
        width=width,
        font=dict(size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )

    return fig


# ============================================================================
# POSITION-SPECIFIC RADAR
# ============================================================================

def create_position_radar(
    player_name: str,
    player_metrics: Dict[str, float],
    position: str,
    title: Optional[str] = None,
    height: int = 500,
    width: int = 500
) -> go.Figure:
    """
    Create position-specific radar chart with appropriate metrics.

    Automatically selects relevant metrics based on position.

    Args:
        player_name: Player name
        player_metrics: All player metrics (relevant ones will be selected)
        position: Position code (FW, MF, DF, GK)
        title: Optional chart title
        height: Chart height
        width: Chart width

    Returns:
        Plotly Figure object

    Example:
        >>> all_metrics = {
        ...     'goals_per90': 85,
        ...     'assists_per90': 70,
        ...     'tackles_per90': 45,
        ...     'passes_completed_per90': 88
        ... }
        >>> fig = create_position_radar('Haaland', all_metrics, 'FW')
    """
    # Define position-specific metric sets
    position_metrics = {
        'FW': {
            'metrics': [
                'goals_per90', 'xg_per90', 'shots_per90',
                'assists_per90', 'key_passes_per90',
                'dribbles_completed_per90'
            ],
            'labels': [
                'Goals', 'xG', 'Shots',
                'Assists', 'Key Passes',
                'Dribbles'
            ]
        },
        'MF': {
            'metrics': [
                'passes_completed_per90', 'progressive_passes_per90',
                'key_passes_per90', 'tackles_per90',
                'interceptions_per90', 'dribbles_completed_per90'
            ],
            'labels': [
                'Passes', 'Progressive Passes',
                'Key Passes', 'Tackles',
                'Interceptions', 'Dribbles'
            ]
        },
        'DF': {
            'metrics': [
                'tackles_per90', 'interceptions_per90',
                'blocks_per90', 'aerial_duels_won_pct',
                'pass_completion_pct', 'progressive_passes_per90'
            ],
            'labels': [
                'Tackles', 'Interceptions',
                'Blocks', 'Aerial Duels %',
                'Pass Accuracy', 'Progressive Passes'
            ]
        },
        'GK': {
            'metrics': [
                'saves_per90', 'save_pct',
                'clean_sheets_per90', 'psxg_per90',
                'pass_completion_pct', 'long_passes_per90'
            ],
            'labels': [
                'Saves', 'Save %',
                'Clean Sheets', 'PSxG',
                'Pass Accuracy', 'Long Passes'
            ]
        }
    }

    # Get metrics for position (default to MF if unknown)
    pos_config = position_metrics.get(position, position_metrics['MF'])
    metric_keys = pos_config['metrics']
    categories = pos_config['labels']

    # Filter to available metrics
    filtered_metrics = {}
    filtered_categories = []
    for metric_key, category in zip(metric_keys, categories):
        if metric_key in player_metrics:
            filtered_metrics[metric_key] = player_metrics[metric_key]
            filtered_categories.append(category)

    if not filtered_metrics:
        # Fallback to all available metrics
        filtered_metrics = player_metrics
        filtered_categories = list(player_metrics.keys())

    # Create radar
    return create_player_radar(
        player_name=player_name,
        metrics=filtered_metrics,
        categories=filtered_categories,
        title=title or f"{player_name} - {position} Metrics",
        height=height,
        width=width
    )


# ============================================================================
# RADAR WITH PERCENTILE BANDS
# ============================================================================

def create_radar_with_bands(
    player_name: str,
    metrics: Dict[str, float],
    categories: List[str],
    title: Optional[str] = None,
    height: int = 600,
    width: int = 600,
    show_bands: bool = True
) -> go.Figure:
    """
    Create radar with percentile bands (elite, good, average, poor).

    Args:
        player_name: Player name
        metrics: Player metric percentiles
        categories: Metric display names
        title: Optional chart title
        height: Chart height
        width: Chart width
        show_bands: Whether to show percentile bands

    Returns:
        Plotly Figure object
    """
    fig = go.Figure()

    # Extract values
    metric_keys = list(metrics.keys())
    values = [metrics[key] for key in metric_keys]
    values_closed = values + [values[0]]
    categories_closed = categories + [categories[0]]

    # Add percentile bands if requested
    if show_bands:
        bands = [
            {'range': [0, 25], 'color': 'rgba(255, 100, 100, 0.1)', 'name': 'Bottom 25%'},
            {'range': [25, 50], 'color': 'rgba(255, 200, 100, 0.1)', 'name': '25-50%'},
            {'range': [50, 75], 'color': 'rgba(200, 255, 100, 0.1)', 'name': '50-75%'},
            {'range': [75, 100], 'color': 'rgba(100, 255, 100, 0.1)', 'name': 'Top 25%'}
        ]

        for band in bands:
            band_values = [band['range'][1]] * (len(categories) + 1)
            fig.add_trace(go.Scatterpolar(
                r=band_values,
                theta=categories_closed,
                fill='toself',
                fillcolor=band['color'],
                line=dict(width=0),
                showlegend=False,
                hoverinfo='skip'
            ))

    # Add player trace
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill='toself',
        fillcolor='rgba(31, 119, 180, 0.5)',
        line=dict(color='#1f77b4', width=3),
        name=player_name
    ))

    # Update layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickmode='array',
                tickvals=[25, 50, 75, 100],
                ticktext=['25%', '50%', '75%', '100%'],
                gridcolor='lightgray'
            ),
            angularaxis=dict(
                gridcolor='lightgray'
            )
        ),
        showlegend=True,
        title=title or f"{player_name} - Percentile Bands",
        height=height,
        width=width,
        font=dict(size=12)
    )

    return fig


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    """
    Example usage of radar chart functions.
    """

    print("=" * 80)
    print("RADAR CHART EXAMPLES")
    print("=" * 80)

    # Example 1: Single player radar
    print("\n[Example 1] Single Player Radar")

    player_metrics = {
        'goals_per90': 95,
        'assists_per90': 72,
        'xg_per90': 92,
        'shots_per90': 88,
        'key_passes_per90': 75,
        'dribbles_completed_per90': 68
    }

    categories = [
        'Goals per 90',
        'Assists per 90',
        'xG per 90',
        'Shots per 90',
        'Key Passes per 90',
        'Dribbles per 90'
    ]

    fig1 = create_player_radar('Erling Haaland', player_metrics, categories)
    # fig1.show()  # Uncomment to display
    print("Created single player radar")

    # Example 2: Multi-player comparison
    print("\n[Example 2] Multi-Player Comparison")

    players_data = [
        {
            'name': 'Haaland',
            'metrics': player_metrics,
            'color': '#1f77b4'
        },
        {
            'name': 'Kane',
            'metrics': {
                'goals_per90': 88,
                'assists_per90': 85,
                'xg_per90': 87,
                'shots_per90': 82,
                'key_passes_per90': 90,
                'dribbles_completed_per90': 65
            },
            'color': '#ff7f0e'
        }
    ]

    fig2 = create_comparison_radar(players_data, categories)
    # fig2.show()
    print("Created comparison radar")

    # Example 3: Player vs template
    print("\n[Example 3] Player vs Role Template")

    template_values = {
        'goals_per90': 90,
        'assists_per90': 80,
        'xg_per90': 90,
        'shots_per90': 85,
        'key_passes_per90': 85,
        'dribbles_completed_per90': 75
    }

    fig3 = create_player_vs_template_radar(
        'Haaland',
        player_metrics,
        'Elite Striker',
        template_values,
        categories
    )
    # fig3.show()
    print("Created player vs template radar")

    print("\n" + "=" * 80)
    print("All radar charts created successfully!")
