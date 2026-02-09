"""
Main Dash Application - app.py

RESPONSIBILITIES:
-----------------
Orchestrate all services and visualizations into interactive web interface.

CRITICAL RULES:
--------------
- ORCHESTRATION ONLY - Coordinate services and visualizations
- NO METRIC COMPUTATION - All calculations in services
- NO RAW DATA LOOPS - Use service functions
- CACHE SERVICE CALLS - Store results to avoid recomputation
- THIN CALLBACKS - Just wire services to UI

ARCHITECTURE:
------------
    User Input (UI)
        |
    Dash Callback (orchestration)
        |
    Service Function (computation)
        |
    Visualization Function (display)
        |
    Update UI

FEATURES:
--------
1. League -> Team -> Player browsing
2. Player dashboard (metrics, radars, etc.)
3. Similarity search
4. LLM natural language queries
"""

import dash
from dash import dcc, html, dash_table, Input, Output, State, callback
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
from functools import lru_cache
import logging

# Import services
from services.metrics_service import (
    compute_player_season_metrics,
    compute_team_aggregates
)
from services.role_service import build_role_vector
from services.similarity_service import (
    find_similar_players,
    similarity_score_breakdown
)
from services.llm_service import parse_query_with_fallback

# Import visualizations
from visualization.radar import (
    create_player_radar,
    create_comparison_radar,
    create_position_radar
)
from visualization.scatter import (
    create_metric_scatter,
    create_similarity_scatter
)
from visualization.heatmaps import (
    create_similarity_matrix,
    create_position_heatmap
)
from visualization.tables import (
    create_player_comparison_table,
    create_similarity_results_table,
    create_leaderboard_table
)

# Import database utilities
from utils.db import fetch_dataframe, startup_db, shutdown_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# APP INITIALIZATION
# ============================================================================

# Initialize Dash app with Bootstrap theme
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    suppress_callback_exceptions=True,
    title="Football Scouting Analytics"
)

# Initialize database
startup_db()

# Default season
DEFAULT_SEASON = "2023-24"


# ============================================================================
# CACHED DATA LOADING FUNCTIONS
# ============================================================================

@lru_cache(maxsize=128)
def get_leagues():
    """Get list of available leagues."""
    query = "SELECT league_id, league_name, country FROM leagues ORDER BY league_name"
    df = fetch_dataframe(query)
    return df['league_name'].tolist() if not df.empty else []


@lru_cache(maxsize=128)
def get_teams(league: str = None):
    """Get list of teams, optionally filtered by league."""
    if league:
        query = """
            SELECT DISTINCT t.team_name
            FROM teams t
            JOIN leagues l ON t.league_id = l.league_id
            WHERE l.league_name = %s
            ORDER BY t.team_name
        """
        df = fetch_dataframe(query, params=(league,))
    else:
        query = "SELECT DISTINCT team_name FROM teams ORDER BY team_name"
        df = fetch_dataframe(query)

    return df['team_name'].tolist() if not df.empty else []


@lru_cache(maxsize=256)
def get_players(team: str = None, position: str = None):
    """Get list of players, optionally filtered by team and position."""
    query = """
        SELECT DISTINCT p.player_id, p.player_name as name, p.position,
               EXTRACT(YEAR FROM AGE(p.date_of_birth))::int as age,
               t.team_name as current_team
        FROM players p
        LEFT JOIN player_season_stats pss ON p.player_id = pss.player_id
        LEFT JOIN teams t ON pss.team_id = t.team_id
        WHERE 1=1
    """
    params = []

    if team:
        query += " AND t.team_name = %s"
        params.append(team)

    if position:
        query += " AND p.position = %s"
        params.append(position)

    query += " ORDER BY p.player_name"

    df = fetch_dataframe(query, params=tuple(params) if params else None)
    return df.to_dict('records') if not df.empty else []


# ============================================================================
# LAYOUT COMPONENTS
# ============================================================================

def create_header():
    """Create application header."""
    return dbc.Navbar(
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H2("Football Scouting Analytics", className="text-light mb-0")
                ], width="auto"),
            ], align="center"),
            dbc.Row([
                dbc.Col([
                    html.Span("Powered by Advanced Analytics", className="text-muted small")
                ])
            ])
        ], fluid=True),
        color="dark",
        dark=True,
        className="mb-4"
    )


def create_navigation_panel():
    """Create navigation panel for browsing."""
    return dbc.Card([
        dbc.CardHeader(html.H5("Browse Players")),
        dbc.CardBody([
            # League selector
            html.Label("League:", className="fw-bold"),
            dcc.Dropdown(
                id='league-dropdown',
                options=[{'label': 'All Leagues', 'value': 'all'}] +
                        [{'label': league, 'value': league} for league in get_leagues()],
                value='all',
                clearable=False,
                className="mb-3"
            ),

            # Team selector
            html.Label("Team:", className="fw-bold"),
            dcc.Dropdown(
                id='team-dropdown',
                options=[{'label': 'All Teams', 'value': 'all'}],
                value='all',
                clearable=False,
                className="mb-3"
            ),

            # Position filter
            html.Label("Position:", className="fw-bold"),
            dcc.Dropdown(
                id='position-dropdown',
                options=[
                    {'label': 'All Positions', 'value': 'all'},
                    {'label': 'Goalkeeper (GK)', 'value': 'GK'},
                    {'label': 'Defender (DF)', 'value': 'DF'},
                    {'label': 'Midfielder (MF)', 'value': 'MF'},
                    {'label': 'Forward (FW)', 'value': 'FW'}
                ],
                value='all',
                clearable=False,
                className="mb-3"
            ),

            # Player selector
            html.Label("Player:", className="fw-bold"),
            dcc.Dropdown(
                id='player-dropdown',
                options=[],
                value=None,
                placeholder="Select a player...",
                className="mb-3"
            ),

            # Season selector
            html.Label("Season:", className="fw-bold"),
            dcc.Dropdown(
                id='season-dropdown',
                options=[
                    {'label': '2023-24', 'value': '2023-24'},
                    {'label': '2022-23', 'value': '2022-23'},
                    {'label': '2021-22', 'value': '2021-22'}
                ],
                value=DEFAULT_SEASON,
                clearable=False,
                className="mb-3"
            ),

            # Load button
            dbc.Button(
                "Load Player Dashboard",
                id='load-player-btn',
                color="primary",
                className="w-100",
                disabled=True
            )
        ])
    ], className="mb-4")


def create_llm_query_bar():
    """Create LLM natural language query interface."""
    return dbc.Card([
        dbc.CardHeader(html.H5("Ask AI")),
        dbc.CardBody([
            html.P(
                "Ask natural language questions about players:",
                className="text-muted small"
            ),
            dbc.InputGroup([
                dbc.Input(
                    id='llm-query-input',
                    placeholder='e.g., "Find players similar to Rodri but younger"',
                    type='text'
                ),
                dbc.Button(
                    "Ask",
                    id='llm-query-btn',
                    color="success"
                )
            ]),
            html.Div(id='llm-query-status', className="mt-2"),
            dcc.Loading(
                id='llm-loading',
                type='default',
                children=html.Div(id='llm-results')
            )
        ])
    ], className="mb-4")


def create_player_dashboard():
    """Create player dashboard tab content."""
    return dbc.Container([
        # Player info header
        html.Div(id='player-info-header', className="mb-4"),

        # Metrics and visualizations
        dbc.Row([
            # Radar chart
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("Metric Profile")),
                    dbc.CardBody([
                        dcc.Loading(
                            dcc.Graph(id='player-radar-chart')
                        )
                    ])
                ])
            ], width=6),

            # Position heatmap
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("Position Distribution")),
                    dbc.CardBody([
                        dcc.Loading(
                            dcc.Graph(id='position-heatmap')
                        )
                    ])
                ])
            ], width=6)
        ], className="mb-4"),

        # Detailed metrics table
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("Detailed Metrics")),
                    dbc.CardBody([
                        dcc.Loading(
                            html.Div(id='player-metrics-table')
                        )
                    ])
                ])
            ])
        ], className="mb-4"),

        # Role analysis
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("Role Analysis")),
                    dbc.CardBody([
                        dcc.Loading(
                            html.Div(id='role-analysis')
                        )
                    ])
                ])
            ])
        ])
    ], fluid=True)


def create_similarity_search():
    """Create similarity search tab content."""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H5("Find Similar Players"),
                html.P(
                    "Configure similarity search parameters:",
                    className="text-muted"
                )
            ])
        ], className="mb-3"),

        dbc.Row([
            # Search parameters
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Search Parameters"),
                    dbc.CardBody([
                        html.Label("Number of Results:", className="fw-bold"),
                        dcc.Slider(
                            id='n-similar-slider',
                            min=5,
                            max=20,
                            step=5,
                            value=10,
                            marks={i: str(i) for i in range(5, 21, 5)},
                            className="mb-3"
                        ),

                        html.Label("Minimum Minutes:", className="fw-bold"),
                        dcc.Input(
                            id='min-minutes-input',
                            type='number',
                            value=450,
                            className="form-control mb-3"
                        ),

                        html.Label("Age Range:", className="fw-bold"),
                        dcc.RangeSlider(
                            id='age-range-slider',
                            min=16,
                            max=40,
                            step=1,
                            value=[18, 35],
                            marks={i: str(i) for i in range(16, 41, 4)},
                            className="mb-3"
                        ),

                        dbc.Button(
                            "Find Similar Players",
                            id='similarity-search-btn',
                            color="primary",
                            className="w-100",
                            disabled=True
                        )
                    ])
                ])
            ], width=4),

            # Results
            dbc.Col([
                dcc.Loading([
                    # Similarity scatter
                    dbc.Card([
                        dbc.CardHeader("Similarity Space"),
                        dbc.CardBody([
                            dcc.Graph(id='similarity-scatter')
                        ])
                    ], className="mb-3"),

                    # Results table
                    dbc.Card([
                        dbc.CardHeader("Similar Players"),
                        dbc.CardBody([
                            html.Div(id='similarity-results-table')
                        ])
                    ])
                ])
            ], width=8)
        ])
    ], fluid=True)


# ============================================================================
# MAIN LAYOUT
# ============================================================================

app.layout = dbc.Container([
    # Header
    create_header(),

    # Main content
    dbc.Row([
        # Left sidebar - Navigation
        dbc.Col([
            create_navigation_panel(),
            create_llm_query_bar()
        ], width=3),

        # Main content area
        dbc.Col([
            dbc.Tabs([
                dbc.Tab(
                    create_player_dashboard(),
                    label="Player Dashboard",
                    tab_id="dashboard"
                ),
                dbc.Tab(
                    create_similarity_search(),
                    label="Similarity Search",
                    tab_id="similarity"
                )
            ], id='main-tabs', active_tab="dashboard")
        ], width=9)
    ]),

    # Hidden divs for storing state
    dcc.Store(id='current-player-id'),
    dcc.Store(id='current-season'),
    dcc.Store(id='player-metrics-cache'),
    dcc.Store(id='player-role-cache'),
    dcc.Store(id='similarity-results-cache')

], fluid=True, className="p-4")


# ============================================================================
# NAVIGATION CALLBACKS
# ============================================================================

@app.callback(
    Output('team-dropdown', 'options'),
    Input('league-dropdown', 'value')
)
def update_team_dropdown(league):
    """Update team dropdown based on selected league."""
    if league == 'all':
        teams = get_teams()
    else:
        teams = get_teams(league)

    options = [{'label': 'All Teams', 'value': 'all'}]
    options.extend([{'label': team, 'value': team} for team in teams])

    return options


@app.callback(
    Output('player-dropdown', 'options'),
    [Input('team-dropdown', 'value'),
     Input('position-dropdown', 'value')]
)
def update_player_dropdown(team, position):
    """Update player dropdown based on team and position filters."""
    # Get players with filters
    team_filter = None if team == 'all' else team
    position_filter = None if position == 'all' else position

    players = get_players(team_filter, position_filter)

    options = [
        {
            'label': f"{p['name']} ({p['position']}, {p['age']} yo) - {p['current_team']}",
            'value': p['player_id']
        }
        for p in players
    ]

    return options


@app.callback(
    [Output('load-player-btn', 'disabled'),
     Output('similarity-search-btn', 'disabled')],
    Input('player-dropdown', 'value')
)
def enable_buttons(player_id):
    """Enable buttons when player is selected."""
    disabled = player_id is None
    return disabled, disabled


# ============================================================================
# PLAYER DASHBOARD CALLBACKS
# ============================================================================

@app.callback(
    [Output('current-player-id', 'data'),
     Output('current-season', 'data'),
     Output('player-metrics-cache', 'data'),
     Output('player-role-cache', 'data')],
    [Input('load-player-btn', 'n_clicks')],
    [State('player-dropdown', 'value'),
     State('season-dropdown', 'value')],
    prevent_initial_call=True
)
def load_player_data(n_clicks, player_id, season):
    """
    Load player data when button clicked.

    ORCHESTRATION ONLY:
    - Call service functions
    - Store results
    - No computation here
    """
    if not player_id:
        raise PreventUpdate

    logger.info(f"Loading player {player_id} for season {season}")

    # Call services (computation happens here, not in callback)
    metrics = compute_player_season_metrics(player_id, season)
    role = build_role_vector(player_id, season)

    # Store in cache
    return player_id, season, metrics, role


@app.callback(
    Output('player-info-header', 'children'),
    Input('player-metrics-cache', 'data')
)
def update_player_info_header(metrics):
    """Display player information header."""
    if not metrics:
        return html.Div("Select a player to view dashboard", className="text-muted")

    player_info = metrics.get('player_info', {})
    aggregates = metrics.get('aggregates', {})

    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H3(player_info.get('name', 'Unknown')),
                    html.P([
                        f"{player_info.get('position', 'N/A')} | ",
                        f"Age {player_info.get('age', 'N/A')} | ",
                        f"{player_info.get('current_team', 'N/A')}"
                    ], className="text-muted")
                ], width=8),
                dbc.Col([
                    html.Div([
                        html.H5(f"{aggregates.get('matches_played', 0)}", className="mb-0"),
                        html.Small("Matches", className="text-muted")
                    ], className="text-center"),
                ], width=2),
                dbc.Col([
                    html.Div([
                        html.H5(f"{aggregates.get('total_minutes', 0):.0f}", className="mb-0"),
                        html.Small("Minutes", className="text-muted")
                    ], className="text-center"),
                ], width=2)
            ])
        ])
    ], color="primary", outline=True)


@app.callback(
    Output('player-radar-chart', 'figure'),
    Input('player-metrics-cache', 'data')
)
def update_player_radar(metrics):
    """
    Create player radar chart.

    ORCHESTRATION ONLY:
    - Extract data from cache
    - Call visualization function
    - Return figure
    """
    if not metrics or not metrics.get('meets_minimum'):
        return go.Figure().add_annotation(
            text="Insufficient data for visualization",
            showarrow=False,
            font=dict(size=16)
        )

    player_info = metrics.get('player_info', {})
    per90 = metrics.get('per90_metrics', {})

    # Get position-specific metrics (let visualization handle it)
    fig = create_position_radar(
        player_name=player_info.get('name', 'Player'),
        player_metrics=per90,
        position=player_info.get('position', 'MF')
    )

    return fig


@app.callback(
    Output('position-heatmap', 'figure'),
    Input('player-role-cache', 'data')
)
def update_position_heatmap(role):
    """Create position distribution heatmap."""
    if not role or role.get('vector') is None:
        return go.Figure().add_annotation(
            text="Position data not available",
            showarrow=False,
            font=dict(size=16)
        )

    components = role.get('components', {})

    # Build position data for heatmap
    position_data = {
        'left_attacking': components.get('left_zone_pct', 0) *
                         (components.get('attacking_third_pct', 0) / 100),
        'center_attacking': components.get('center_zone_pct', 0) *
                           (components.get('attacking_third_pct', 0) / 100),
        'right_attacking': components.get('right_zone_pct', 0) *
                          (components.get('attacking_third_pct', 0) / 100),
        'left_middle': components.get('left_zone_pct', 0) *
                      (components.get('middle_third_pct', 0) / 100),
        'center_middle': components.get('center_zone_pct', 0) *
                        (components.get('middle_third_pct', 0) / 100),
        'right_middle': components.get('right_zone_pct', 0) *
                       (components.get('middle_third_pct', 0) / 100),
        'left_defensive': components.get('left_zone_pct', 0) *
                         (components.get('defensive_third_pct', 0) / 100),
        'center_defensive': components.get('center_zone_pct', 0) *
                           (components.get('defensive_third_pct', 0) / 100),
        'right_defensive': components.get('right_zone_pct', 0) *
                          (components.get('defensive_third_pct', 0) / 100)
    }

    # Get player name from somewhere
    player_name = "Player"

    fig = create_position_heatmap(player_name, position_data)

    return fig


@app.callback(
    Output('player-metrics-table', 'children'),
    Input('player-metrics-cache', 'data')
)
def update_metrics_table(metrics):
    """Create detailed metrics table."""
    if not metrics:
        return html.P("No data available", className="text-muted")

    from visualization.tables import create_detailed_metrics_table

    table_config = create_detailed_metrics_table(metrics)

    return dash_table.DataTable(**table_config)


@app.callback(
    Output('role-analysis', 'children'),
    Input('player-role-cache', 'data')
)
def update_role_analysis(role):
    """Display role analysis text."""
    if not role or role.get('vector') is None:
        return html.P("Role analysis not available", className="text-muted")

    # Build explanation from role components
    components = role.get('components', {})

    explanation_parts = []

    avg_x = components.get('avg_x', 50)
    if avg_x > 60:
        explanation_parts.append("Operates primarily in the attacking third")
    elif avg_x < 40:
        explanation_parts.append("Operates primarily in the defensive third")
    else:
        explanation_parts.append("Operates primarily in the middle third")

    spread = components.get('spread', 0)
    if spread > 15:
        explanation_parts.append("with a wide range of movement across the pitch")
    else:
        explanation_parts.append("with concentrated positioning")

    explanation = ". ".join(explanation_parts) + "."

    return dbc.Alert(explanation, color="info")


# ============================================================================
# SIMILARITY SEARCH CALLBACKS
# ============================================================================

@app.callback(
    [Output('similarity-results-cache', 'data'),
     Output('similarity-scatter', 'figure'),
     Output('similarity-results-table', 'children')],
    [Input('similarity-search-btn', 'n_clicks')],
    [State('current-player-id', 'data'),
     State('current-season', 'data'),
     State('n-similar-slider', 'value'),
     State('min-minutes-input', 'value'),
     State('age-range-slider', 'value')],
    prevent_initial_call=True
)
def run_similarity_search(n_clicks, player_id, season, n_similar, min_minutes, age_range):
    """
    Run similarity search.

    ORCHESTRATION ONLY:
    - Call similarity service
    - Call visualization functions
    - Return results
    """
    if not player_id:
        raise PreventUpdate

    logger.info(f"Running similarity search for player {player_id}")

    # Build filters
    filters = {
        'min_minutes': min_minutes,
        'age_min': age_range[0],
        'age_max': age_range[1]
    }

    # Call service (computation happens here)
    similar_players = find_similar_players(
        player_id=player_id,
        season=season,
        n_similar=n_similar,
        filters=filters
    )

    # Convert to dicts for caching
    similar_dicts = [s.to_dict() for s in similar_players]

    # Create scatter plot
    # Need to get target player's role for scatter
    target_role = build_role_vector(player_id, season)

    target_data = {
        'name': 'Target Player',
        'role_components': target_role.get('components', {}),
        'similarity': 1.0
    }

    similar_data = [
        {
            'name': s['player_name'],
            'role_components': build_role_vector(s['player_id'], season).get('components', {}),
            'similarity': s['similarity_score']
        }
        for s in similar_dicts[:10]  # Limit for performance
    ]

    scatter_fig = create_similarity_scatter(target_data, similar_data)

    # Create results table
    table_config = create_similarity_results_table(similar_dicts)
    table_component = dash_table.DataTable(**table_config)

    return similar_dicts, scatter_fig, table_component


# ============================================================================
# LLM QUERY CALLBACKS
# ============================================================================

@app.callback(
    [Output('llm-query-status', 'children'),
     Output('llm-results', 'children')],
    [Input('llm-query-btn', 'n_clicks')],
    [State('llm-query-input', 'value'),
     State('current-season', 'data')],
    prevent_initial_call=True
)
def process_llm_query(n_clicks, query, season):
    """
    Process LLM natural language query.

    ORCHESTRATION ONLY:
    - Parse query with LLM service
    - Route to appropriate service
    - Display results
    """
    if not query:
        raise PreventUpdate

    logger.info(f"Processing LLM query: {query}")

    # Parse query (LLM call happens here)
    parsed = parse_query_with_fallback(query)

    # Display parsing status
    status = dbc.Alert([
        html.Strong("Query understood: "),
        html.Span(f"Searching for {parsed.get('position', 'players')}"),
        html.Br(),
        html.Small(f"Filters: {parsed.get('validation_warnings', [])}" if parsed.get('validation_warnings') else "")
    ], color="success", className="mt-2")

    # Route based on query type
    if parsed.get('similarity_search'):
        # Similarity search
        results_text = html.P("Similarity search not yet implemented in this query handler")
    else:
        # Regular search
        results_text = html.P("Regular search not yet implemented in this query handler")

    results = dbc.Card([
        dbc.CardHeader("Query Results"),
        dbc.CardBody(results_text)
    ], className="mt-3")

    return status, results


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == '__main__':
    try:
        logger.info("Starting Dash application...")
        app.run(debug=True, host='0.0.0.0', port=8050)
    finally:
        shutdown_db()
        logger.info("Database connection closed")
