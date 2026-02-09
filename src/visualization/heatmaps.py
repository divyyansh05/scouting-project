"""
Heatmap Visualization - visualization/heatmaps.py

RESPONSIBILITIES:
-----------------
Create heatmaps for similarity matrices, role distributions, and correlations.

CRITICAL RULES:
--------------
- ACCEPT PREPARED DATA ONLY - No computation
- NO BUSINESS LOGIC - Pure visualization
- RETURN PLOTLY FIGURES - Reusable across app
- NO DASH CALLBACKS - Just functions that return figures

USE CASES:
---------
1. Similarity matrix between players
2. Role distribution heatmap
3. Metric correlation matrix
4. Performance across competitions
"""

import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from typing import Dict, List, Optional


# ============================================================================
# SIMILARITY MATRIX HEATMAP
# ============================================================================

def create_similarity_matrix(
    player_names: List[str],
    similarity_matrix: List[List[float]],
    title: Optional[str] = None,
    height: int = 600,
    width: int = 700,
    colorscale: str = 'RdYlGn'
) -> go.Figure:
    """
    Create heatmap showing pairwise similarity between players.

    Args:
        player_names: List of player names
        similarity_matrix: 2D list/array of similarity scores (0-1)
        title: Chart title
        height: Chart height
        width: Chart width
        colorscale: Plotly colorscale name

    Returns:
        Plotly Figure object

    Example:
        >>> names = ['Haaland', 'Kane', 'Lewandowski']
        >>> matrix = [
        ...     [1.00, 0.85, 0.78],
        ...     [0.85, 1.00, 0.82],
        ...     [0.78, 0.82, 1.00]
        ... ]
        >>> fig = create_similarity_matrix(names, matrix)
    """
    # Create hover text
    hover_text = []
    for i, name1 in enumerate(player_names):
        row = []
        for j, name2 in enumerate(player_names):
            similarity = similarity_matrix[i][j]
            text = f"{name1} vs {name2}<br>Similarity: {similarity:.3f}"
            row.append(text)
        hover_text.append(row)

    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=similarity_matrix,
        x=player_names,
        y=player_names,
        colorscale=colorscale,
        zmin=0,
        zmax=1,
        text=hover_text,
        hoverinfo='text',
        colorbar=dict(title="Similarity")
    ))

    # Add annotations (similarity scores on cells)
    annotations = []
    for i in range(len(player_names)):
        for j in range(len(player_names)):
            annotations.append(
                dict(
                    x=j,
                    y=i,
                    text=f"{similarity_matrix[i][j]:.2f}",
                    showarrow=False,
                    font=dict(
                        color='white' if similarity_matrix[i][j] < 0.5 else 'black',
                        size=10
                    )
                )
            )

    # Update layout
    fig.update_layout(
        title=title or "Player Similarity Matrix",
        xaxis=dict(title="", side='bottom'),
        yaxis=dict(title=""),
        height=height,
        width=width,
        annotations=annotations
    )

    return fig


# ============================================================================
# ROLE DISTRIBUTION HEATMAP
# ============================================================================

def create_role_heatmap(
    player_names: List[str],
    role_components: Dict[str, List[float]],
    title: Optional[str] = None,
    height: int = 600,
    width: int = 800,
    colorscale: str = 'Blues'
) -> go.Figure:
    """
    Create heatmap showing role vector components across players.

    Args:
        player_names: List of player names
        role_components: Dict mapping component_name -> list of values
            e.g., {
                'avg_x': [65, 70, 60],
                'avg_y': [25, 30, 28],
                ...
            }
        title: Chart title
        height: Chart height
        width: Chart width
        colorscale: Plotly colorscale

    Returns:
        Plotly Figure object

    Example:
        >>> names = ['Haaland', 'Kane', 'Lewandowski']
        >>> components = {
        ...     'avg_x': [68, 67, 66],
        ...     'avg_y': [50, 52, 48],
        ...     'attacking_third_pct': [75, 72, 70]
        ... }
        >>> fig = create_role_heatmap(names, components)
    """
    # Convert to matrix (components x players)
    component_names = list(role_components.keys())
    matrix = []
    for comp_name in component_names:
        matrix.append(role_components[comp_name])

    # Create hover text
    hover_text = []
    for i, comp_name in enumerate(component_names):
        row = []
        for j, player_name in enumerate(player_names):
            value = matrix[i][j]
            text = f"{player_name}<br>{comp_name}: {value:.1f}"
            row.append(text)
        hover_text.append(row)

    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=player_names,
        y=component_names,
        colorscale=colorscale,
        text=hover_text,
        hoverinfo='text',
        colorbar=dict(title="Value")
    ))

    # Update layout
    fig.update_layout(
        title=title or "Role Components Heatmap",
        xaxis=dict(title="Players", side='bottom'),
        yaxis=dict(title="Components"),
        height=height,
        width=width
    )

    return fig


# ============================================================================
# METRIC CORRELATION MATRIX
# ============================================================================

def create_correlation_matrix(
    metric_names: List[str],
    correlation_matrix: List[List[float]],
    title: Optional[str] = None,
    height: int = 600,
    width: int = 700
) -> go.Figure:
    """
    Create correlation matrix heatmap for metrics.

    Args:
        metric_names: List of metric names
        correlation_matrix: 2D correlation matrix (-1 to 1)
        title: Chart title
        height: Chart height
        width: Chart width

    Returns:
        Plotly Figure object

    Example:
        >>> metrics = ['Goals', 'xG', 'Shots']
        >>> corr = [
        ...     [1.00, 0.92, 0.85],
        ...     [0.92, 1.00, 0.88],
        ...     [0.85, 0.88, 1.00]
        ... ]
        >>> fig = create_correlation_matrix(metrics, corr)
    """
    # Create hover text
    hover_text = []
    for i, metric1 in enumerate(metric_names):
        row = []
        for j, metric2 in enumerate(metric_names):
            corr = correlation_matrix[i][j]
            text = f"{metric1} vs {metric2}<br>Correlation: {corr:.3f}"
            row.append(text)
        hover_text.append(row)

    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=correlation_matrix,
        x=metric_names,
        y=metric_names,
        colorscale='RdBu',
        zmid=0,
        zmin=-1,
        zmax=1,
        text=hover_text,
        hoverinfo='text',
        colorbar=dict(title="Correlation")
    ))

    # Add correlation values as annotations
    annotations = []
    for i in range(len(metric_names)):
        for j in range(len(metric_names)):
            corr = correlation_matrix[i][j]
            annotations.append(
                dict(
                    x=j,
                    y=i,
                    text=f"{corr:.2f}",
                    showarrow=False,
                    font=dict(
                        color='white' if abs(corr) > 0.5 else 'black',
                        size=10
                    )
                )
            )

    # Update layout
    fig.update_layout(
        title=title or "Metric Correlation Matrix",
        xaxis=dict(title="", side='bottom'),
        yaxis=dict(title=""),
        height=height,
        width=width,
        annotations=annotations
    )

    return fig


# ============================================================================
# PERFORMANCE ACROSS COMPETITIONS HEATMAP
# ============================================================================

def create_competition_heatmap(
    player_names: List[str],
    competitions: List[str],
    metric_values: List[List[float]],
    metric_name: str,
    title: Optional[str] = None,
    height: int = 500,
    width: int = 800
) -> go.Figure:
    """
    Create heatmap showing metric performance across competitions.

    Args:
        player_names: List of player names
        competitions: List of competition names
        metric_values: 2D array [players x competitions]
        metric_name: Name of the metric being displayed
        title: Chart title
        height: Chart height
        width: Chart width

    Returns:
        Plotly Figure object

    Example:
        >>> players = ['Haaland', 'Kane']
        >>> comps = ['Premier League', 'Champions League', 'FA Cup']
        >>> values = [
        ...     [1.2, 0.9, 1.1],  # Haaland
        ...     [0.9, 0.8, 0.7]   # Kane
        ... ]
        >>> fig = create_competition_heatmap(
        ...     players, comps, values, 'Goals per 90'
        ... )
    """
    # Create hover text
    hover_text = []
    for i, player in enumerate(player_names):
        row = []
        for j, comp in enumerate(competitions):
            value = metric_values[i][j]
            text = f"{player}<br>{comp}<br>{metric_name}: {value:.2f}"
            row.append(text)
        hover_text.append(row)

    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=metric_values,
        x=competitions,
        y=player_names,
        colorscale='YlOrRd',
        text=hover_text,
        hoverinfo='text',
        colorbar=dict(title=metric_name)
    ))

    # Add values as annotations
    annotations = []
    for i in range(len(player_names)):
        for j in range(len(competitions)):
            value = metric_values[i][j]
            annotations.append(
                dict(
                    x=j,
                    y=i,
                    text=f"{value:.2f}",
                    showarrow=False,
                    font=dict(size=10)
                )
            )

    # Update layout
    fig.update_layout(
        title=title or f"{metric_name} Across Competitions",
        xaxis=dict(title="Competition", side='bottom'),
        yaxis=dict(title="Players"),
        height=height,
        width=width,
        annotations=annotations
    )

    return fig


# ============================================================================
# POSITION HEATMAP (PITCH VISUALIZATION)
# ============================================================================

def create_position_heatmap(
    player_name: str,
    position_data: Dict[str, float],
    title: Optional[str] = None,
    height: int = 600,
    width: int = 400
) -> go.Figure:
    """
    Create heatmap showing player's position distribution on pitch.

    Args:
        player_name: Player name
        position_data: Dict with zone percentages:
            {
                'left_attacking': 35,
                'center_attacking': 25,
                'right_attacking': 5,
                'left_middle': 10,
                'center_middle': 15,
                'right_middle': 5,
                'left_defensive': 2,
                'center_defensive': 2,
                'right_defensive': 1
            }
        title: Chart title
        height: Chart height
        width: Chart width

    Returns:
        Plotly Figure object
    """
    # Create 3x3 grid (defensive, middle, attacking) x (left, center, right)
    zones = ['attacking', 'middle', 'defensive']
    positions = ['left', 'center', 'right']

    # Build matrix
    matrix = []
    hover_text = []

    for zone in zones:
        row = []
        hover_row = []
        for pos in positions:
            key = f'{pos}_{zone}'
            value = position_data.get(key, 0)
            row.append(value)
            hover_row.append(f"{pos.title()} {zone.title()}<br>{value:.1f}%")
        matrix.append(row)
        hover_text.append(hover_row)

    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=['Left', 'Center', 'Right'],
        y=['Attacking', 'Middle', 'Defensive'],
        colorscale='Reds',
        text=hover_text,
        hoverinfo='text',
        colorbar=dict(title="% of Touches")
    ))

    # Add percentage annotations
    annotations = []
    for i in range(3):
        for j in range(3):
            value = matrix[i][j]
            annotations.append(
                dict(
                    x=j,
                    y=i,
                    text=f"{value:.1f}%",
                    showarrow=False,
                    font=dict(color='white' if value > 15 else 'black', size=12)
                )
            )

    # Update layout
    fig.update_layout(
        title=title or f"{player_name} - Position Distribution",
        xaxis=dict(title="", side='top'),
        yaxis=dict(title="", autorange='reversed'),
        height=height,
        width=width,
        annotations=annotations
    )

    return fig


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    """
    Example usage of heatmap functions.
    """

    print("=" * 80)
    print("HEATMAP EXAMPLES")
    print("=" * 80)

    # Example 1: Similarity matrix
    print("\n[Example 1] Similarity Matrix")

    names = ['Haaland', 'Kane', 'Lewandowski']
    sim_matrix = [
        [1.00, 0.85, 0.78],
        [0.85, 1.00, 0.82],
        [0.78, 0.82, 1.00]
    ]

    fig1 = create_similarity_matrix(names, sim_matrix)
    # fig1.show()
    print("Created similarity matrix")

    # Example 2: Role heatmap
    print("\n[Example 2] Role Components Heatmap")

    role_comps = {
        'avg_x': [68, 67, 66],
        'avg_y': [50, 52, 48],
        'attacking_third_pct': [75, 72, 70],
        'touches_in_box_per90': [5.2, 4.8, 5.0]
    }

    fig2 = create_role_heatmap(names, role_comps)
    # fig2.show()
    print("Created role heatmap")

    # Example 3: Position heatmap
    print("\n[Example 3] Position Distribution")

    pos_data = {
        'left_attacking': 35,
        'center_attacking': 40,
        'right_attacking': 5,
        'left_middle': 5,
        'center_middle': 10,
        'right_middle': 3,
        'left_defensive': 1,
        'center_defensive': 1,
        'right_defensive': 0
    }

    fig3 = create_position_heatmap('Erling Haaland', pos_data)
    # fig3.show()
    print("Created position heatmap")

    print("\n" + "=" * 80)
    print("All heatmaps created successfully!")
