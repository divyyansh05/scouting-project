"""
Scatter Plot Visualization - visualization/scatter.py

RESPONSIBILITIES:
-----------------
Create scatter plots for similarity space and metric comparisons.

CRITICAL RULES:
--------------
- ACCEPT PREPARED DATA ONLY - No computation
- NO BUSINESS LOGIC - Pure visualization
- RETURN PLOTLY FIGURES - Reusable across app
- NO DASH CALLBACKS - Just functions that return figures

USE CASES:
---------
1. 2D metric comparison (e.g., goals vs assists)
2. Similarity space visualization
3. Player clustering
4. Interactive player selection
"""

import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from typing import Dict, List, Optional, Tuple


# ============================================================================
# 2D METRIC SCATTER
# ============================================================================

def create_metric_scatter(
    players_data: List[Dict],
    x_metric: str,
    y_metric: str,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
    title: Optional[str] = None,
    color_by: Optional[str] = None,
    size_by: Optional[str] = None,
    highlight_players: Optional[List[str]] = None,
    height: int = 600,
    width: int = 800,
    show_labels: bool = True
) -> go.Figure:
    """
    Create 2D scatter plot comparing two metrics.

    Args:
        players_data: List of dicts with:
            {
                'name': 'Player Name',
                'metrics': {'metric_id': value, ...},
                'position': 'FW',
                'age': 25,
                ... (other attributes)
            }
        x_metric: Metric ID for x-axis
        y_metric: Metric ID for y-axis
        x_label: X-axis label (default: x_metric)
        y_label: Y-axis label (default: y_metric)
        title: Chart title
        color_by: Attribute to color by (e.g., 'position', 'age')
        size_by: Metric to size points by
        highlight_players: List of player names to highlight
        height: Chart height
        width: Chart width
        show_labels: Whether to show player name labels

    Returns:
        Plotly Figure object

    Example:
        >>> players = [
        ...     {
        ...         'name': 'Haaland',
        ...         'metrics': {'goals_per90': 1.2, 'assists_per90': 0.3},
        ...         'position': 'FW'
        ...     },
        ...     {
        ...         'name': 'Kane',
        ...         'metrics': {'goals_per90': 0.9, 'assists_per90': 0.5},
        ...         'position': 'FW'
        ...     }
        ... ]
        >>> fig = create_metric_scatter(
        ...     players, 'goals_per90', 'assists_per90',
        ...     x_label='Goals per 90', y_label='Assists per 90'
        ... )
    """
    # Extract data
    x_values = []
    y_values = []
    names = []
    colors = []
    sizes = []
    hover_texts = []

    for player in players_data:
        name = player['name']
        metrics = player.get('metrics', {})

        x_val = metrics.get(x_metric, 0)
        y_val = metrics.get(y_metric, 0)

        x_values.append(x_val)
        y_values.append(y_val)
        names.append(name)

        # Color by attribute
        if color_by:
            colors.append(player.get(color_by, 'Unknown'))
        else:
            colors.append('All Players')

        # Size by metric
        if size_by:
            sizes.append(metrics.get(size_by, 10))
        else:
            sizes.append(10)

        # Hover text
        hover_text = f"<b>{name}</b><br>"
        hover_text += f"{x_label or x_metric}: {x_val:.2f}<br>"
        hover_text += f"{y_label or y_metric}: {y_val:.2f}<br>"
        if color_by:
            hover_text += f"{color_by}: {player.get(color_by)}"
        hover_texts.append(hover_text)

    # Create figure
    fig = go.Figure()

    # Group by color if color_by specified
    if color_by:
        unique_colors = list(set(colors))
        for color_val in unique_colors:
            mask = [c == color_val for c in colors]

            fig.add_trace(go.Scatter(
                x=[x for x, m in zip(x_values, mask) if m],
                y=[y for y, m in zip(y_values, mask) if m],
                mode='markers+text' if show_labels else 'markers',
                name=str(color_val),
                text=[n for n, m in zip(names, mask) if m],
                textposition='top center',
                marker=dict(
                    size=[s for s, m in zip(sizes, mask) if m],
                    sizemode='diameter',
                    sizeref=2,
                    sizemin=4,
                    line=dict(width=1, color='white')
                ),
                hovertext=[h for h, m in zip(hover_texts, mask) if m],
                hoverinfo='text'
            ))
    else:
        fig.add_trace(go.Scatter(
            x=x_values,
            y=y_values,
            mode='markers+text' if show_labels else 'markers',
            name='Players',
            text=names,
            textposition='top center',
            marker=dict(
                size=sizes,
                sizemode='diameter',
                sizeref=2,
                sizemin=4,
                color='#1f77b4',
                line=dict(width=1, color='white')
            ),
            hovertext=hover_texts,
            hoverinfo='text'
        ))

    # Highlight specific players
    if highlight_players:
        highlight_x = []
        highlight_y = []
        highlight_names = []

        for i, name in enumerate(names):
            if name in highlight_players:
                highlight_x.append(x_values[i])
                highlight_y.append(y_values[i])
                highlight_names.append(name)

        if highlight_x:
            fig.add_trace(go.Scatter(
                x=highlight_x,
                y=highlight_y,
                mode='markers+text',
                name='Highlighted',
                text=highlight_names,
                textposition='top center',
                textfont=dict(size=12, color='red'),
                marker=dict(
                    size=15,
                    color='red',
                    symbol='star',
                    line=dict(width=2, color='darkred')
                ),
                showlegend=False
            ))

    # Update layout
    fig.update_layout(
        title=title or f"{x_label or x_metric} vs {y_label or y_metric}",
        xaxis_title=x_label or x_metric,
        yaxis_title=y_label or y_metric,
        height=height,
        width=width,
        hovermode='closest',
        showlegend=bool(color_by)
    )

    return fig


# ============================================================================
# SIMILARITY SPACE SCATTER
# ============================================================================

def create_similarity_scatter(
    target_player: Dict,
    similar_players: List[Dict],
    title: Optional[str] = None,
    height: int = 600,
    width: int = 800,
    show_similarity_labels: bool = True
) -> go.Figure:
    """
    Create scatter plot showing similarity space.

    Uses role vector components (avg_x, avg_y) for positioning.

    Args:
        target_player: Dict with:
            {
                'name': 'Player Name',
                'role_components': {'avg_x': 65, 'avg_y': 25},
                'similarity': 1.0
            }
        similar_players: List of similar player dicts with similarity scores
        title: Chart title
        height: Chart height
        width: Chart width
        show_similarity_labels: Show similarity scores on hover

    Returns:
        Plotly Figure object

    Example:
        >>> target = {
        ...     'name': 'Rodri',
        ...     'role_components': {'avg_x': 45, 'avg_y': 50},
        ...     'similarity': 1.0
        ... }
        >>> similar = [
        ...     {
        ...         'name': 'Busquets',
        ...         'role_components': {'avg_x': 43, 'avg_y': 52},
        ...         'similarity': 0.92
        ...     }
        ... ]
        >>> fig = create_similarity_scatter(target, similar)
    """
    fig = go.Figure()

    # Extract similar players data
    sim_x = []
    sim_y = []
    sim_names = []
    sim_scores = []
    sim_colors = []

    for player in similar_players:
        role_comp = player.get('role_components', {})
        sim_x.append(role_comp.get('avg_x', 50))
        sim_y.append(role_comp.get('avg_y', 50))
        sim_names.append(player['name'])
        sim_score = player.get('similarity', 0)
        sim_scores.append(sim_score)

        # Color by similarity (gradient)
        if sim_score >= 0.9:
            sim_colors.append('darkgreen')
        elif sim_score >= 0.8:
            sim_colors.append('green')
        elif sim_score >= 0.7:
            sim_colors.append('orange')
        else:
            sim_colors.append('red')

    # Add similar players
    fig.add_trace(go.Scatter(
        x=sim_x,
        y=sim_y,
        mode='markers+text',
        name='Similar Players',
        text=sim_names,
        textposition='top center',
        marker=dict(
            size=[score * 20 for score in sim_scores],  # Size by similarity
            color=sim_scores,
            colorscale='RdYlGn',
            cmin=0.5,
            cmax=1.0,
            showscale=True,
            colorbar=dict(title="Similarity"),
            line=dict(width=1, color='white')
        ),
        hovertext=[
            f"<b>{name}</b><br>Similarity: {score:.3f}<br>Position: ({x:.1f}, {y:.1f})"
            for name, score, x, y in zip(sim_names, sim_scores, sim_x, sim_y)
        ],
        hoverinfo='text'
    ))

    # Add target player (star marker)
    target_role = target_player.get('role_components', {})
    target_x = target_role.get('avg_x', 50)
    target_y = target_role.get('avg_y', 50)

    fig.add_trace(go.Scatter(
        x=[target_x],
        y=[target_y],
        mode='markers+text',
        name='Target Player',
        text=[target_player['name']],
        textposition='top center',
        textfont=dict(size=14, color='darkblue'),
        marker=dict(
            size=25,
            color='blue',
            symbol='star',
            line=dict(width=3, color='darkblue')
        ),
        hovertext=f"<b>{target_player['name']}</b><br>Target Player<br>Position: ({target_x:.1f}, {target_y:.1f})",
        hoverinfo='text'
    ))

    # Update layout
    fig.update_layout(
        title=title or f"Similarity Space - {target_player['name']}",
        xaxis_title="Average X Position (0=defensive, 100=attacking)",
        yaxis_title="Average Y Position (0=left, 100=right)",
        height=height,
        width=width,
        hovermode='closest',
        xaxis=dict(range=[0, 100]),
        yaxis=dict(range=[0, 100])
    )

    return fig


# ============================================================================
# CLUSTER SCATTER
# ============================================================================

def create_cluster_scatter(
    players_data: List[Dict],
    cluster_labels: List[int],
    cluster_names: Optional[Dict[int, str]] = None,
    title: Optional[str] = None,
    height: int = 600,
    width: int = 800
) -> go.Figure:
    """
    Create scatter plot with player clusters.

    Args:
        players_data: List of player dicts with 'x' and 'y' coordinates
        cluster_labels: List of cluster IDs for each player
        cluster_names: Optional dict mapping cluster_id -> cluster_name
        title: Chart title
        height: Chart height
        width: Chart width

    Returns:
        Plotly Figure object

    Example:
        >>> players = [
        ...     {'name': 'Player A', 'x': 65, 'y': 25},
        ...     {'name': 'Player B', 'x': 45, 'y': 50}
        ... ]
        >>> clusters = [0, 1]
        >>> cluster_names = {0: 'Attackers', 1: 'Midfielders'}
        >>> fig = create_cluster_scatter(players, clusters, cluster_names)
    """
    fig = go.Figure()

    # Get unique clusters
    unique_clusters = list(set(cluster_labels))

    colors = px.colors.qualitative.Set1

    for cluster_id in unique_clusters:
        # Get players in this cluster
        cluster_mask = [label == cluster_id for label in cluster_labels]

        cluster_players = [p for p, m in zip(players_data, cluster_mask) if m]
        cluster_x = [p.get('x', 0) for p in cluster_players]
        cluster_y = [p.get('y', 0) for p in cluster_players]
        cluster_player_names = [p.get('name', '') for p in cluster_players]

        cluster_name = cluster_names.get(cluster_id, f"Cluster {cluster_id}") if cluster_names else f"Cluster {cluster_id}"

        fig.add_trace(go.Scatter(
            x=cluster_x,
            y=cluster_y,
            mode='markers+text',
            name=cluster_name,
            text=cluster_player_names,
            textposition='top center',
            marker=dict(
                size=12,
                color=colors[cluster_id % len(colors)],
                line=dict(width=1, color='white')
            )
        ))

    # Update layout
    fig.update_layout(
        title=title or "Player Clusters",
        xaxis_title="Dimension 1",
        yaxis_title="Dimension 2",
        height=height,
        width=width,
        hovermode='closest'
    )

    return fig


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    """
    Example usage of scatter plot functions.
    """

    print("=" * 80)
    print("SCATTER PLOT EXAMPLES")
    print("=" * 80)

    # Example 1: Metric scatter
    print("\n[Example 1] Metric Scatter")

    players = [
        {
            'name': 'Haaland',
            'metrics': {'goals_per90': 1.2, 'assists_per90': 0.3},
            'position': 'FW',
            'age': 23
        },
        {
            'name': 'Kane',
            'metrics': {'goals_per90': 0.9, 'assists_per90': 0.5},
            'position': 'FW',
            'age': 30
        },
        {
            'name': 'Salah',
            'metrics': {'goals_per90': 0.8, 'assists_per90': 0.4},
            'position': 'FW',
            'age': 31
        }
    ]

    fig1 = create_metric_scatter(
        players,
        'goals_per90',
        'assists_per90',
        x_label='Goals per 90',
        y_label='Assists per 90',
        color_by='position'
    )
    # fig1.show()
    print("Created metric scatter")

    # Example 2: Similarity scatter
    print("\n[Example 2] Similarity Space")

    target = {
        'name': 'Rodri',
        'role_components': {'avg_x': 45, 'avg_y': 50},
        'similarity': 1.0
    }

    similar = [
        {
            'name': 'Busquets',
            'role_components': {'avg_x': 43, 'avg_y': 52},
            'similarity': 0.92
        },
        {
            'name': 'Fabinho',
            'role_components': {'avg_x': 44, 'avg_y': 48},
            'similarity': 0.88
        }
    ]

    fig2 = create_similarity_scatter(target, similar)
    # fig2.show()
    print("Created similarity scatter")

    print("\n" + "=" * 80)
    print("All scatter plots created successfully!")
