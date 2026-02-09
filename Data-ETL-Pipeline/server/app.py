import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from flask import Flask, render_template, jsonify, request
from database.connection import get_db

app = Flask(__name__)

@app.route('/')
def index():
    """Render the dashboard home page."""
    return render_template('index.html', active_page='dashboard')

@app.route('/api/stats')
def get_stats():
    """Get overall database statistics."""
    db = get_db()

    # Convert Row objects to dicts for serialization
    sources_data = db.execute_query("SELECT source_name, reliability_score FROM data_sources", fetch=True)
    sources_list = [{'name': row[0], 'score': row[1]} for row in sources_data]

    stats = {
        'leagues': db.execute_query("SELECT COUNT(*) FROM leagues", fetch=True)[0][0],
        'teams': db.execute_query("SELECT COUNT(*) FROM teams", fetch=True)[0][0],
        'players': db.execute_query("SELECT COUNT(*) FROM players", fetch=True)[0][0],
        'matches': db.execute_query("SELECT COUNT(*) FROM matches", fetch=True)[0][0],
        'player_season_stats': db.execute_query("SELECT COUNT(*) FROM player_season_stats", fetch=True)[0][0],
        'team_season_stats': db.execute_query("SELECT COUNT(*) FROM team_season_stats", fetch=True)[0][0],
        'sources': sources_list
    }
    return jsonify(stats)


@app.route('/api/stats/detailed')
def get_detailed_stats():
    """Get detailed database statistics with league and season breakdown."""
    db = get_db()

    # League breakdown with data coverage
    league_stats = db.execute_query("""
        SELECT
            l.league_id,
            l.league_name,
            l.country,
            COUNT(DISTINCT t.team_id) as teams,
            COUNT(DISTINCT m.match_id) as matches,
            COUNT(DISTINCT pss.player_id) as players_with_stats,
            COUNT(DISTINCT pss.player_season_stat_id) as stat_records
        FROM leagues l
        LEFT JOIN teams t ON l.league_id = t.league_id
        LEFT JOIN matches m ON l.league_id = m.league_id
        LEFT JOIN player_season_stats pss ON l.league_id = pss.league_id
        GROUP BY l.league_id, l.league_name, l.country
        ORDER BY matches DESC
    """, fetch=True)

    leagues = [{
        'id': row[0],
        'name': row[1],
        'country': row[2],
        'teams': row[3],
        'matches': row[4],
        'players_with_stats': row[5],
        'stat_records': row[6],
        'data_completeness': min(100, int((row[5] / max(row[3] * 25, 1)) * 100)) if row[3] else 0
    } for row in league_stats]

    # Season breakdown
    season_stats = db.execute_query("""
        SELECT
            s.season_id,
            s.season_name,
            COUNT(DISTINCT m.match_id) as matches,
            COUNT(DISTINCT pss.player_id) as players_with_stats,
            COUNT(DISTINCT pss.player_season_stat_id) as stat_records
        FROM seasons s
        LEFT JOIN matches m ON s.season_id = m.season_id
        LEFT JOIN player_season_stats pss ON s.season_id = pss.season_id
        GROUP BY s.season_id, s.season_name
        ORDER BY s.season_name DESC
    """, fetch=True)

    seasons = [{
        'id': row[0],
        'name': row[1],
        'matches': row[2],
        'players_with_stats': row[3],
        'stat_records': row[4]
    } for row in season_stats]

    # Top scorers across all data
    top_scorers = db.execute_query("""
        SELECT
            p.player_id,
            p.player_name,
            p.position,
            t.team_name,
            l.league_name,
            SUM(pss.goals) as total_goals,
            SUM(pss.assists) as total_assists,
            SUM(pss.minutes) as total_minutes,
            s.season_name
        FROM player_season_stats pss
        JOIN players p ON pss.player_id = p.player_id
        JOIN teams t ON pss.team_id = t.team_id
        JOIN leagues l ON pss.league_id = l.league_id
        JOIN seasons s ON pss.season_id = s.season_id
        WHERE pss.goals > 0
        GROUP BY p.player_id, p.player_name, p.position, t.team_name, l.league_name, s.season_name
        ORDER BY total_goals DESC
        LIMIT 15
    """, fetch=True)

    scorers = [{
        'id': row[0],
        'name': row[1],
        'position': row[2],
        'team': row[3],
        'league': row[4],
        'goals': row[5],
        'assists': row[6],
        'minutes': row[7],
        'season': row[8]
    } for row in top_scorers]

    # Top assisters
    top_assisters = db.execute_query("""
        SELECT
            p.player_id,
            p.player_name,
            p.position,
            t.team_name,
            l.league_name,
            SUM(pss.assists) as total_assists,
            SUM(pss.goals) as total_goals,
            SUM(pss.minutes) as total_minutes,
            s.season_name
        FROM player_season_stats pss
        JOIN players p ON pss.player_id = p.player_id
        JOIN teams t ON pss.team_id = t.team_id
        JOIN leagues l ON pss.league_id = l.league_id
        JOIN seasons s ON pss.season_id = s.season_id
        WHERE pss.assists > 0
        GROUP BY p.player_id, p.player_name, p.position, t.team_name, l.league_name, s.season_name
        ORDER BY total_assists DESC
        LIMIT 15
    """, fetch=True)

    assisters = [{
        'id': row[0],
        'name': row[1],
        'position': row[2],
        'team': row[3],
        'league': row[4],
        'assists': row[5],
        'goals': row[6],
        'minutes': row[7],
        'season': row[8]
    } for row in top_assisters]

    # Recent data updates (matches by month)
    monthly_matches = db.execute_query("""
        SELECT
            to_char(match_date, 'YYYY-MM') as month,
            COUNT(*) as matches
        FROM matches
        WHERE match_date IS NOT NULL
        GROUP BY to_char(match_date, 'YYYY-MM')
        ORDER BY month DESC
        LIMIT 12
    """, fetch=True)

    monthly_data = [{
        'month': row[0],
        'matches': row[1]
    } for row in monthly_matches]

    return jsonify({
        'leagues': leagues,
        'seasons': seasons,
        'top_scorers': scorers,
        'top_assisters': assisters,
        'monthly_matches': monthly_data
    })


@app.route('/api/players/top')
def get_top_players():
    """Get top players with comprehensive stats."""
    db = get_db()
    league = request.args.get('league', '')
    season = request.args.get('season', '')
    sort_by = request.args.get('sort', 'goals')
    limit = min(int(request.args.get('limit', 50)), 100)

    # Build query with filters
    where_clauses = []
    params = {}

    if league:
        where_clauses.append("l.league_name = :league")
        params['league'] = league
    if season:
        where_clauses.append("s.season_name = :season")
        params['season'] = season

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    # Determine sort column
    sort_columns = {
        'goals': 'pss.goals DESC',
        'assists': 'pss.assists DESC',
        'minutes': 'pss.minutes DESC',
        'xg': 'pss.xg DESC NULLS LAST',
        'goals_per_90': '(pss.goals::float / NULLIF(pss.minutes, 0) * 90) DESC NULLS LAST'
    }
    order_by = sort_columns.get(sort_by, 'pss.goals DESC')

    query = f"""
        SELECT
            p.player_id,
            p.player_name,
            p.position,
            p.nationality,
            t.team_name,
            l.league_name,
            s.season_name,
            pss.matches_played,
            pss.starts,
            pss.minutes,
            pss.goals,
            pss.assists,
            pss.xg,
            pss.xag,
            pss.shots,
            pss.key_passes,
            ROUND((pss.goals::numeric / NULLIF(pss.minutes, 0) * 90)::numeric, 2) as goals_per_90,
            ROUND((pss.assists::numeric / NULLIF(pss.minutes, 0) * 90)::numeric, 2) as assists_per_90
        FROM player_season_stats pss
        JOIN players p ON pss.player_id = p.player_id
        JOIN teams t ON pss.team_id = t.team_id
        JOIN leagues l ON pss.league_id = l.league_id
        JOIN seasons s ON pss.season_id = s.season_id
        {where_sql}
        ORDER BY {order_by}
        LIMIT :limit
    """
    params['limit'] = limit

    players = db.execute_query(query, params, fetch=True)

    return jsonify([{
        'id': row[0],
        'name': row[1],
        'position': row[2],
        'nationality': row[3],
        'team': row[4],
        'league': row[5],
        'season': row[6],
        'matches': row[7],
        'starts': row[8],
        'minutes': row[9],
        'goals': row[10],
        'assists': row[11],
        'xg': float(row[12]) if row[12] else None,
        'xag': float(row[13]) if row[13] else None,
        'shots': row[14],
        'key_passes': row[15],
        'goals_per_90': float(row[16]) if row[16] else None,
        'assists_per_90': float(row[17]) if row[17] else None
    } for row in players])


@app.route('/api/leagues')
def get_leagues():
    """Get all leagues with summary stats."""
    db = get_db()

    leagues = db.execute_query("""
        SELECT
            l.league_id,
            l.league_name,
            l.country,
            COUNT(DISTINCT t.team_id) as teams,
            COUNT(DISTINCT m.match_id) as matches
        FROM leagues l
        LEFT JOIN teams t ON l.league_id = t.league_id
        LEFT JOIN matches m ON l.league_id = m.league_id
        GROUP BY l.league_id, l.league_name, l.country
        ORDER BY l.league_name
    """, fetch=True)

    return jsonify([{
        'id': row[0],
        'name': row[1],
        'country': row[2],
        'teams': row[3],
        'matches': row[4]
    } for row in leagues])


@app.route('/api/seasons')
def get_seasons():
    """Get all seasons."""
    db = get_db()

    seasons = db.execute_query("""
        SELECT season_id, season_name
        FROM seasons
        ORDER BY season_name DESC
    """, fetch=True)

    return jsonify([{
        'id': row[0],
        'name': row[1]
    } for row in seasons])


@app.route('/api/health')
def get_data_health():
    """Get data health and completeness indicators."""
    db = get_db()
    health_issues = []
    health_metrics = {}

    # Check for players without stats
    players_without_stats = db.execute_query("""
        SELECT COUNT(*) FROM players p
        WHERE NOT EXISTS (
            SELECT 1 FROM player_season_stats pss WHERE pss.player_id = p.player_id
        )
    """, fetch=True)[0][0]
    health_metrics['players_without_stats'] = players_without_stats
    if players_without_stats > 0:
        health_issues.append({
            'level': 'warning',
            'message': f'{players_without_stats} players have no season stats'
        })

    # Check for teams without players
    teams_without_players = db.execute_query("""
        SELECT COUNT(*) FROM teams t
        WHERE NOT EXISTS (
            SELECT 1 FROM player_season_stats pss WHERE pss.team_id = t.team_id
        )
    """, fetch=True)[0][0]
    health_metrics['teams_without_players'] = teams_without_players
    if teams_without_players > 0:
        health_issues.append({
            'level': 'info',
            'message': f'{teams_without_players} teams have no player stats'
        })

    # Check for matches without scores
    matches_without_scores = db.execute_query("""
        SELECT COUNT(*) FROM matches
        WHERE home_score IS NULL OR away_score IS NULL
    """, fetch=True)[0][0]
    health_metrics['matches_without_scores'] = matches_without_scores
    if matches_without_scores > 0:
        health_issues.append({
            'level': 'info',
            'message': f'{matches_without_scores} matches have no scores (possibly upcoming)'
        })

    # Check last data update
    last_match = db.execute_query("""
        SELECT MAX(match_date) FROM matches
    """, fetch=True)[0][0]
    health_metrics['latest_match_date'] = str(last_match) if last_match else None

    last_stat_update = db.execute_query("""
        SELECT MAX(updated_at) FROM player_season_stats
    """, fetch=True)[0][0]
    health_metrics['last_stat_update'] = str(last_stat_update) if last_stat_update else None

    # Data coverage by league
    league_coverage = db.execute_query("""
        SELECT
            l.league_name,
            COUNT(DISTINCT t.team_id) as teams,
            COUNT(DISTINCT pss.player_id) as players_with_stats,
            COUNT(DISTINCT pss.player_season_stat_id) as stat_records,
            ROUND(COUNT(DISTINCT pss.player_id)::numeric / NULLIF(COUNT(DISTINCT t.team_id), 0) / 25 * 100, 1) as coverage_pct
        FROM leagues l
        LEFT JOIN teams t ON l.league_id = t.league_id
        LEFT JOIN player_season_stats pss ON l.league_id = pss.league_id
        GROUP BY l.league_id, l.league_name
        ORDER BY l.league_name
    """, fetch=True)

    coverage = [{
        'league': row[0],
        'teams': row[1],
        'players': row[2],
        'records': row[3],
        'coverage': float(row[4]) if row[4] else 0
    } for row in league_coverage]

    # Overall health score (0-100)
    total_players = db.execute_query("SELECT COUNT(*) FROM players", fetch=True)[0][0]
    total_teams = db.execute_query("SELECT COUNT(*) FROM teams", fetch=True)[0][0]

    score = 100
    if total_players > 0:
        score -= min(30, (players_without_stats / total_players) * 50)
    if total_teams > 0:
        score -= min(20, (teams_without_players / total_teams) * 30)

    return jsonify({
        'score': max(0, round(score)),
        'issues': health_issues,
        'metrics': health_metrics,
        'coverage': coverage
    })

@app.route('/api/matches')
def get_recent_matches():
    """Get 50 most recent matches."""
    db = get_db()
    query = """
        SELECT 
            m.match_date, 
            l.league_name,
            ht.team_name as home_team,
            at.team_name as away_team,
            m.home_score,
            m.away_score,
            m.venue
        FROM matches m
        JOIN leagues l ON m.league_id = l.league_id
        JOIN teams ht ON m.home_team_id = ht.team_id
        JOIN teams at ON m.away_team_id = at.team_id
        ORDER BY m.match_date DESC
        LIMIT 50
    """
    matches = db.execute_query(query, fetch=True)
    
    # Format for JSON
    data = []
    for m in matches:
        data.append({
            'date': str(m[0]),
            'league': m[1],
            'home_team': m[2],
            'away_team': m[3],
            'score': f"{m[4]} - {m[5]}" if m[4] is not None else "vs",
            'venue': m[6]
        })
        
    return jsonify(data)

# --- Routes for Teams ---

@app.route('/teams')
def teams_list():
    """Render the teams list page."""
    return render_template('teams.html', active_page='teams')

@app.route('/teams/<int:team_id>')
def team_detail(team_id):
    """Render the team detail page."""
    db = get_db()
    # verify team exists
    res = db.execute_query("SELECT team_name FROM teams WHERE team_id = :id", {'id': team_id}, fetch=True)
    if not res:
        return "Team not found", 404
    return render_template('team_detail.html', active_page='teams', team_id=team_id, team_name=res[0][0])

@app.route('/api/teams')
def get_teams():
    """Get all teams with league info, optional search."""
    db = get_db()
    search = request.args.get('q', '').lower()
    
    query = """
        SELECT t.team_id, t.team_name, l.league_name, t.stadium, t.founded_year
        FROM teams t
        JOIN leagues l ON t.league_id = l.league_id
    """
    params = {}
    if search:
        query += " WHERE LOWER(t.team_name) LIKE :search"
        params['search'] = f"%{search}%"
        
    query += " ORDER BY t.team_name ASC"
    
    teams = db.execute_query(query, params, fetch=True)
    data = [{
        'id': t[0],
        'name': t[1],
        'league': t[2],
        'stadium': t[3],
        'founded': t[4]
    } for t in teams]
    return jsonify(data)

@app.route('/api/teams/<int:team_id>')
def get_team_details(team_id):
    """Get detailed stats for a team."""
    db = get_db()
    
    # Basic Info
    q_info = """
        SELECT t.team_name, l.league_name, t.stadium, t.founded_year
        FROM teams t
        JOIN leagues l ON t.league_id = l.league_id
        WHERE t.team_id = :id
    """
    info = db.execute_query(q_info, {'id': team_id}, fetch=True)
    if not info:
        return jsonify({'error': 'Team not found'}), 404
        
    team_data = {
        'name': info[0][0],
        'league': info[0][1],
        'stadium': info[0][2],
        'founded': info[0][3]
    }
    
    # Recent Matches
    q_matches = """
        SELECT m.match_date, ht.team_name, at.team_name, m.home_score, m.away_score, m.match_id
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.team_id
        JOIN teams at ON m.away_team_id = at.team_id
        WHERE m.home_team_id = :id OR m.away_team_id = :id
        ORDER BY m.match_date DESC
        LIMIT 10
    """
    matches = db.execute_query(q_matches, {'id': team_id}, fetch=True)
    team_data['recent_matches'] = [{
        'date': str(m[0]),
        'home_team': m[1],
        'away_team': m[2],
        'score': f"{m[3]} - {m[4]}",
        'id': m[5]
    } for m in matches]
    
    # Squad with Stats Summary (using player_season_stats)
    q_squad = """
        SELECT DISTINCT p.player_id, p.player_name, p.position, p.nationality,
               SUM(pss.matches_played) as apps,
               SUM(pss.goals) as goals,
               SUM(pss.assists) as assists,
               SUM(pss.minutes) as minutes
        FROM players p
        JOIN player_season_stats pss ON p.player_id = pss.player_id
        WHERE pss.team_id = :id
        GROUP BY p.player_id, p.player_name, p.position, p.nationality
        ORDER BY goals DESC, apps DESC
    """
    players = db.execute_query(q_squad, {'id': team_id}, fetch=True)

    team_data['squad'] = [{
        'id': p[0],
        'name': p[1],
        'position': p[2],
        'nationality': p[3],
        'apps': p[4] or 0,
        'goals': p[5] or 0,
        'assists': p[6] or 0,
        'minutes': p[7] or 0
    } for p in players]

    return jsonify(team_data)

# --- Routes for Players ---

@app.route('/players')
def players_list():
    return render_template('players.html', active_page='players')

@app.route('/players/<int:player_id>')
def player_detail(player_id):
    db = get_db()
    res = db.execute_query("SELECT player_name FROM players WHERE player_id = :id", {'id': player_id}, fetch=True)
    if not res:
        return "Player not found", 404
    return render_template('player_detail.html', active_page='players', player_id=player_id, player_name=res[0][0])

@app.route('/api/players')
def get_players():
    db = get_db()
    search = request.args.get('q', '').lower()
    league = request.args.get('league', '')
    position = request.args.get('position', '')

    # Enhanced query with stats summary
    query = """
        SELECT
            p.player_id,
            p.player_name,
            p.position,
            p.nationality,
            t.team_name,
            l.league_name,
            SUM(pss.goals) as total_goals,
            SUM(pss.assists) as total_assists,
            SUM(pss.minutes) as total_minutes,
            COUNT(DISTINCT pss.season_id) as seasons
        FROM players p
        LEFT JOIN player_season_stats pss ON p.player_id = pss.player_id
        LEFT JOIN teams t ON pss.team_id = t.team_id
        LEFT JOIN leagues l ON pss.league_id = l.league_id
        WHERE 1=1
    """
    params = {}

    if search:
        query += " AND LOWER(p.player_name) LIKE :search"
        params['search'] = f"%{search}%"
    if league:
        query += " AND l.league_name = :league"
        params['league'] = league
    if position:
        query += " AND p.position = :position"
        params['position'] = position

    query += """
        GROUP BY p.player_id, p.player_name, p.position, p.nationality, t.team_name, l.league_name
        ORDER BY total_goals DESC NULLS LAST, p.player_name ASC
        LIMIT 200
    """

    players = db.execute_query(query, params, fetch=True)
    data = [{
        'id': p[0],
        'name': p[1],
        'position': p[2],
        'nationality': p[3],
        'team': p[4],
        'league': p[5],
        'goals': p[6] or 0,
        'assists': p[7] or 0,
        'minutes': p[8] or 0,
        'seasons': p[9] or 0
    } for p in players]
    return jsonify(data)

@app.route('/api/players/<int:player_id>')
def get_player_details(player_id):
    db = get_db()

    # Basic Info
    q_info = "SELECT player_name, position, nationality, date_of_birth FROM players WHERE player_id = :id"
    info = db.execute_query(q_info, {'id': player_id}, fetch=True)
    if not info:
        return jsonify({'error': 'Player not found'}), 404

    player_data = {
        'name': info[0][0],
        'position': info[0][1],
        'nationality': info[0][2],
        'dob': str(info[0][3]) if info[0][3] else None
    }

    # Season stats (primary data source)
    q_seasons = """
        SELECT
            s.season_name,
            t.team_name,
            l.league_name,
            pss.matches_played,
            pss.starts,
            pss.minutes,
            pss.goals,
            pss.assists,
            pss.xg,
            pss.xag,
            pss.shots,
            pss.key_passes,
            pss.passes_completed,
            pss.tackles,
            pss.interceptions,
            pss.dribbles_completed,
            pss.yellow_cards,
            pss.red_cards
        FROM player_season_stats pss
        JOIN seasons s ON pss.season_id = s.season_id
        JOIN teams t ON pss.team_id = t.team_id
        JOIN leagues l ON pss.league_id = l.league_id
        WHERE pss.player_id = :id
        ORDER BY s.season_name DESC
    """
    seasons = db.execute_query(q_seasons, {'id': player_id}, fetch=True)

    player_data['season_stats'] = [{
        'season': row[0],
        'team': row[1],
        'league': row[2],
        'matches': row[3] or 0,
        'starts': row[4] or 0,
        'minutes': row[5] or 0,
        'goals': row[6] or 0,
        'assists': row[7] or 0,
        'xg': float(row[8]) if row[8] else 0.0,
        'xag': float(row[9]) if row[9] else 0.0,
        'shots': row[10] or 0,
        'key_passes': row[11] or 0,
        'passes': row[12] or 0,
        'tackles': row[13] or 0,
        'interceptions': row[14] or 0,
        'dribbles': row[15] or 0,
        'yellow_cards': row[16] or 0,
        'red_cards': row[17] or 0
    } for row in seasons]

    # Calculate career totals
    totals = {
        'matches': sum(s['matches'] for s in player_data['season_stats']),
        'goals': sum(s['goals'] for s in player_data['season_stats']),
        'assists': sum(s['assists'] for s in player_data['season_stats']),
        'minutes': sum(s['minutes'] for s in player_data['season_stats']),
        'xg': sum(s['xg'] for s in player_data['season_stats']),
        'xag': sum(s['xag'] for s in player_data['season_stats'])
    }
    player_data['career_totals'] = totals

    return jsonify(player_data)

# --- Routes for Matches ---

@app.route('/matches')
def matches_list():
    return render_template('matches.html', active_page='matches')

@app.route('/matches/<int:match_id>')
def match_detail(match_id):
    db = get_db()
    # Check existence
    res = db.execute_query("SELECT match_id FROM matches WHERE match_id = :id", {'id': match_id}, fetch=True)
    if not res:
        return "Match not found", 404
    return render_template('match_detail.html', active_page='matches', match_id=match_id)

@app.route('/api/matches/<int:match_id>')
def get_match_full_details(match_id):
    db = get_db()
    
    # Header Info
    q_header = """
        SELECT m.match_date, l.league_name, ht.team_name, at.team_name, 
               m.home_score, m.away_score, m.venue, ht.team_id, at.team_id
        FROM matches m
        JOIN leagues l ON m.league_id = l.league_id
        JOIN teams ht ON m.home_team_id = ht.team_id
        JOIN teams at ON m.away_team_id = at.team_id
        WHERE m.match_id = :id
    """
    header = db.execute_query(q_header, {'id': match_id}, fetch=True)
    if not header:
        return jsonify({'error': 'Match not found'}), 404
        
    h = header[0]
    data = {
        'date': str(h[0]),
        'league': h[1],
        'home_team': {'name': h[2], 'id': h[7]},
        'away_team': {'name': h[3], 'id': h[8]},
        'score': f"{h[4]} - {h[5]}",
        'venue': h[6]
    }
    
    # Lineups / Players
    # We get player stats for this match, sorted by team
    q_stats = """
        SELECT p.player_name, p.player_id, t.team_id, pms.minutes_played, pms.goals, pms.assists
        FROM player_match_stats pms
        JOIN players p ON pms.player_id = p.player_id
        JOIN teams t ON pms.team_id = t.team_id
        WHERE pms.match_id = :id
        ORDER BY t.team_name, pms.started DESC, pms.minutes_played DESC
    """
    stats = db.execute_query(q_stats, {'id': match_id}, fetch=True)
    
    home_players = []
    away_players = []
    
    for s in stats:
        p_obj = {
            'name': s[0], 'id': s[1], 
            'mins': s[3], 'goals': s[4], 'assists': s[5]
        }
        if s[2] == data['home_team']['id']:
            home_players.append(p_obj)
        else:
            away_players.append(p_obj)
            
    data['home_lineup'] = home_players
    data['away_lineup'] = away_players
    
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
