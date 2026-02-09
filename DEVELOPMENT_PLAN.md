# Chelsea FC Scouting System - Development Plan

> **Document Version:** 2.0
> **Last Updated:** 2024-02-03
> **Project Root:** `/Users/divyanshshrivastava/Scouting_project`
> **Target Audience:** Development agents (Claude Code, Codex, Antigravity), Human developers

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Current Architecture](#2-current-architecture)
3. [Development Phases](#3-development-phases)
4. [Phase 1: Foundation & Infrastructure](#4-phase-1-foundation--infrastructure)
5. [Phase 2: Core Feature Enhancements](#5-phase-2-core-feature-enhancements)
6. [Phase 3: Analytics & Intelligence](#6-phase-3-analytics--intelligence)
7. [Phase 4: Advanced Workflows](#7-phase-4-advanced-workflows)
8. [Phase 5: LLM Integration](#8-phase-5-llm-integration)
9. [Phase 6: Polish & Documentation](#9-phase-6-polish--documentation)
10. [Deferred Items](#10-deferred-items)
11. [File Reference Guide](#11-file-reference-guide)
12. [Testing Requirements](#12-testing-requirements)
13. [Success Metrics](#13-success-metrics)

---

## 1. Project Overview

### 1.1 What This Project Does

A **football (soccer) player scouting analytics platform** for Chelsea FC that enables:
- **Player similarity search**: Find players similar to a target player
- **Metrics analysis**: Compute per-90 stats, percentiles, derived metrics
- **Role matching**: 20-dimensional spatial/behavioral player profiles
- **Natural language queries**: "Find strikers like Harry Kane but younger"
- **Data pipeline**: ETL from API-Football to PostgreSQL

### 1.2 Two Main Components

```
/Scouting_project/
├── src/                    # Scouting Analytics App (Dash UI + Services)
│   ├── app.py              # Main Dash application
│   ├── services/           # Business logic (metrics, similarity, role, LLM)
│   ├── visualization/      # Plotly charts (radar, scatter, heatmap)
│   ├── utils/              # DB access, validation
│   └── config/             # Settings, metrics registry
│
└── Data-etl-pipeline/      # Data Collection Pipeline
    ├── cli.py              # Command-line interface
    ├── etl/                # Extract-Transform-Load logic
    ├── scrapers/           # API-Football integration
    ├── scheduler/          # Automated collection
    ├── server/             # Flask web UI for monitoring
    └── database/           # Schema, migrations, connection
```

### 1.3 Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | Dash + Plotly + Bootstrap |
| Backend | Python (services layer) |
| Database | PostgreSQL (read-only from app) |
| LLM | Anthropic Claude (for query parsing) |
| ETL | Python + API-Football |
| Config | YAML (settings.yaml, metrics_registry.yaml) |

---

## 2. Current Architecture

### 2.1 Implemented Features (Working)

| Feature | Status | Location |
|---------|--------|----------|
| Metrics computation (60+ metrics) | ✅ Complete | `src/services/metrics_service.py` |
| Role vectors (20 dimensions) | ✅ Complete | `src/services/role_service.py` |
| Similarity search algorithm | ✅ Complete | `src/services/similarity_service.py` |
| Metrics registry (anti-hallucination) | ✅ Complete | `src/config/metrics_registry.yaml` |
| Basic Dash UI | ✅ Complete | `src/app.py` |
| ETL pipeline | ✅ Complete | `Data-etl-pipeline/` |
| ETL web monitoring UI | ✅ Complete | `Data-etl-pipeline/server/` |
| Database schema | ✅ Complete | `Data-etl-pipeline/database/` |

### 2.2 Placeholder/Incomplete Features

| Feature | Status | Issue |
|---------|--------|-------|
| LLM API calls | ⚠️ Placeholder | `call_llm_api()` returns mock data |
| Query execution from LLM | ⚠️ Not wired | Parsing works, execution not connected |
| Watchlists/Persistence | ❌ Missing | No save/load functionality |
| Export functionality | ❌ Missing | No CSV/PDF export |
| CI/CD pipeline | ❌ Missing | No automated testing |

### 2.3 Database Schema (Reference)

```sql
-- Core tables (already exist in PostgreSQL)
players (player_id, player_name, position, nationality, date_of_birth)
teams (team_id, team_name, league_id, stadium, founded_year)
leagues (league_id, league_name, country)
seasons (season_id, season_name)
matches (match_id, match_date, home_team_id, away_team_id, home_score, away_score)

-- Stats tables
player_season_stats (player_id, season_id, team_id, league_id,
                     matches_played, minutes, goals, assists, xg, xag,
                     shots, key_passes, passes_completed, tackles,
                     interceptions, dribbles_completed, yellow_cards, red_cards,
                     created_at, updated_at)
```

---

## 3. Development Phases

### Phase Overview

| Phase | Focus | Priority | Estimated Effort |
|-------|-------|----------|------------------|
| **Phase 1** | Foundation & Infrastructure | CRITICAL | 2-3 days |
| **Phase 2** | Core Feature Enhancements | HIGH | 4-5 days |
| **Phase 3** | Analytics & Intelligence | HIGH | 3-4 days |
| **Phase 4** | Advanced Workflows | MEDIUM | 4-5 days |
| **Phase 5** | LLM Integration | HIGH | 2-3 days |
| **Phase 6** | Polish & Documentation | MEDIUM | 2-3 days |

### Dependency Graph

```
Phase 1 (Foundation)
    ├── CI/CD Pipeline
    ├── Loading/Empty States
    └── Docker Setup
           │
           ▼
Phase 2 (Core Features)
    ├── Watchlists/Scouting Projects
    ├── Multi-Season Trends
    ├── Quick Compare Mode
    └── Export Functionality
           │
           ▼
Phase 3 (Analytics)
    ├── Benchmarks & Percentiles
    ├── Similarity Score Breakdown
    ├── Data Quality Flags
    └── Trend Alerts
           │
           ▼
Phase 4 (Advanced Workflows)
    ├── Replace Player Workflow
    ├── Role Vector Visualization
    ├── Position Flexibility Score
    └── Similar Players in Squad
           │
           ▼
Phase 5 (LLM)
    ├── Complete API Integration
    ├── Tiered Parsing (Regex + LLM)
    ├── Parser Test Suite
    └── User-Tunable Weights
           │
           ▼
Phase 6 (Polish)
    ├── Scout Report Templates
    ├── Documentation
    └── Performance Optimization
```

---

## 4. Phase 1: Foundation & Infrastructure

> **Goal:** Establish development best practices and improve basic UX
> **Priority:** CRITICAL
> **Prerequisite for:** All other phases

### Task 1.1: CI/CD Pipeline Setup

**Objective:** Automated testing and code quality checks on every commit

**Files to Create:**

```yaml
# File: /Scouting_project/.github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd src
          pip install -r requirements.txt
          pip install pytest pytest-cov flake8 mypy black isort

      - name: Lint with flake8
        run: flake8 src/ --max-line-length=120

      - name: Check formatting with black
        run: black --check src/

      - name: Check imports with isort
        run: isort --check-only src/

      - name: Type check with mypy
        run: mypy src/ --ignore-missing-imports

      - name: Run tests
        run: |
          cd src
          pytest tests/ -v --cov=services --cov=utils --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

**Files to Create:**

```yaml
# File: /Scouting_project/.pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black
        args: [--line-length=120]

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: [--profile=black]

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=120]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-PyYAML, types-requests]
        args: [--ignore-missing-imports]
```

**Installation Commands:**
```bash
cd /Users/divyanshshrivastava/Scouting_project
pip install pre-commit
pre-commit install
```

**Verification:**
- [ ] `pre-commit run --all-files` passes
- [ ] GitHub Actions workflow triggers on push
- [ ] All tests pass in CI

---

### Task 1.2: Loading & Empty States

**Objective:** Improve UX with clear feedback during data loading

**File to Modify:** `src/app.py`

**Implementation Pattern:**

```python
# Add to imports
from dash import dcc, html
import dash_bootstrap_components as dbc

# Create reusable loading component
def create_loading_component(component_id, children):
    """Wrap component with loading spinner."""
    return dcc.Loading(
        id=f"{component_id}-loading",
        type="circle",
        children=children,
        color="#3b82f6"
    )

# Create empty state component
def create_empty_state(message, icon="🔍", action_text=None, action_id=None):
    """Create consistent empty state UI."""
    children = [
        html.Div(icon, style={"fontSize": "4rem", "opacity": 0.5}),
        html.P(message, style={"color": "var(--text-secondary)", "marginTop": "1rem"}),
    ]
    if action_text and action_id:
        children.append(
            dbc.Button(action_text, id=action_id, color="primary", className="mt-3")
        )
    return html.Div(
        children,
        style={"textAlign": "center", "padding": "3rem"}
    )
```

**Apply to all data-loading sections:**
- Player dashboard
- Similarity search results
- Comparison tables
- Charts/graphs

**Verification:**
- [ ] Loading spinner appears during data fetch
- [ ] Empty state shows when no results
- [ ] Error state shows on API failure

---

### Task 1.3: Docker Setup for Scouting App

**Objective:** Containerize the scouting app for consistent deployment

**File to Create:** `src/Dockerfile`

```dockerfile
# File: /Scouting_project/src/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Dash port
EXPOSE 8050

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8050/ || exit 1

# Run application
CMD ["python", "app.py"]
```

**File to Create:** `docker-compose.yml` (project root)

```yaml
# File: /Scouting_project/docker-compose.yml
version: '3.8'

services:
  scouting-app:
    build:
      context: ./src
      dockerfile: Dockerfile
    ports:
      - "8050:8050"
    environment:
      - DB_HOST=db
      - DB_PORT=5432
      - DB_NAME=football_data
      - DB_USER=postgres
      - DB_PASSWORD=postgres
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      db:
        condition: service_healthy
    networks:
      - scouting-network

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=football_data
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./Data-etl-pipeline/database/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
    ports:
      - "5434:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - scouting-network

  etl-ui:
    build:
      context: ./Data-etl-pipeline
      dockerfile: Dockerfile
    ports:
      - "5001:5001"
    environment:
      - DB_HOST=db
      - DB_PORT=5432
    depends_on:
      db:
        condition: service_healthy
    networks:
      - scouting-network

volumes:
  postgres_data:

networks:
  scouting-network:
    driver: bridge
```

**Verification:**
- [ ] `docker-compose up --build` starts all services
- [ ] Scouting app accessible at http://localhost:8050
- [ ] ETL UI accessible at http://localhost:5001
- [ ] Database connection works from containers

---

### Task 1.4: Data Freshness Banner

**Objective:** Show users when data was last updated

**File to Modify:** `src/app.py`

**Implementation:**

```python
# Add API endpoint or direct query
def get_data_freshness():
    """Get last update timestamps from database."""
    # Query from ETL pipeline's health endpoint or direct DB query
    return {
        'last_stat_update': '2024-02-03 19:45:10',
        'latest_match_date': '2025-05-29',
        'player_count': 1373,
        'staleness_days': 7
    }

# Add to layout - data freshness banner
def create_freshness_banner():
    freshness = get_data_freshness()
    staleness = freshness.get('staleness_days', 0)

    if staleness > 14:
        color = "danger"
        message = f"⚠️ Data is {staleness} days old - consider running ETL"
    elif staleness > 7:
        color = "warning"
        message = f"Data updated {staleness} days ago"
    else:
        color = "success"
        message = f"Data up to date (updated {staleness} days ago)"

    return dbc.Alert(
        [
            html.Span(message),
            html.Span(f" | {freshness['player_count']} players",
                     className="ms-3 text-muted")
        ],
        color=color,
        dismissable=True,
        className="mb-3"
    )
```

**Verification:**
- [ ] Banner shows at top of dashboard
- [ ] Color changes based on staleness
- [ ] Shows player count

---

## 5. Phase 2: Core Feature Enhancements

> **Goal:** Add high-value features scouts will use daily
> **Priority:** HIGH
> **Depends on:** Phase 1

### Task 2.1: Watchlists / Scouting Projects

**Objective:** Allow scouts to save and compare player sets across sessions

#### Step 2.1.1: Database Schema

**File to Create:** `Data-etl-pipeline/database/migrations/002_watchlists.sql`

```sql
-- Watchlists / Scouting Projects Schema
-- Run: psql -h localhost -p 5434 -U postgres -d football_data -f 002_watchlists.sql

-- Main watchlist/project table
CREATE TABLE IF NOT EXISTS scouting_projects (
    project_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    project_type VARCHAR(50) DEFAULT 'watchlist',  -- 'watchlist', 'replacement', 'comparison'
    target_position VARCHAR(20),
    age_min INT,
    age_max INT,
    min_minutes INT DEFAULT 450,
    leagues TEXT[],  -- Array of league names
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_archived BOOLEAN DEFAULT FALSE
);

-- Players in each project
CREATE TABLE IF NOT EXISTS project_players (
    project_id INT REFERENCES scouting_projects(project_id) ON DELETE CASCADE,
    player_id INT REFERENCES players(player_id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT NOW(),
    notes TEXT,
    priority INT DEFAULT 0,  -- 1=high, 2=medium, 3=low
    status VARCHAR(20) DEFAULT 'watching',  -- 'watching', 'contacted', 'rejected', 'signed'
    PRIMARY KEY (project_id, player_id)
);

-- Create indexes
CREATE INDEX idx_scouting_projects_type ON scouting_projects(project_type);
CREATE INDEX idx_project_players_player ON project_players(player_id);
CREATE INDEX idx_project_players_status ON project_players(status);
```

#### Step 2.1.2: Backend Service

**File to Create:** `src/services/watchlist_service.py`

```python
"""
Watchlist/Scouting Projects Service

Provides CRUD operations for scouting projects and player watchlists.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from utils.db import fetch_dataframe, execute_query


@dataclass
class ScoutingProject:
    """Represents a scouting project/watchlist."""
    project_id: int
    name: str
    description: Optional[str]
    project_type: str
    target_position: Optional[str]
    age_min: Optional[int]
    age_max: Optional[int]
    min_minutes: int
    leagues: Optional[List[str]]
    created_at: datetime
    updated_at: datetime
    player_count: int = 0


@dataclass
class ProjectPlayer:
    """Represents a player in a project."""
    player_id: int
    player_name: str
    position: str
    nationality: str
    team: str
    added_at: datetime
    notes: Optional[str]
    priority: int
    status: str
    # Stats summary
    goals: int = 0
    assists: int = 0
    minutes: int = 0


def create_project(
    name: str,
    description: str = None,
    project_type: str = 'watchlist',
    target_position: str = None,
    age_min: int = None,
    age_max: int = None,
    min_minutes: int = 450,
    leagues: List[str] = None
) -> int:
    """
    Create a new scouting project.

    Args:
        name: Project name
        description: Optional description
        project_type: 'watchlist', 'replacement', or 'comparison'
        target_position: Target position filter
        age_min: Minimum age filter
        age_max: Maximum age filter
        min_minutes: Minimum minutes played filter
        leagues: List of league names to filter

    Returns:
        project_id: ID of created project
    """
    query = """
        INSERT INTO scouting_projects
        (name, description, project_type, target_position, age_min, age_max, min_minutes, leagues)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING project_id
    """
    result = execute_query(
        query,
        (name, description, project_type, target_position, age_min, age_max, min_minutes, leagues)
    )
    return result[0][0]


def get_project(project_id: int) -> Optional[ScoutingProject]:
    """Get a single project by ID."""
    query = """
        SELECT sp.*, COUNT(pp.player_id) as player_count
        FROM scouting_projects sp
        LEFT JOIN project_players pp ON sp.project_id = pp.project_id
        WHERE sp.project_id = %s AND sp.is_archived = FALSE
        GROUP BY sp.project_id
    """
    result = execute_query(query, (project_id,))
    if not result:
        return None
    row = result[0]
    return ScoutingProject(
        project_id=row[0],
        name=row[1],
        description=row[2],
        project_type=row[3],
        target_position=row[4],
        age_min=row[5],
        age_max=row[6],
        min_minutes=row[7],
        leagues=row[8],
        created_at=row[9],
        updated_at=row[10],
        player_count=row[12]
    )


def get_all_projects(include_archived: bool = False) -> List[ScoutingProject]:
    """Get all scouting projects."""
    query = """
        SELECT sp.*, COUNT(pp.player_id) as player_count
        FROM scouting_projects sp
        LEFT JOIN project_players pp ON sp.project_id = pp.project_id
        WHERE sp.is_archived = %s OR %s = TRUE
        GROUP BY sp.project_id
        ORDER BY sp.updated_at DESC
    """
    results = execute_query(query, (False, include_archived))
    return [ScoutingProject(
        project_id=row[0],
        name=row[1],
        description=row[2],
        project_type=row[3],
        target_position=row[4],
        age_min=row[5],
        age_max=row[6],
        min_minutes=row[7],
        leagues=row[8],
        created_at=row[9],
        updated_at=row[10],
        player_count=row[12]
    ) for row in results]


def add_player_to_project(
    project_id: int,
    player_id: int,
    notes: str = None,
    priority: int = 0
) -> bool:
    """Add a player to a project."""
    query = """
        INSERT INTO project_players (project_id, player_id, notes, priority)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (project_id, player_id) DO UPDATE
        SET notes = EXCLUDED.notes, priority = EXCLUDED.priority
    """
    execute_query(query, (project_id, player_id, notes, priority))
    # Update project timestamp
    execute_query(
        "UPDATE scouting_projects SET updated_at = NOW() WHERE project_id = %s",
        (project_id,)
    )
    return True


def remove_player_from_project(project_id: int, player_id: int) -> bool:
    """Remove a player from a project."""
    query = "DELETE FROM project_players WHERE project_id = %s AND player_id = %s"
    execute_query(query, (project_id, player_id))
    return True


def get_project_players(project_id: int) -> List[ProjectPlayer]:
    """Get all players in a project with their stats."""
    query = """
        SELECT
            p.player_id, p.player_name, p.position, p.nationality,
            t.team_name,
            pp.added_at, pp.notes, pp.priority, pp.status,
            COALESCE(SUM(pss.goals), 0) as goals,
            COALESCE(SUM(pss.assists), 0) as assists,
            COALESCE(SUM(pss.minutes), 0) as minutes
        FROM project_players pp
        JOIN players p ON pp.player_id = p.player_id
        LEFT JOIN player_season_stats pss ON p.player_id = pss.player_id
        LEFT JOIN teams t ON pss.team_id = t.team_id
        WHERE pp.project_id = %s
        GROUP BY p.player_id, p.player_name, p.position, p.nationality,
                 t.team_name, pp.added_at, pp.notes, pp.priority, pp.status
        ORDER BY pp.priority ASC, pp.added_at DESC
    """
    results = execute_query(query, (project_id,))
    return [ProjectPlayer(
        player_id=row[0],
        player_name=row[1],
        position=row[2],
        nationality=row[3],
        team=row[4] or 'Unknown',
        added_at=row[5],
        notes=row[6],
        priority=row[7],
        status=row[8],
        goals=row[9],
        assists=row[10],
        minutes=row[11]
    ) for row in results]


def update_player_status(project_id: int, player_id: int, status: str) -> bool:
    """Update player status in project."""
    valid_statuses = ['watching', 'contacted', 'rejected', 'signed']
    if status not in valid_statuses:
        raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")

    query = """
        UPDATE project_players
        SET status = %s
        WHERE project_id = %s AND player_id = %s
    """
    execute_query(query, (status, project_id, player_id))
    return True


def delete_project(project_id: int, hard_delete: bool = False) -> bool:
    """Delete or archive a project."""
    if hard_delete:
        execute_query("DELETE FROM scouting_projects WHERE project_id = %s", (project_id,))
    else:
        execute_query(
            "UPDATE scouting_projects SET is_archived = TRUE WHERE project_id = %s",
            (project_id,)
        )
    return True


def compare_project_players(project_id: int, metrics: List[str] = None) -> Dict[str, Any]:
    """
    Compare all players in a project.

    Returns a comparison matrix of players vs metrics.
    """
    if metrics is None:
        metrics = ['goals', 'assists', 'minutes', 'xg', 'xag']

    players = get_project_players(project_id)

    # Build comparison data
    comparison = {
        'players': [p.player_name for p in players],
        'metrics': {}
    }

    for metric in metrics:
        comparison['metrics'][metric] = [
            getattr(p, metric, 0) for p in players
        ]

    return comparison
```

#### Step 2.1.3: Frontend Components

**File to Modify:** `src/app.py`

Add watchlist management tab and components. Create callbacks for:
- List all projects
- Create new project
- Add/remove players from project
- View project with player cards
- Export project

**Verification:**
- [ ] Can create new scouting project
- [ ] Can add players to project
- [ ] Can view all projects
- [ ] Projects persist across browser sessions
- [ ] Can export project data

---

### Task 2.2: Multi-Season Trend Views

**Objective:** Show player performance trends across seasons

#### Step 2.2.1: Backend Enhancement

**File to Modify:** `src/services/metrics_service.py`

```python
def compute_player_trend(
    player_id: int,
    metrics: List[str] = None,
    seasons: List[str] = None
) -> Dict[str, Any]:
    """
    Compute player metrics across multiple seasons for trend analysis.

    Args:
        player_id: Player ID
        metrics: List of metric IDs to include
        seasons: List of season names (e.g., ['2022-23', '2023-24', '2024-25'])

    Returns:
        {
            'player_id': 123,
            'player_name': 'Harry Kane',
            'seasons': ['2022-23', '2023-24', '2024-25'],
            'metrics': {
                'goals_per90': [0.65, 0.72, 0.81],
                'xg_per90': [0.58, 0.65, 0.74],
                ...
            },
            'changes': {
                'goals_per90': {'absolute': 0.16, 'percentage': 24.6, 'trend': 'improving'},
                ...
            }
        }
    """
    if metrics is None:
        metrics = ['goals', 'assists', 'minutes', 'xg', 'xag', 'shots', 'key_passes']

    query = """
        SELECT
            s.season_name,
            pss.goals, pss.assists, pss.minutes, pss.xg, pss.xag,
            pss.shots, pss.key_passes, pss.matches_played
        FROM player_season_stats pss
        JOIN seasons s ON pss.season_id = s.season_id
        JOIN players p ON pss.player_id = p.player_id
        WHERE pss.player_id = %s
        ORDER BY s.season_name ASC
    """

    results = fetch_dataframe(query, (player_id,))

    if results.empty:
        return None

    # Build trend data
    trend_data = {
        'player_id': player_id,
        'seasons': results['season_name'].tolist(),
        'metrics': {},
        'changes': {}
    }

    for metric in metrics:
        if metric in results.columns:
            values = results[metric].tolist()
            trend_data['metrics'][metric] = values

            # Calculate change from first to last season
            if len(values) >= 2 and values[0] and values[-1]:
                first_val = float(values[0])
                last_val = float(values[-1])
                abs_change = last_val - first_val
                pct_change = ((last_val - first_val) / first_val * 100) if first_val != 0 else 0

                trend_data['changes'][metric] = {
                    'absolute': round(abs_change, 2),
                    'percentage': round(pct_change, 1),
                    'trend': 'improving' if abs_change > 0 else 'declining' if abs_change < 0 else 'stable'
                }

    return trend_data
```

#### Step 2.2.2: Visualization

**File to Modify:** `src/visualization/scatter.py`

```python
def create_trend_line_chart(trend_data: Dict[str, Any], metrics: List[str] = None) -> go.Figure:
    """
    Create line chart showing player metrics over seasons.

    Args:
        trend_data: Output from compute_player_trend()
        metrics: Metrics to display (default: goals, assists)
    """
    if metrics is None:
        metrics = ['goals', 'assists']

    fig = go.Figure()

    colors = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6']

    for i, metric in enumerate(metrics):
        if metric in trend_data['metrics']:
            fig.add_trace(go.Scatter(
                x=trend_data['seasons'],
                y=trend_data['metrics'][metric],
                mode='lines+markers',
                name=metric.replace('_', ' ').title(),
                line=dict(color=colors[i % len(colors)], width=3),
                marker=dict(size=10)
            ))

    fig.update_layout(
        title=f"Performance Trend",
        xaxis_title="Season",
        yaxis_title="Value",
        template="plotly_dark",
        hovermode='x unified'
    )

    return fig
```

**Verification:**
- [ ] Trend chart displays for players with multiple seasons
- [ ] Shows improvement/decline indicators
- [ ] Can toggle different metrics on/off

---

### Task 2.3: Quick Compare Mode

**Objective:** Select 2-4 players from any list for instant comparison

#### Implementation

**File to Modify:** `src/app.py`

```python
# Add to layout - comparison selection store
dcc.Store(id='selected-players-store', data=[]),

# Add selection checkboxes to player cards/rows
def create_player_row_with_select(player_data):
    return html.Div([
        dbc.Checkbox(
            id={'type': 'player-select', 'index': player_data['player_id']},
            value=False,
            className='me-2'
        ),
        # ... rest of player row
    ])

# Comparison panel that appears when 2+ players selected
def create_comparison_panel(selected_players):
    if len(selected_players) < 2:
        return html.Div()

    return dbc.Card([
        dbc.CardHeader([
            f"Comparing {len(selected_players)} players",
            dbc.Button("Clear", id='clear-comparison', size='sm', className='float-end')
        ]),
        dbc.CardBody([
            # Side-by-side radar charts
            # Metrics comparison table
        ])
    ], className='comparison-panel')

# Callback to handle player selection
@app.callback(
    Output('selected-players-store', 'data'),
    Input({'type': 'player-select', 'index': ALL}, 'value'),
    State({'type': 'player-select', 'index': ALL}, 'id')
)
def update_selected_players(values, ids):
    selected = []
    for value, id_dict in zip(values, ids):
        if value:
            selected.append(id_dict['index'])
    return selected[:4]  # Max 4 players
```

**Verification:**
- [ ] Can select players via checkbox
- [ ] Comparison panel appears with 2+ players
- [ ] Shows side-by-side radar chart
- [ ] Shows metrics comparison table
- [ ] Clear button works

---

### Task 2.4: Export Functionality

**Objective:** Export data as CSV, Excel, and PDF reports

#### Step 2.4.1: Backend Service

**File to Create:** `src/services/export_service.py`

```python
"""
Export Service

Generates CSV, Excel, and PDF exports of player data and reports.
"""

import io
from typing import List, Dict, Any
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def export_to_csv(data: List[Dict], filename: str = None) -> io.BytesIO:
    """Export data to CSV format."""
    df = pd.DataFrame(data)
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    return buffer


def export_to_excel(data: List[Dict], sheet_name: str = 'Data') -> io.BytesIO:
    """Export data to Excel format."""
    df = pd.DataFrame(data)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    buffer.seek(0)
    return buffer


def export_player_report_pdf(player_data: Dict, metrics: Dict) -> io.BytesIO:
    """
    Generate PDF player profile report.

    Args:
        player_data: Player info (name, position, nationality, etc.)
        metrics: Player metrics dictionary
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph(f"Player Report: {player_data['name']}", styles['Heading1']))
    story.append(Spacer(1, 12))

    # Basic Info
    story.append(Paragraph("Player Information", styles['Heading2']))
    info_data = [
        ['Position', player_data.get('position', 'N/A')],
        ['Nationality', player_data.get('nationality', 'N/A')],
        ['Age', player_data.get('age', 'N/A')],
        ['Current Team', player_data.get('team', 'N/A')],
    ]
    info_table = Table(info_data, colWidths=[150, 300])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 20))

    # Metrics Table
    story.append(Paragraph("Key Metrics", styles['Heading2']))
    metrics_data = [['Metric', 'Value', 'Percentile']]
    for metric_name, metric_value in metrics.items():
        if isinstance(metric_value, dict):
            metrics_data.append([
                metric_name.replace('_', ' ').title(),
                str(metric_value.get('value', 'N/A')),
                f"{metric_value.get('percentile', 'N/A')}%"
            ])
        else:
            metrics_data.append([
                metric_name.replace('_', ' ').title(),
                str(metric_value),
                'N/A'
            ])

    metrics_table = Table(metrics_data, colWidths=[200, 100, 100])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(metrics_table)

    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


def export_comparison_pdf(players: List[Dict], title: str = "Player Comparison") -> io.BytesIO:
    """Generate PDF comparing multiple players."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=30, rightMargin=30)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(title, styles['Heading1']))
    story.append(Spacer(1, 12))

    # Comparison table
    headers = ['Metric'] + [p['name'] for p in players]
    data = [headers]

    metrics_to_compare = ['goals', 'assists', 'minutes', 'xg', 'xag']
    for metric in metrics_to_compare:
        row = [metric.replace('_', ' ').title()]
        for player in players:
            row.append(str(player.get(metric, 'N/A')))
        data.append(row)

    col_width = 400 // len(headers)
    table = Table(data, colWidths=[100] + [col_width] * (len(headers) - 1))
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('BACKGROUND', (0, 1), (0, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(table)

    doc.build(story)
    buffer.seek(0)
    return buffer
```

#### Step 2.4.2: Add to requirements.txt

```
# Add to src/requirements.txt
openpyxl>=3.1.0
reportlab>=4.0.0
```

**Verification:**
- [ ] Export button appears on tables
- [ ] CSV downloads correctly
- [ ] Excel downloads with formatting
- [ ] PDF report generates with charts

---

## 6. Phase 3: Analytics & Intelligence

> **Goal:** Add deep analytics features that differentiate the tool
> **Priority:** HIGH
> **Depends on:** Phase 2

### Task 3.1: Benchmarks & Percentiles Display

**Objective:** Show how players rank against position/league peers

#### Implementation

**File to Modify:** `src/services/metrics_service.py`

```python
def compute_player_percentiles(
    player_id: int,
    season: str,
    cohort_type: str = 'position',  # 'position', 'league', 'age_bracket'
    min_minutes: int = 450
) -> Dict[str, Dict[str, Any]]:
    """
    Compute percentile rankings for a player against a cohort.

    Args:
        player_id: Target player ID
        season: Season name
        cohort_type: How to define the comparison group
        min_minutes: Minimum minutes for cohort inclusion

    Returns:
        {
            'goals_per90': {
                'value': 0.65,
                'percentile': 92,
                'cohort_size': 150,
                'cohort_avg': 0.35,
                'cohort_max': 0.81
            },
            ...
        }
    """
    # Get player's position and metrics
    player_query = """
        SELECT p.position, pss.*
        FROM player_season_stats pss
        JOIN players p ON pss.player_id = p.player_id
        JOIN seasons s ON pss.season_id = s.season_id
        WHERE pss.player_id = %s AND s.season_name = %s
    """
    player_data = fetch_dataframe(player_query, (player_id, season))

    if player_data.empty:
        return {}

    position = player_data.iloc[0]['position']

    # Get cohort data
    cohort_query = """
        SELECT pss.*
        FROM player_season_stats pss
        JOIN players p ON pss.player_id = p.player_id
        JOIN seasons s ON pss.season_id = s.season_id
        WHERE s.season_name = %s
          AND p.position = %s
          AND pss.minutes >= %s
    """
    cohort_data = fetch_dataframe(cohort_query, (season, position, min_minutes))

    if cohort_data.empty:
        return {}

    # Compute percentiles for each metric
    metrics = ['goals', 'assists', 'xg', 'xag', 'shots', 'key_passes', 'tackles', 'interceptions']
    results = {}

    for metric in metrics:
        if metric in player_data.columns and metric in cohort_data.columns:
            player_value = float(player_data.iloc[0][metric] or 0)
            cohort_values = cohort_data[metric].dropna().astype(float)

            if len(cohort_values) > 0:
                percentile = (cohort_values < player_value).sum() / len(cohort_values) * 100
                results[metric] = {
                    'value': round(player_value, 2),
                    'percentile': round(percentile, 1),
                    'cohort_size': len(cohort_values),
                    'cohort_avg': round(cohort_values.mean(), 2),
                    'cohort_max': round(cohort_values.max(), 2)
                }

    return results
```

**File to Modify:** `src/visualization/radar.py`

```python
def create_percentile_bars(percentiles: Dict[str, Dict]) -> go.Figure:
    """Create horizontal bar chart showing percentile rankings."""
    metrics = list(percentiles.keys())
    values = [percentiles[m]['percentile'] for m in metrics]

    # Color based on percentile
    colors = []
    for v in values:
        if v >= 75:
            colors.append('#22c55e')  # Green
        elif v >= 50:
            colors.append('#3b82f6')  # Blue
        elif v >= 25:
            colors.append('#f59e0b')  # Yellow
        else:
            colors.append('#ef4444')  # Red

    fig = go.Figure(go.Bar(
        x=values,
        y=[m.replace('_', ' ').title() for m in metrics],
        orientation='h',
        marker_color=colors,
        text=[f"{v:.0f}%" for v in values],
        textposition='inside'
    ))

    fig.update_layout(
        title="Percentile Rankings vs Position",
        xaxis_title="Percentile",
        xaxis=dict(range=[0, 100]),
        template="plotly_dark"
    )

    return fig
```

**Verification:**
- [ ] Percentile bars show on player dashboard
- [ ] Color coding reflects performance level
- [ ] Cohort size displayed
- [ ] Can switch between cohort types

---

### Task 3.2: Similarity Score Breakdown

**Objective:** Show users which factors drove similarity results

#### Implementation

**File to Modify:** `src/services/similarity_service.py`

The function `similarity_score_breakdown()` already exists - we need to expose it in the UI.

**File to Modify:** `src/app.py`

```python
# Add expandable breakdown to similarity results
def create_similarity_result_with_breakdown(result, breakdown):
    """Create similarity result card with expandable breakdown."""
    return dbc.Card([
        dbc.CardHeader([
            html.Span(f"{result['name']} - {result['similarity_score']:.1%} similar"),
            dbc.Button(
                "Details",
                id={'type': 'breakdown-toggle', 'index': result['player_id']},
                size='sm',
                className='float-end'
            )
        ]),
        dbc.Collapse(
            dbc.CardBody([
                html.H6("Similarity Breakdown"),
                dbc.Progress([
                    dbc.Progress(
                        value=breakdown['role_similarity'] * 60,
                        label=f"Role: {breakdown['role_similarity']:.1%}",
                        color="primary",
                        bar=True
                    ),
                    dbc.Progress(
                        value=breakdown['stats_similarity'] * 40,
                        label=f"Stats: {breakdown['stats_similarity']:.1%}",
                        color="success",
                        bar=True
                    ),
                ], className="mb-3"),
                html.H6("Key Matching Factors"),
                html.Ul([
                    html.Li(f"✓ {factor}") for factor in breakdown.get('matching_factors', [])
                ]),
                html.H6("Key Differences"),
                html.Ul([
                    html.Li(f"✗ {diff}") for diff in breakdown.get('differences', [])
                ])
            ]),
            id={'type': 'breakdown-collapse', 'index': result['player_id']},
            is_open=False
        )
    ])
```

**Verification:**
- [ ] Breakdown panel expands on click
- [ ] Shows role vs stats contribution
- [ ] Lists matching factors
- [ ] Lists key differences

---

### Task 3.3: Data Quality Flags

**Objective:** Show confidence/reliability indicators for player data

**File to Create:** `src/services/quality_service.py`

```python
"""
Data Quality Service

Computes reliability scores and quality flags for player data.
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class DataQualityReport:
    """Quality assessment for a player's data."""
    player_id: int
    reliability_score: float  # 0-100
    flags: list
    sample_size: str  # 'low', 'medium', 'high'
    data_completeness: float  # 0-100


def assess_player_data_quality(
    player_id: int,
    season: str = None
) -> DataQualityReport:
    """
    Assess data quality for a player.

    Returns reliability score and any quality flags.
    """
    query = """
        SELECT
            pss.minutes,
            pss.matches_played,
            pss.goals IS NOT NULL as has_goals,
            pss.xg IS NOT NULL as has_xg,
            pss.tackles IS NOT NULL as has_defensive,
            pss.key_passes IS NOT NULL as has_creative
        FROM player_season_stats pss
        JOIN seasons s ON pss.season_id = s.season_id
        WHERE pss.player_id = %s
    """

    params = [player_id]
    if season:
        query += " AND s.season_name = %s"
        params.append(season)

    data = fetch_dataframe(query, params)

    if data.empty:
        return DataQualityReport(
            player_id=player_id,
            reliability_score=0,
            flags=['no_data'],
            sample_size='none',
            data_completeness=0
        )

    row = data.iloc[0]
    flags = []

    # Sample size assessment
    minutes = row['minutes'] or 0
    matches = row['matches_played'] or 0

    if minutes < 450:
        sample_size = 'low'
        flags.append('low_minutes')
    elif minutes < 1800:
        sample_size = 'medium'
    else:
        sample_size = 'high'

    if matches < 5:
        flags.append('few_matches')

    # Data completeness
    completeness_checks = [
        row.get('has_goals', False),
        row.get('has_xg', False),
        row.get('has_defensive', False),
        row.get('has_creative', False)
    ]
    data_completeness = sum(completeness_checks) / len(completeness_checks) * 100

    if not row.get('has_xg', False):
        flags.append('no_xg_data')

    # Calculate reliability score
    reliability = 50  # Base score
    reliability += min(30, minutes / 60)  # Up to 30 points for minutes
    reliability += data_completeness * 0.2  # Up to 20 points for completeness

    return DataQualityReport(
        player_id=player_id,
        reliability_score=min(100, reliability),
        flags=flags,
        sample_size=sample_size,
        data_completeness=data_completeness
    )
```

**Verification:**
- [ ] Quality badge shows on player cards
- [ ] Tooltip explains quality factors
- [ ] Low-quality data has visual warning

---

### Task 3.4: Trend Alerts

**Objective:** Auto-detect significant metric changes

**File to Create:** `src/services/alerts_service.py`

```python
"""
Trend Alerts Service

Detects significant changes in player performance across seasons.
"""

from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class TrendAlert:
    """Represents a significant trend detection."""
    player_id: int
    player_name: str
    metric: str
    change_type: str  # 'improvement', 'decline'
    percentage_change: float
    from_value: float
    to_value: float
    seasons: tuple


def detect_trends(
    min_change_pct: float = 25.0,
    min_minutes: int = 900,
    metrics: List[str] = None
) -> List[TrendAlert]:
    """
    Detect significant trends across all players.

    Args:
        min_change_pct: Minimum percentage change to flag
        min_minutes: Minimum minutes in both seasons
        metrics: Metrics to analyze
    """
    if metrics is None:
        metrics = ['goals', 'assists', 'xg', 'key_passes', 'tackles']

    alerts = []

    query = """
        WITH season_comparison AS (
            SELECT
                p.player_id,
                p.player_name,
                s.season_name,
                pss.goals, pss.assists, pss.xg, pss.key_passes, pss.tackles,
                pss.minutes,
                LAG(pss.goals) OVER (PARTITION BY p.player_id ORDER BY s.season_name) as prev_goals,
                LAG(pss.assists) OVER (PARTITION BY p.player_id ORDER BY s.season_name) as prev_assists,
                LAG(pss.xg) OVER (PARTITION BY p.player_id ORDER BY s.season_name) as prev_xg,
                LAG(pss.minutes) OVER (PARTITION BY p.player_id ORDER BY s.season_name) as prev_minutes,
                LAG(s.season_name) OVER (PARTITION BY p.player_id ORDER BY s.season_name) as prev_season
            FROM player_season_stats pss
            JOIN players p ON pss.player_id = p.player_id
            JOIN seasons s ON pss.season_id = s.season_id
            WHERE pss.minutes >= %s
        )
        SELECT * FROM season_comparison
        WHERE prev_season IS NOT NULL AND prev_minutes >= %s
    """

    data = fetch_dataframe(query, (min_minutes, min_minutes))

    for _, row in data.iterrows():
        for metric in metrics:
            curr_val = row.get(metric, 0) or 0
            prev_val = row.get(f'prev_{metric}', 0) or 0

            if prev_val == 0:
                continue

            pct_change = ((curr_val - prev_val) / prev_val) * 100

            if abs(pct_change) >= min_change_pct:
                alerts.append(TrendAlert(
                    player_id=row['player_id'],
                    player_name=row['player_name'],
                    metric=metric,
                    change_type='improvement' if pct_change > 0 else 'decline',
                    percentage_change=round(pct_change, 1),
                    from_value=prev_val,
                    to_value=curr_val,
                    seasons=(row['prev_season'], row['season_name'])
                ))

    # Sort by absolute change magnitude
    alerts.sort(key=lambda x: abs(x.percentage_change), reverse=True)

    return alerts
```

**Verification:**
- [ ] Alerts page shows significant trends
- [ ] Can filter by improvement/decline
- [ ] Links to player profile

---

## 7. Phase 4: Advanced Workflows

> **Goal:** Build complete scouting workflows
> **Priority:** MEDIUM
> **Depends on:** Phase 3

### Task 4.1: Replace Player Workflow

**Objective:** Find replacements for departing players

**File to Create:** `src/services/replacement_service.py`

```python
"""
Player Replacement Service

Finds and ranks potential replacements for outgoing players.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from services.similarity_service import find_similar_players, similarity_score_breakdown
from services.role_service import build_role_vector, explain_role_vector
from services.metrics_service import compute_player_season_metrics


@dataclass
class ReplacementCandidate:
    """A potential replacement candidate."""
    player_id: int
    player_name: str
    similarity_score: float
    role_fit: float
    stats_fit: float
    age: int
    position: str
    team: str
    league: str
    strengths: List[str]
    weaknesses: List[str]
    metrics: Dict[str, float]


def find_replacements(
    outgoing_player_id: int,
    season: str,
    filters: Dict[str, Any] = None,
    n_candidates: int = 20
) -> Dict[str, Any]:
    """
    Find replacement candidates for an outgoing player.

    Args:
        outgoing_player_id: ID of player leaving
        season: Season to base analysis on
        filters: Optional filters (age_max, leagues, min_minutes)
        n_candidates: Number of candidates to return

    Returns:
        {
            'outgoing_player': {...player details...},
            'profile': {...role and metrics profile...},
            'candidates': [ReplacementCandidate, ...]
        }
    """
    if filters is None:
        filters = {}

    # Get outgoing player details
    outgoing_metrics = compute_player_season_metrics(outgoing_player_id, season)
    outgoing_role = build_role_vector(outgoing_player_id, season)
    role_explanation = explain_role_vector(outgoing_role)

    # Find similar players
    similar = find_similar_players(
        player_id=outgoing_player_id,
        season=season,
        n_similar=n_candidates,
        filters=filters
    )

    # Build candidate profiles
    candidates = []
    for player in similar:
        breakdown = similarity_score_breakdown(
            outgoing_player_id,
            player['player_id'],
            season
        )

        # Identify strengths and weaknesses vs outgoing
        player_metrics = compute_player_season_metrics(player['player_id'], season)
        strengths = []
        weaknesses = []

        compare_metrics = ['goals', 'assists', 'xg', 'key_passes', 'tackles']
        for metric in compare_metrics:
            outgoing_val = outgoing_metrics.get(metric, 0)
            player_val = player_metrics.get(metric, 0)

            if outgoing_val and player_val:
                diff_pct = ((player_val - outgoing_val) / outgoing_val) * 100
                metric_name = metric.replace('_', ' ').title()

                if diff_pct > 10:
                    strengths.append(f"Better {metric_name} (+{diff_pct:.0f}%)")
                elif diff_pct < -10:
                    weaknesses.append(f"Lower {metric_name} ({diff_pct:.0f}%)")

        candidates.append(ReplacementCandidate(
            player_id=player['player_id'],
            player_name=player['name'],
            similarity_score=player['similarity_score'],
            role_fit=breakdown.get('role_similarity', 0),
            stats_fit=breakdown.get('stats_similarity', 0),
            age=player.get('age', 0),
            position=player.get('position', ''),
            team=player.get('team', ''),
            league=player.get('league', ''),
            strengths=strengths[:3],
            weaknesses=weaknesses[:3],
            metrics=player_metrics
        ))

    return {
        'outgoing_player': {
            'id': outgoing_player_id,
            'metrics': outgoing_metrics,
            'role_explanation': role_explanation
        },
        'candidates': candidates
    }


def compare_replacement(
    outgoing_id: int,
    replacement_id: int,
    season: str
) -> Dict[str, Any]:
    """
    Detailed side-by-side comparison of outgoing vs replacement.
    """
    outgoing_metrics = compute_player_season_metrics(outgoing_id, season)
    replacement_metrics = compute_player_season_metrics(replacement_id, season)

    outgoing_role = build_role_vector(outgoing_id, season)
    replacement_role = build_role_vector(replacement_id, season)

    breakdown = similarity_score_breakdown(outgoing_id, replacement_id, season)

    # Metric-by-metric comparison
    comparison = {}
    for metric in outgoing_metrics:
        if metric in replacement_metrics:
            comparison[metric] = {
                'outgoing': outgoing_metrics[metric],
                'replacement': replacement_metrics[metric],
                'difference': replacement_metrics[metric] - outgoing_metrics[metric],
                'better': replacement_metrics[metric] > outgoing_metrics[metric]
            }

    return {
        'similarity_breakdown': breakdown,
        'metrics_comparison': comparison,
        'role_comparison': {
            'outgoing': explain_role_vector(outgoing_role),
            'replacement': explain_role_vector(replacement_role)
        }
    }
```

**Verification:**
- [ ] Can select outgoing player
- [ ] Shows player profile summary
- [ ] Lists ranked replacement candidates
- [ ] Side-by-side comparison works

---

### Task 4.2: Role Vector Visualization

**Objective:** Visualize 20D role vectors as "Player DNA"

**File to Create:** `src/visualization/role_viz.py`

```python
"""
Role Vector Visualization

Visualizes the 20-dimensional role vectors as intuitive graphics.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np


def create_role_fingerprint(role_vector: np.ndarray, player_name: str) -> go.Figure:
    """
    Create a unique 'fingerprint' visualization of a player's role vector.

    The 20 dimensions are grouped into interpretable categories:
    - Position (dims 0-1): avg_x, avg_y
    - Movement (dims 2-3): spread_x, spread_y
    - Zone (dims 4-9): thirds and width distribution
    - Passing (dims 10-13): direction tendencies
    - Style (dims 14-19): progressive, spatial, involvement
    """
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Pitch Position', 'Zone Distribution',
                       'Pass Direction', 'Play Style'),
        specs=[[{'type': 'scatter'}, {'type': 'bar'}],
               [{'type': 'pie'}, {'type': 'polar'}]]
    )

    # 1. Pitch position scatter (avg_x, avg_y)
    fig.add_trace(
        go.Scatter(
            x=[role_vector[0]],
            y=[role_vector[1]],
            mode='markers+text',
            marker=dict(size=20, color='#3b82f6'),
            text=[player_name],
            textposition='top center',
            name='Position'
        ),
        row=1, col=1
    )

    # Add pitch outline
    fig.add_shape(
        type='rect', x0=0, y0=0, x1=100, y1=100,
        line=dict(color='white', width=1),
        row=1, col=1
    )

    # 2. Zone distribution bar chart
    zones = ['Def Third', 'Mid Third', 'Att Third', 'Left', 'Center', 'Right']
    zone_values = role_vector[4:10]
    fig.add_trace(
        go.Bar(
            x=zones,
            y=zone_values,
            marker_color=['#ef4444', '#f59e0b', '#22c55e', '#8b5cf6', '#3b82f6', '#ec4899']
        ),
        row=1, col=2
    )

    # 3. Pass direction pie chart
    pass_labels = ['Forward', 'Backward', 'Lateral']
    pass_values = role_vector[10:13]
    fig.add_trace(
        go.Pie(
            labels=pass_labels,
            values=pass_values,
            hole=0.4
        ),
        row=2, col=1
    )

    # 4. Play style polar chart
    style_metrics = ['Progressive', 'Box Activity', 'High Regains',
                    'Width', 'Verticality', 'Involvement']
    style_values = list(role_vector[13:19]) + [role_vector[13]]  # Close the polygon

    fig.add_trace(
        go.Scatterpolar(
            r=style_values,
            theta=style_metrics + [style_metrics[0]],
            fill='toself',
            fillcolor='rgba(59, 130, 246, 0.3)',
            line=dict(color='#3b82f6', width=2)
        ),
        row=2, col=2
    )

    fig.update_layout(
        title=f"Role Profile: {player_name}",
        template="plotly_dark",
        showlegend=False,
        height=700
    )

    return fig


def create_role_comparison(
    role_vector_1: np.ndarray,
    role_vector_2: np.ndarray,
    name_1: str,
    name_2: str
) -> go.Figure:
    """Create overlay comparison of two role vectors."""

    # Create polar chart with both players
    style_metrics = ['Progressive', 'Box Activity', 'High Regains',
                    'Width', 'Verticality', 'Involvement']

    fig = go.Figure()

    # Player 1
    values_1 = list(role_vector_1[13:19]) + [role_vector_1[13]]
    fig.add_trace(go.Scatterpolar(
        r=values_1,
        theta=style_metrics + [style_metrics[0]],
        fill='toself',
        fillcolor='rgba(59, 130, 246, 0.3)',
        line=dict(color='#3b82f6', width=2),
        name=name_1
    ))

    # Player 2
    values_2 = list(role_vector_2[13:19]) + [role_vector_2[13]]
    fig.add_trace(go.Scatterpolar(
        r=values_2,
        theta=style_metrics + [style_metrics[0]],
        fill='toself',
        fillcolor='rgba(239, 68, 68, 0.3)',
        line=dict(color='#ef4444', width=2),
        name=name_2
    ))

    fig.update_layout(
        title=f"Role Comparison: {name_1} vs {name_2}",
        template="plotly_dark",
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100])
        )
    )

    return fig
```

**Verification:**
- [ ] Role fingerprint shows for each player
- [ ] Comparison overlay works
- [ ] Visual is intuitive and informative

---

### Task 4.3: Position Flexibility Score

**Objective:** Score how well players fit alternative positions

**File to Modify:** `src/services/role_service.py`

```python
# Add to role_service.py

POSITION_ROLE_PROFILES = {
    'ST': {'avg_x': (70, 90), 'attacking_third': (60, 100), 'box_touches': 'high'},
    'CF': {'avg_x': (60, 80), 'attacking_third': (50, 80), 'key_passes': 'high'},
    'LW': {'avg_x': (60, 85), 'left_zone': (40, 80), 'dribbles': 'high'},
    'RW': {'avg_x': (60, 85), 'right_zone': (40, 80), 'dribbles': 'high'},
    'CAM': {'avg_x': (55, 75), 'center_zone': (50, 90), 'key_passes': 'high'},
    'CM': {'avg_x': (40, 60), 'center_zone': (60, 100), 'passes': 'high'},
    'CDM': {'avg_x': (30, 50), 'middle_third': (50, 80), 'tackles': 'high'},
    'LB': {'avg_x': (20, 50), 'left_zone': (40, 80), 'defensive_third': (30, 70)},
    'RB': {'avg_x': (20, 50), 'right_zone': (40, 80), 'defensive_third': (30, 70)},
    'CB': {'avg_x': (15, 35), 'center_zone': (60, 100), 'defensive_third': (50, 90)},
}


def compute_position_flexibility(
    player_id: int,
    season: str,
    current_position: str = None
) -> Dict[str, float]:
    """
    Compute how well a player fits each position.

    Returns:
        {
            'ST': 85.2,
            'CF': 78.5,
            'LW': 62.1,
            ...
        }
    """
    role_vector = build_role_vector(player_id, season)

    if role_vector is None:
        return {}

    flexibility_scores = {}

    for position, profile in POSITION_ROLE_PROFILES.items():
        score = 100.0

        # Check avg_x range
        if 'avg_x' in profile:
            min_x, max_x = profile['avg_x']
            player_x = role_vector[0]
            if player_x < min_x:
                score -= (min_x - player_x) * 2
            elif player_x > max_x:
                score -= (player_x - max_x) * 2

        # Check zone distributions
        for zone_key in ['attacking_third', 'middle_third', 'defensive_third',
                        'left_zone', 'center_zone', 'right_zone']:
            if zone_key in profile:
                min_val, max_val = profile[zone_key]
                # Map zone key to vector index
                zone_idx = {
                    'defensive_third': 4, 'middle_third': 5, 'attacking_third': 6,
                    'left_zone': 7, 'center_zone': 8, 'right_zone': 9
                }.get(zone_key, 4)

                player_val = role_vector[zone_idx]
                if player_val < min_val:
                    score -= (min_val - player_val) * 0.5
                elif player_val > max_val:
                    score -= (player_val - max_val) * 0.5

        flexibility_scores[position] = max(0, min(100, score))

    # Sort by score
    flexibility_scores = dict(sorted(
        flexibility_scores.items(),
        key=lambda x: x[1],
        reverse=True
    ))

    return flexibility_scores
```

**Verification:**
- [ ] Position flexibility shows on player profile
- [ ] Scores seem reasonable
- [ ] Can filter similarity search by alternative positions

---

### Task 4.4: Similar Players in Squad

**Objective:** When viewing a target, show similar players already on the team

**File to Modify:** `src/services/similarity_service.py`

```python
def find_similar_in_squad(
    target_player_id: int,
    squad_team_id: int,
    season: str,
    n_similar: int = 5
) -> List[Dict[str, Any]]:
    """
    Find players in a specific squad who are similar to the target.

    Useful for: "Do we already have someone like this player?"

    Args:
        target_player_id: Player we're considering signing
        squad_team_id: Team ID of our squad (e.g., Chelsea)
        season: Season for analysis
        n_similar: Number of similar squad players to return
    """
    # Get squad player IDs
    squad_query = """
        SELECT DISTINCT player_id
        FROM player_season_stats
        WHERE team_id = %s
    """
    squad_ids = [row[0] for row in execute_query(squad_query, (squad_team_id,))]

    if not squad_ids:
        return []

    # Find similarity with squad players only
    similar = find_similar_players(
        player_id=target_player_id,
        season=season,
        n_similar=n_similar,
        filters={'player_ids': squad_ids}
    )

    return similar
```

**UI Integration:**
- Add "Similar in Our Squad" panel on target player view
- Show warning if high similarity exists: "You already have [Player X] who is 85% similar"

**Verification:**
- [ ] Shows squad similarity on target player
- [ ] Warning appears for high overlap

---

## 8. Phase 5: LLM Integration

> **Goal:** Complete and enhance natural language query capabilities
> **Priority:** HIGH
> **Depends on:** Phase 2

### Task 5.1: Complete LLM API Integration

**Objective:** Implement actual API calls (currently placeholder)

**File to Modify:** `src/services/llm_service.py`

```python
# Replace the placeholder call_llm_api function

import anthropic
import openai
from typing import Dict, Any


def call_llm_api(prompt: str, config: Dict[str, Any]) -> str:
    """
    Call LLM API for query parsing.

    Args:
        prompt: The prompt to send
        config: Configuration dict with provider, model, etc.

    Returns:
        LLM response text
    """
    provider = config.get('provider', 'anthropic')

    if provider == 'anthropic':
        return _call_anthropic(prompt, config)
    elif provider == 'openai':
        return _call_openai(prompt, config)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def _call_anthropic(prompt: str, config: Dict[str, Any]) -> str:
    """Call Anthropic Claude API."""
    import os

    client = anthropic.Anthropic(
        api_key=os.environ.get('ANTHROPIC_API_KEY')
    )

    message = client.messages.create(
        model=config.get('model', 'claude-sonnet-4-20250514'),
        max_tokens=config.get('max_tokens', 1000),
        temperature=config.get('temperature', 0.1),
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return message.content[0].text


def _call_openai(prompt: str, config: Dict[str, Any]) -> str:
    """Call OpenAI API."""
    import os

    client = openai.OpenAI(
        api_key=os.environ.get('OPENAI_API_KEY')
    )

    response = client.chat.completions.create(
        model=config.get('model', 'gpt-4'),
        max_tokens=config.get('max_tokens', 1000),
        temperature=config.get('temperature', 0.1),
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content
```

**Add to requirements.txt:**
```
anthropic>=0.18.0
openai>=1.0.0
```

**Verification:**
- [ ] API calls work with valid key
- [ ] Handles API errors gracefully
- [ ] Rate limiting works

---

### Task 5.2: Tiered Parsing (Regex + LLM Fallback)

**Objective:** Use fast regex for simple queries, LLM for complex

**File to Create:** `src/services/simple_parser.py`

```python
"""
Simple Query Parser

Fast regex-based parsing for common query patterns.
Falls back to LLM for complex queries.
"""

import re
from typing import Dict, Any, Optional


# Common query patterns
PATTERNS = {
    'similarity': [
        r'(?:find\s+)?players?\s+(?:like|similar\s+to)\s+(.+)',
        r'who\s+(?:plays?|is)\s+like\s+(.+)',
        r'(.+)\s+alternatives?',
    ],
    'comparison': [
        r'compare\s+(.+)\s+(?:and|vs\.?|versus)\s+(.+)',
        r'(.+)\s+(?:vs\.?|versus)\s+(.+)',
    ],
    'leaderboard': [
        r'(?:top|best)\s+(\d+)?\s*(.+?)(?:\s+in\s+(.+))?$',
        r'who\s+(?:has\s+the\s+)?most\s+(.+)',
    ],
    'filter': [
        r'(.+)\s+under\s+(\d+)(?:\s+years?)?',
        r'(.+)\s+from\s+(.+)',
        r'young\s+(.+)',
    ]
}


def parse_simple_query(query: str) -> Optional[Dict[str, Any]]:
    """
    Try to parse query with regex patterns.

    Returns parsed query dict if successful, None if needs LLM.
    """
    query = query.lower().strip()

    # Try similarity patterns
    for pattern in PATTERNS['similarity']:
        match = re.match(pattern, query, re.IGNORECASE)
        if match:
            player_name = match.group(1).strip()
            return {
                'query_type': 'similarity',
                'base_player_name': player_name,
                'similarity_search': True,
                'n_results': 10
            }

    # Try comparison patterns
    for pattern in PATTERNS['comparison']:
        match = re.match(pattern, query, re.IGNORECASE)
        if match:
            return {
                'query_type': 'comparison',
                'players': [match.group(1).strip(), match.group(2).strip()]
            }

    # Try leaderboard patterns
    for pattern in PATTERNS['leaderboard']:
        match = re.match(pattern, query, re.IGNORECASE)
        if match:
            groups = match.groups()
            return {
                'query_type': 'leaderboard',
                'count': int(groups[0]) if groups[0] else 10,
                'metric': groups[1].strip() if len(groups) > 1 else 'goals',
                'league': groups[2].strip() if len(groups) > 2 and groups[2] else None
            }

    # Try filter patterns
    for pattern in PATTERNS['filter']:
        match = re.match(pattern, query, re.IGNORECASE)
        if match:
            # Extract filters - return partial, will need more processing
            return {
                'query_type': 'filtered_search',
                'raw_match': match.groups(),
                'needs_refinement': True
            }

    # No simple pattern matched - needs LLM
    return None


def parse_query_with_fallback(query: str, config: Dict) -> Dict[str, Any]:
    """
    Parse query using tiered approach.

    1. Try simple regex patterns (fast, free)
    2. Fall back to LLM (slower, costs money)
    """
    # Try simple parsing first
    simple_result = parse_simple_query(query)

    if simple_result and not simple_result.get('needs_refinement'):
        simple_result['parse_method'] = 'regex'
        return simple_result

    # Fall back to LLM
    from services.llm_service import parse_query

    llm_result = parse_query(query, config)
    llm_result['parse_method'] = 'llm'

    return llm_result
```

**Verification:**
- [ ] Simple queries parsed instantly
- [ ] Complex queries fall back to LLM
- [ ] Parse method logged for debugging

---

### Task 5.3: LLM Parser Test Suite

**Objective:** Regression tests for query parsing

**File to Create:** `src/tests/test_llm_parser_golden.py`

```python
"""
Golden Test Suite for LLM Query Parser

Tests query parsing against expected outputs.
Run with: pytest tests/test_llm_parser_golden.py -v
"""

import pytest
from services.llm_service import parse_query
from services.simple_parser import parse_simple_query


# Golden test cases: (input_query, expected_output_fields)
GOLDEN_TESTS = [
    # Similarity queries
    (
        "Find players like Harry Kane",
        {
            'base_player_name': 'Harry Kane',
            'similarity_search': True
        }
    ),
    (
        "Who plays like Kevin De Bruyne but younger",
        {
            'base_player_name': 'Kevin De Bruyne',
            'similarity_search': True,
            'age_max': lambda x: x is not None and x < 30
        }
    ),
    (
        "Strikers similar to Haaland in La Liga",
        {
            'base_player_name': 'Haaland',
            'position': 'FW',
            'leagues': lambda x: 'La Liga' in (x or [])
        }
    ),

    # Comparison queries
    (
        "Compare Salah and Mane",
        {
            'query_type': 'comparison',
            'players': lambda x: 'Salah' in str(x) and 'Mane' in str(x)
        }
    ),

    # Leaderboard queries
    (
        "Top 10 scorers in Premier League",
        {
            'query_type': 'leaderboard',
            'metric': lambda x: 'goal' in x.lower() or 'scor' in x.lower(),
            'league': lambda x: 'Premier' in str(x)
        }
    ),

    # Filter queries
    (
        "Young midfielders under 23 with good passing",
        {
            'position': lambda x: x in ['MF', 'CM', 'CDM', 'CAM'],
            'age_max': lambda x: x is not None and x <= 23
        }
    ),

    # Metric-specific queries
    (
        "Players with xG over 0.5 per 90",
        {
            'metrics': lambda x: 'xg' in str(x).lower() or 'xg_per90' in (x or [])
        }
    ),

    # Edge cases
    (
        "Find me someone",
        {
            # Should handle vague queries gracefully
            'similarity_search': lambda x: x in [True, False, None]
        }
    ),
]


class TestSimpleParser:
    """Test regex-based simple parser."""

    def test_similarity_patterns(self):
        result = parse_simple_query("players like Messi")
        assert result is not None
        assert result.get('similarity_search') == True
        assert 'messi' in result.get('base_player_name', '').lower()

    def test_comparison_patterns(self):
        result = parse_simple_query("compare Kane and Haaland")
        assert result is not None
        assert result.get('query_type') == 'comparison'

    def test_leaderboard_patterns(self):
        result = parse_simple_query("top 5 scorers")
        assert result is not None
        assert result.get('query_type') == 'leaderboard'
        assert result.get('count') == 5

    def test_returns_none_for_complex(self):
        result = parse_simple_query("Find creative midfielders who can play as a false 9 with good aerial ability")
        assert result is None  # Should need LLM


class TestGoldenCases:
    """Test against golden expected outputs."""

    @pytest.mark.parametrize("query,expected", GOLDEN_TESTS)
    def test_golden_case(self, query, expected, llm_config):
        # Try simple parser first
        result = parse_simple_query(query)

        # If simple parser returns None, we'd normally call LLM
        # For testing without API, we skip LLM tests
        if result is None:
            pytest.skip("Requires LLM API for this test")

        # Validate expected fields
        for field, expected_value in expected.items():
            if callable(expected_value):
                assert expected_value(result.get(field)), \
                    f"Field {field} failed validation. Got: {result.get(field)}"
            else:
                assert result.get(field) == expected_value, \
                    f"Field {field} mismatch. Expected {expected_value}, got {result.get(field)}"


@pytest.fixture
def llm_config():
    """LLM configuration for testing."""
    return {
        'provider': 'anthropic',
        'model': 'claude-sonnet-4-20250514',
        'temperature': 0.1,
        'max_tokens': 1000
    }
```

**Verification:**
- [ ] All golden tests pass
- [ ] Tests run in CI pipeline
- [ ] Easy to add new test cases

---

### Task 5.4: User-Tunable Similarity Weights

**Objective:** Allow users to adjust role vs stats weight

**File to Modify:** `src/app.py`

```python
# Add weight controls to similarity search panel
similarity_controls = dbc.Card([
    dbc.CardHeader("Search Parameters"),
    dbc.CardBody([
        # Existing controls...

        html.Hr(),
        html.H6("Similarity Weights"),

        html.Label("Role vs Stats Balance"),
        dcc.Slider(
            id='role-stats-weight',
            min=0,
            max=100,
            step=10,
            value=60,  # Default: 60% role, 40% stats
            marks={
                0: 'All Stats',
                50: 'Balanced',
                100: 'All Role'
            },
            tooltip={'placement': 'bottom', 'always_visible': True}
        ),

        html.Hr(),
        html.Label("Metric Emphasis"),
        dcc.Dropdown(
            id='metric-emphasis-preset',
            options=[
                {'label': 'Balanced (Default)', 'value': 'balanced'},
                {'label': 'Goalscorer Focus', 'value': 'goalscorer'},
                {'label': 'Creator Focus', 'value': 'creator'},
                {'label': 'Defensive Focus', 'value': 'defensive'},
                {'label': 'Athletic Focus', 'value': 'athletic'},
            ],
            value='balanced'
        )
    ])
])

# Modify similarity search callback to use weights
@app.callback(
    Output('similarity-results', 'children'),
    Input('run-similarity-btn', 'n_clicks'),
    State('role-stats-weight', 'value'),
    State('metric-emphasis-preset', 'value'),
    # ... other states
)
def run_similarity_search(n_clicks, role_weight, metric_preset, ...):
    stats_weight = 100 - role_weight

    # Adjust metric weights based on preset
    metric_weights = get_metric_weights_for_preset(metric_preset)

    results = find_similar_players(
        player_id=player_id,
        season=season,
        role_weight=role_weight / 100,
        stats_weight=stats_weight / 100,
        metric_weights=metric_weights,
        ...
    )

    return render_similarity_results(results)
```

**Verification:**
- [ ] Weight slider appears in UI
- [ ] Changing weights affects results
- [ ] Presets apply correctly

---

## 9. Phase 6: Polish & Documentation

> **Goal:** Production readiness and maintainability
> **Priority:** MEDIUM
> **Depends on:** All previous phases

### Task 6.1: Scout Report Templates

**Objective:** Professional PDF exports for presentations

**File to Modify:** `src/services/export_service.py`

Add templates:
- Player Profile (1-page summary)
- Comparison Report (2-3 players)
- Shortlist Summary (10+ players overview)
- Replacement Analysis (outgoing vs candidates)

### Task 6.2: User Documentation

**File to Create:** `docs/USER_GUIDE.md`

Contents:
- Getting started
- Understanding metrics
- Using similarity search
- Managing watchlists
- Interpreting results

### Task 6.3: API Documentation

**File to Create:** `docs/API.md`

Document all service functions with:
- Function signatures
- Parameter descriptions
- Return types
- Example usage

### Task 6.4: Deployment Guide

**File to Create:** `docs/DEPLOYMENT.md`

Contents:
- Docker deployment
- Environment variables
- Database setup
- Monitoring setup

---

## 10. Deferred Items

These items are intentionally deprioritized:

| Item | Reason | When to Revisit |
|------|--------|-----------------|
| Redis caching | Memory cache sufficient for now | When hitting performance limits |
| FastAPI service layer | Dash works fine for internal tool | When building external API |
| JSON structured logging | Nice-to-have | Production deployment |
| Automated Dash smoke tests | Complex setup, low ROI | After core features stable |
| Log correlation IDs | Enterprise feature | Multi-service architecture |
| Ops runbooks | Need production first | Post-deployment |

---

## 11. File Reference Guide

### Quick Reference: Key Files

| Purpose | File Path |
|---------|-----------|
| Main app entry | `src/app.py` |
| Metrics computation | `src/services/metrics_service.py` |
| Similarity algorithm | `src/services/similarity_service.py` |
| Role vectors | `src/services/role_service.py` |
| LLM parsing | `src/services/llm_service.py` |
| Metrics definitions | `src/config/metrics_registry.yaml` |
| App settings | `src/config/settings.yaml` |
| Database access | `src/utils/db.py` |
| Validation | `src/utils/validation.py` |
| Radar charts | `src/visualization/radar.py` |
| Scatter plots | `src/visualization/scatter.py` |
| Tests | `src/tests/` |
| ETL CLI | `Data-etl-pipeline/cli.py` |
| ETL web UI | `Data-etl-pipeline/server/app.py` |

### New Files to Create (This Plan)

| File | Phase | Purpose |
|------|-------|---------|
| `.github/workflows/ci.yml` | 1.1 | CI pipeline |
| `.pre-commit-config.yaml` | 1.1 | Pre-commit hooks |
| `src/Dockerfile` | 1.3 | App containerization |
| `docker-compose.yml` | 1.3 | Full stack compose |
| `database/migrations/002_watchlists.sql` | 2.1 | Watchlist schema |
| `src/services/watchlist_service.py` | 2.1 | Watchlist logic |
| `src/services/export_service.py` | 2.4 | Export functionality |
| `src/services/quality_service.py` | 3.3 | Data quality |
| `src/services/alerts_service.py` | 3.4 | Trend alerts |
| `src/services/replacement_service.py` | 4.1 | Replacement workflow |
| `src/visualization/role_viz.py` | 4.2 | Role visualization |
| `src/services/simple_parser.py` | 5.2 | Regex parsing |
| `src/tests/test_llm_parser_golden.py` | 5.3 | Parser tests |

---

## 12. Testing Requirements

### Unit Tests (Required)

Each new service must have corresponding tests:

```
tests/
├── test_watchlist_service.py
├── test_export_service.py
├── test_quality_service.py
├── test_alerts_service.py
├── test_replacement_service.py
├── test_simple_parser.py
└── test_llm_parser_golden.py
```

### Test Coverage Targets

| Component | Minimum Coverage |
|-----------|------------------|
| Services | 80% |
| Utils | 90% |
| Visualization | 50% |
| App callbacks | 30% |

### Critical Invariants (Must Always Pass)

From `tests/test_invariants.py`:
1. Player vs self similarity = 1.0
2. All metrics in registry are valid
3. Database is read-only
4. No SQL injection possible
5. LLM can't hallucinate metrics

---

## 13. Success Metrics

### User Experience

| Metric | Target |
|--------|--------|
| Page load time | < 2 seconds |
| Similarity search | < 5 seconds |
| Export generation | < 10 seconds |

### Data Quality

| Metric | Target |
|--------|--------|
| Data freshness | < 7 days |
| League coverage | > 90% top 5 leagues |
| Metric completeness | > 95% |

### Development

| Metric | Target |
|--------|--------|
| Test coverage | > 80% |
| CI pass rate | > 95% |
| Build time | < 5 minutes |

---

## Appendix: Command Reference

### Development Commands

```bash
# Start scouting app
cd /Users/divyanshshrivastava/Scouting_project/src
python app.py

# Start ETL UI
cd /Users/divyanshshrivastava/Scouting_project/Data-etl-pipeline
python server/app.py

# Run tests
cd /Users/divyanshshrivastava/Scouting_project/src
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=services --cov=utils --cov-report=html

# Lint code
flake8 src/ --max-line-length=120
black src/ --check
mypy src/ --ignore-missing-imports

# Docker commands
docker-compose up --build
docker-compose down
docker-compose logs -f scouting-app
```

### Database Commands

```bash
# Connect to database
psql -h localhost -p 5434 -U postgres -d football_data

# Run migration
psql -h localhost -p 5434 -U postgres -d football_data -f database/migrations/002_watchlists.sql

# Check data stats
psql -h localhost -p 5434 -U postgres -d football_data -c "SELECT COUNT(*) FROM players;"
```

---

**Document End**

*This plan is designed to be read and executed by development agents (Claude Code, Codex, Antigravity) as well as human developers. Each task includes specific file paths, code examples, and verification steps.*
