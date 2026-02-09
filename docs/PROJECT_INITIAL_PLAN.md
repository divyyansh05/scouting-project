# Chelsea FC Data-Driven Scouting System: Complete Project Plan

## 1. Project Idea & Elevator Pitch

**"Chelsea Intelligence Hub: Automated Scouting & Squad Optimization"**

This project builds an end-to-end data-driven scouting system for Chelsea FC that automates player discovery, comparison, and squad planning using free, open football data sources.

The tool produces actionable deliverables:
1. A dynamic shortlist of 10 candidates per position ranked by tactical fit
2. Interactive dashboards comparing players across 25+ metrics
3. Budget simulation tools respecting FFP constraints

---

## 2. Scope & Objectives (Mapped to Academic Deliverables)

### Core Objectives

| Objective | Description |
|-----------|-------------|
| **Data Engineering** | Build a reproducible ETL pipeline ingesting 38,000+ matches from 5 leagues (2018-2024 seasons) |
| **Feature Engineering** | Compute 25+ scouting-relevant metrics per player (per-90 normalized, age-adjusted) |
| **Player Similarity Engine** | Implement cosine similarity + dimensionality reduction to find tactical replacements |
| **Squad Optimization** | Simulate transfer scenarios with budget/salary constraints (£200M budget, FFP compliance) |
| **Visualization Layer** | Deploy 5 interactive dashboards for position-specific analysis |

### Academic Deliverables Mapping

| Deliverable | Requirement | Output Artifact |
|-------------|-------------|-----------------|
| GitHub Repository | ETL code, feature engineering, model training | `/src` folder with Python modules, `requirements.txt`, `README.md` |
| Interactive Tool | Streamlit dashboard or Tableau workbook | Deployed Streamlit app + `/dashboard` folder |
| PDF Presentation | 15-slide deck: problem, method, insights, business impact | `Chelsea_Scouting_Presentation.pdf` |
| Video Demo | 45-min walkthrough: code review, dashboard tour, findings | `demo_video.mp4` (YouTube/Vimeo link) |

---

## 3. Data Plan

### Primary Data Sources (Free & Open)

#### A. Match Event Data

**StatsBomb Open Data** - [GitHub Repo](https://github.com/statsbomb/open-data)
- **Coverage**: 900+ matches (La Liga, EPL, EURO/World Cup)
- **Use**: Event sequences (passes, shots, duels), player minutes, match outcomes
- **Limitations**: No current season data; use 2019-2022 competitions

**Wyscout Public Dataset** - [Figshare Link](https://figshare.com/collections/Soccer_match_event_dataset/4415000/2)
- **Coverage**: 1,941 matches, 3,251 players (2017/18 season, top-5 leagues)
- **Use**: Broader player pool, cross-league comparisons
- **Format**: JSON event files + player/team metadata

#### B. Player Market Data

**Transfermarkt via FBref** - [FBref.com](https://fbref.com/en/)
- **Use**: Market values, contract expiry dates, nationality, age
- **Method**: Scrape with `requests` + `BeautifulSoup` (respect rate limits)

**Capology** - [Capology.com](https://www.capology.com/uk/premier-league/salaries/)
- **Use**: Estimated weekly wages for budget modeling
- **Fallback**: If unavailable, use Transfermarkt value × 0.05 as weekly wage proxy

#### C. Tracking Data (Optional - For Advanced Analysis)

**Metrica Sports Sample** - [GitHub](https://github.com/metrica-sports/sample-data)
- **Coverage**: 2 full matches with tracking coordinates
- **Use**: Validate off-ball movement metrics, defensive positioning
- **Caveat**: Limited scale; use for methodology proof-of-concept only

### Data Acquisition Commands

```bash
# Clone StatsBomb repo
git clone https://github.com/statsbomb/open-data.git data/statsbomb

# Download Wyscout dataset
wget https://ndownloader.figshare.com/files/14464622 -O data/wyscout_events.zip
unzip data/wyscout_events.zip -d data/wyscout
```

---

## 4. Tech Stack & Installation

### Core Technologies

| Component | Technology | Justification |
|-----------|------------|---------------|
| Language | Python 3.10+ | Ecosystem for ML, data viz, football libs |
| Data Processing | pandas, polars | Fast dataframe ops (polars for 10M+ events) |
| Event Parsing | statsbombpy, kloppy | Pre-built parsers for SB/Wyscout formats |
| Database | PostgreSQL 15 | Relational store for normalized player stats |
| Feature Store | DuckDB | In-process OLAP for fast aggregations |
| Dashboarding | Streamlit 1.28+ | Rapid prototyping, easy deployment (Streamlit Cloud free tier) |
| ML/Similarity | scikit-learn, umap-learn | Cosine similarity, UMAP for dimensionality reduction |
| Automation | GitHub Actions | Free CI/CD for scheduled data refreshes |
| Version Control | Git + DVC | Track code + large CSV artifacts |

### Installation Commands

```bash
# Create environment
conda create -n chelsea_scouting python=3.10
conda activate chelsea_scouting

# Install dependencies
pip install \
    pandas==2.1 \
    polars==0.19 \
    statsbombpy==1.11 \
    kloppy==3.8 \
    psycopg2-binary==2.9 \
    duckdb==0.9 \
    streamlit==1.28 \
    scikit-learn==1.3 \
    umap-learn==0.5 \
    plotly==5.17 \
    beautifulsoup4==4.12 \
    requests==2.31 \
    mplsoccer==1.3

# Optional: Install Postgres locally
# MacOS: brew install postgresql@15
# Ubuntu: sudo apt install postgresql-15
```

---

## 5. ETL & Data Architecture

### Pipeline Stages

#### Stage 1: Ingestion (`src/etl/ingestion.py`)

```python
# Pseudo-code structure
def ingest_statsbomb_events():
    """
    Fetches all competition events from StatsBomb Open Data
    Returns: Raw events DataFrame with 120+ columns
    """
    competitions = sb.competitions()
    all_events = []
    for comp_id, season_id in competitions[['competition_id', 'season_id']].values:
        matches = sb.matches(competition_id=comp_id, season_id=season_id)
        for match_id in matches['match_id']:
            events = sb.events(match_id=match_id)
            all_events.append(events)
    return pd.concat(all_events)
```

#### Stage 2: Normalization - SPADL Schema (`src/etl/spadl_transform.py`)

Convert raw events to Soccer Player Action Description Language (SPADL):
- **Actions**: 12 atomic types (pass, shot, dribble, tackle, interception, etc.)
- **Locations**: X/Y coordinates normalized to 105×68m pitch
- **Outcomes**: Success/failure binary flags

```sql
-- SPADL events table schema
CREATE TABLE spadl_actions (
    action_id SERIAL PRIMARY KEY,
    game_id INT NOT NULL,
    period_id SMALLINT,
    time_seconds NUMERIC,
    team_id INT,
    player_id INT,
    action_type VARCHAR, -- pass, shot, dribble, etc.
    result BOOLEAN,      -- success/failure
    start_x NUMERIC,
    start_y NUMERIC,
    end_x NUMERIC,
    end_y NUMERIC,
    bodypart VARCHAR     -- foot, head, other
);
```

#### Stage 3: Feature Engineering (`src/features/metrics.py`)

Compute per-player aggregates (90-minute normalized):

```sql
-- Player season stats table
CREATE TABLE player_season_stats (
    player_id INT PRIMARY KEY,
    season VARCHAR,
    team_id INT,
    position VARCHAR,
    minutes_played INT,
    age NUMERIC,

    -- Attacking metrics
    goals_90 NUMERIC,
    xg_90 NUMERIC,
    assists_90 NUMERIC,
    xa_90 NUMERIC,
    shots_90 NUMERIC,
    key_passes_90 NUMERIC,

    -- Progression metrics
    progressive_passes_90 NUMERIC,
    progressive_carries_90 NUMERIC,
    carries_into_box_90 NUMERIC,

    -- Defensive metrics
    tackles_90 NUMERIC,
    interceptions_90 NUMERIC,
    blocks_90 NUMERIC,
    pressures_90 NUMERIC,
    pressure_success_rate NUMERIC,

    -- Possession metrics
    passes_completed_90 NUMERIC,
    pass_completion_pct NUMERIC,
    pass_length_avg NUMERIC,

    -- Value-added (optional - requires VAEP model)
    vaep_90 NUMERIC,
    market_value_eur INT,
    contract_expiry DATE,

    FOREIGN KEY (player_id) REFERENCES players(player_id)
);
```

#### Stage 4: Feature Store Design (DuckDB)

```python
# Store aggregated features for fast querying
import duckdb

conn = duckdb.connect('data/feature_store.duckdb')
conn.execute("""
    CREATE TABLE player_features AS
    SELECT * FROM read_csv_auto('data/processed/player_stats_*.csv')
""")
```

### Automation with GitHub Actions

```yaml
# .github/workflows/update_data.yml
name: Weekly Data Refresh
on:
  schedule:
    - cron: '0 2 * * 0'  # Every Sunday at 2 AM UTC
jobs:
  etl:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run ETL
        run: |
          pip install -r requirements.txt
          python src/etl/run_pipeline.py
      - name: Commit updated data
        run: |
          git config user.name "GitHub Actions"
          git add data/processed/
          git commit -m "Auto-update: $(date)"
          git push
```

---

## 6. Core Scouting Metrics

| Metric | Definition | Computation | Required Fields | Scout Use-Case |
|--------|------------|-------------|-----------------|----------------|
| xG+xA per 90 | Expected goal contributions (goals + assists) | Sum(shot_xG where outcome=goal) + Sum(pass_xA where outcome=assist), normalized to 90 mins | shot_xg, pass_xa, minutes | Identify high-output attackers |
| Progressive Distance | Total meters carried/passed toward opponent goal | Sum(distance) where end_x > start_x + 10m | start_x, end_x, action_type | Find ball progressors (midfielders/fullbacks) |
| Defensive Actions per 90 | Tackles + interceptions + blocks | Count(action_type IN ['tackle', 'interception', 'block']) / (minutes/90) | action_type, minutes | Quantify defensive workrate |
| Pressure Success % | % of pressures forcing turnover within 5 sec | Count(pressure → turnover within 5s) / Count(pressures) | action_type, time_seconds, result | Evaluate pressing intensity |
| Pass Completion % (Final 3rd) | Accuracy in attacking areas | Count(pass success where end_x > 70) / Count(passes where end_x > 70) | action_type, end_x, result | Assess composure under pressure |
| Shot-Creating Actions | Passes/dribbles leading to shot within 2 actions | Count sequences ending in shot within 2 touches | action sequences, time_seconds | Find creators beyond assists |
| Aerial Duel Win % | Success rate in aerial contests | Count(aerial_won) / Count(aerials_total) | action_type=aerial, result | Target physical dominance (CBs, strikers) |
| Market Value per xG+xA | Cost efficiency metric | market_value_eur / (xg_90 + xa_90) | market_value, xg_90, xa_90 | Identify undervalued players |
| Age-Adjusted Performance | Normalize metrics by age curve | metric × age_adjustment_factor[age] | age, base_metric | Predict peak years (buy young or proven) |
| Contract Urgency Score | Time until free agency | 12 - months_until_expiry (capped at 0) | contract_expiry, current_date | Prioritize expiring contracts |

---

## 7. Player Similarity & Ranking System

### Approach: Multi-Dimensional Similarity with Position-Specific Weights

#### Step 1: Feature Selection

```python
# Position-specific feature sets
FEATURE_SETS = {
    'CB': ['tackles_90', 'interceptions_90', 'aerial_win_pct', 'pass_completion_pct', 'progressive_passes_90', 'blocks_90'],
    'FB': ['progressive_carries_90', 'crosses_90', 'tackles_90', 'pass_completion_pct', 'dribbles_success_90', 'xa_90'],
    'CM': ['progressive_passes_90', 'pass_completion_pct', 'key_passes_90', 'pressures_90', 'tackles_90', 'xa_90'],
    'W': ['xg_90', 'xa_90', 'dribbles_success_90', 'shot_creating_actions_90', 'carries_into_box_90', 'progressive_carries_90'],
    'ST': ['xg_90', 'goals_90', 'shots_90', 'aerials_win_pct', 'key_passes_90', 'pressures_90']
}
```

#### Step 2: Similarity Computation

```python
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def find_similar_players(target_player_id, position, top_n=10, max_age_diff=3, max_value_multiplier=1.5):
    """
    Find similar players using weighted cosine similarity
    Filters:
    - Same position
    - Age within ±3 years
    - Market value ≤ 1.5× target's value
    - Minimum 900 minutes played
    """
    # Load feature store
    df = load_player_features(position=position, min_minutes=900)

    # Get target player stats
    target = df[df['player_id'] == target_player_id]
    target_age = target['age'].values[0]
    target_value = target['market_value_eur'].values[0]

    # Apply filters
    candidates = df[
        (df['age'].between(target_age - max_age_diff, target_age + max_age_diff)) &
        (df['market_value_eur'] <= target_value * max_value_multiplier) &
        (df['player_id'] != target_player_id)
    ]

    # Select features
    features = FEATURE_SETS[position]
    X = candidates[features].values
    target_vec = target[features].values

    # Standardize (z-score)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    target_scaled = scaler.transform(target_vec)

    # Compute cosine similarity
    similarities = cosine_similarity(target_scaled, X_scaled)[0]

    # Rank and return top N
    candidates['similarity_score'] = similarities
    shortlist = candidates.nlargest(top_n, 'similarity_score')

    return shortlist[['player_name', 'team', 'age', 'market_value_eur', 'similarity_score'] + features]

# Example usage
similar_to_enzo = find_similar_players(
    target_player_id=123456,  # Enzo Fernández ID
    position='CM',
    top_n=10
)
```

#### Step 3: Dimensionality Reduction Visualization

```python
import umap

# Reduce 15+ features to 2D for interactive plot
reducer = umap.UMAP(n_neighbors=15, min_dist=0.1, metric='cosine')
embedding = reducer.fit_transform(X_scaled)

# Plot in dashboard with Plotly
fig = px.scatter(
    x=embedding[:, 0],
    y=embedding[:, 1],
    color=df['position'],
    size=df['market_value_eur'],
    hover_data=['player_name', 'team', 'age'],
    title='Player Similarity Space (UMAP Projection)'
)
```

---

## 8. Portfolio-Ready Dashboard Visualizations

### Dashboard 1: Squad Overview
- **Purpose**: Show Chelsea's current player roster with wage bill and positional balance
- **Visual**: Interactive squad graphic (formation layout) with player cards showing age, contract expiry, market value
- **Filters**: Season, formation, age range
- **Key Insight**: Highlight positions needing reinforcement ("2/3 CBs over 30, 1 contract expiring")

### Dashboard 2: Transfer Target Shortlist
- **Purpose**: Display top 10 candidates per position with key metrics
- **Visual**: Sortable table with columns: Name, Team, Age, Market Value, Defensive Actions, Similarity Score
- **Interaction**: Click player → open detailed radar chart + recent performance timeline
- **Export**: "Download Scouting Report PDF" button

### Dashboard 3: Player Comparison Radar
- **Purpose**: Compare up to 4 players on 8 metrics (normalized percentiles)
- **Visual**: Multi-player radar chart (mplsoccer `radar_chart`) with league percentile ranks
- **Use Case**: "Compare Declan Rice vs. 3 alternative DM targets"

### Dashboard 4: Market Value Efficiency Plot
- **Purpose**: Identify undervalued players (high output, low cost)
- **Visual**: Scatter plot with xG+xA on Y-axis, Market Value on X-axis, bubble size = age
- **Quadrants**: Label regions "Hidden Gems", "Proven Elite", "Overhyped", "Developing Talent"
- **Interaction**: Click bubble → open player detail pane

### Dashboard 5: Budget Simulation Tool
- **Purpose**: Test transfer scenarios against £200M budget + £300K/week wage cap
- **Visual**: Drag-and-drop interface to add/remove players from proposed squad
- **Real-Time Calculation**: Total spend, wage bill, FFP compliance status (green/red indicator)
- **Output**: "Export Final Squad Proposal as PDF"

---

## 9. Repository Structure & Deliverables

```
chelsea-scouting-system/
├── README.md                    # Project overview, setup instructions
├── requirements.txt             # Python dependencies
├── .gitignore                   # Exclude data/, __pycache__
├── .github/
│   └── workflows/
│       └── update_data.yml      # Automated ETL schedule
│
├── data/
│   ├── raw/                     # Unprocessed StatsBomb/Wyscout files
│   ├── processed/               # Cleaned CSVs (player_stats.csv, matches.csv)
│   └── feature_store.duckdb     # DuckDB database
│
├── src/
│   ├── etl/
│   │   ├── ingestion.py         # Fetch StatsBomb/Wyscout data
│   │   ├── spadl_transform.py   # Event normalization
│   │   └── run_pipeline.py      # Orchestrate ETL stages
│   │
│   ├── features/
│   │   ├── metrics.py           # Compute per-90 stats
│   │   └── market_scraper.py    # Transfermarkt value scraping
│   │
│   ├── models/
│   │   ├── similarity.py        # Cosine similarity engine
│   │   └── squad_optimizer.py   # Budget constraint solver
│   │
│   └── utils/
│       ├── db_connection.py     # Postgres/DuckDB helpers
│       └── plotting.py          # Radar charts, heatmaps
│
├── dashboard/
│   ├── app.py                   # Main Streamlit app
│   ├── pages/
│   │   ├── 1_Squad_Overview.py
│   │   ├── 2_Shortlist.py
│   │   ├── 3_Player_Comparison.py
│   │   ├── 4_Market_Analysis.py
│   │   └── 5_Budget_Simulator.py
│   └── assets/
│       └── chelsea_logo.png
│
├── notebooks/
│   ├── 01_data_exploration.ipynb    # EDA on StatsBomb data
│   ├── 02_feature_engineering.ipynb
│   └── 03_similarity_validation.ipynb
│
├── docs/
│   ├── Chelsea_Scouting_Presentation.pdf  # Final slide deck
│   └── methodology.md                      # Detailed metric definitions
│
├── tests/
│   ├── test_etl.py
│   └── test_similarity.py
│
└── video/
    └── demo_video_link.txt      # YouTube/Vimeo URL
```

### Deliverables Checklist

- [ ] **Code**: All `.py` files committed with docstrings
- [ ] **Data**: Sample CSVs (100 rows) in `/data/processed` (full data in DVC)
- [ ] **Dashboard**: Deployed Streamlit app (include URL in README)
- [ ] **Presentation**: 15-slide PDF covering problem, method, insights, impact
- [ ] **Video**: 45-min demo (code walkthrough 20 min + dashboard tour 25 min)
- [ ] **README**: Setup commands, data sources, reproducibility instructions
- [ ] **Tests**: Unit tests for key functions (≥60% coverage)

---

## 10. Timeline (16-Week Plan)

| Week | Milestone | Tasks | Deliverable |
|------|-----------|-------|-------------|
| 1-2 | Setup & Data Acquisition | Install environment, clone StatsBomb repo, download Wyscout data, setup Git repo | `README.md`, `requirements.txt` |
| 3-4 | ETL Pipeline | Write ingestion scripts, normalize to SPADL, create Postgres schema, load 10k events | `src/etl/*`, populated database |
| 5-6 | Feature Engineering | Compute all 25 metrics, validate against known players, create feature store | `src/features/metrics.py`, `player_stats.csv` |
| 7 | Market Data Integration | Scrape Transfermarkt, join with player stats, handle missing values | `market_value_eur` column added |
| 8-9 | Similarity Engine | Implement cosine similarity, test with Chelsea squad, tune hyperparameters | `src/models/similarity.py`, validation notebook |
| 10 | Dashboard - Phase 1 | Build Squad Overview + Shortlist pages in Streamlit | 2/5 dashboards live |
| 11 | Dashboard - Phase 2 | Add Comparison Radar + Market Analysis pages | 4/5 dashboards live |
| 12 | Dashboard - Phase 3 | Build Budget Simulator with drag-drop, deploy to Streamlit Cloud | All 5 dashboards deployed |
| 13 | Analysis & Insights | Run similarity for all Chelsea positions, identify 10 targets, document findings | Shortlist CSV, insights doc |
| 14 | Presentation Creation | Design 15-slide deck (problem, data, method, results, business value) | `Chelsea_Scouting_Presentation.pdf` |
| 15 | Video Recording | Record 45-min demo: code review (20 min) + dashboard tour (25 min) | `demo_video.mp4`, upload to YouTube |
| 16 | Final QA & Submission | Test all code, update README, check deliverables against rubric, submit | Complete repo pushed to GitHub |

---

## 11. Risks & Mitigation Strategies

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| StatsBomb data insufficient | Medium | High | Fallback to Wyscout (1,941 matches); supplement with FBref scraped stats |
| API rate limits (Transfermarkt) | High | Medium | Cache responses locally; implement exponential backoff; use `time.sleep(5)` |
| Postgres setup issues | Low | Medium | Alternative: Use DuckDB for everything (no server required) |
| Streamlit Cloud deployment fails | Low | High | Test locally first; use Docker container as backup; include screenshots in PDF |
| Insufficient compute for VAEP | Medium | Low | Skip VAEP initially; use simpler xG+xA as proxy; document as future work |
| Video recording technical issues | Low | Medium | Record in segments; use Zoom local recording; have backup slides |
| Missing contract/wage data | High | Low | Use heuristic (market_value × 0.05 = weekly_wage); label as estimated |

---

## 12. Grading Rubric Mapping

### Assumed Rubric Categories

| Category | Weight | Deliverable | Evidence in Project |
|----------|--------|-------------|---------------------|
| Data Engineering | 25% | ETL code, database schema | `src/etl/*`, SQL schemas, GitHub Actions workflow |
| Feature Engineering | 20% | Metrics computation, validation | `src/features/metrics.py`, validation notebooks |
| Analytical Rigor | 20% | Similarity method, model evaluation | `src/models/similarity.py`, comparison to ground truth |
| Visualization & UX | 15% | Dashboard quality, interactivity | 5 Streamlit pages with filters/exports |
| Business Context | 10% | Squad analysis, budget constraints | Budget simulator, FFP compliance checks |
| Documentation | 5% | README, code comments, presentation | Comprehensive README, docstrings, 15-slide PDF |
| Reproducibility | 5% | Setup instructions, tests | `requirements.txt`, unit tests, sample data |

### Acceptance Criteria

- **Pass Threshold**: All 4 deliverables submitted, code runs without errors, presentation covers methodology
- **Distinction Criteria**: Advanced metrics (VAEP), deployed dashboard, business-ready outputs (shortlist PDF), polished video

---

## 13. Quick Start Commands

```bash
# 1. Clone template repo (or create new)
git clone <your-repo-url> chelsea-scouting
cd chelsea-scouting

# 2. Create environment
conda env create -f environment.yml
conda activate chelsea_scouting

# 3. Run ETL pipeline
python src/etl/run_pipeline.py --leagues "EPL,La Liga" --seasons "2022,2023"

# 4. Launch dashboard
streamlit run dashboard/app.py

# 5. Run tests
pytest tests/ --cov=src
```

---

## 14. Additional Resources

### Tutorials
- **SPADL Tutorial**: [socceraction docs](https://socceraction.readthedocs.io/en/latest/)
- **StatsBomb Python API**: [statsbombpy GitHub](https://github.com/statsbomb/statsbombpy)
- **Streamlit for Sports Analytics**: [Medium Article](https://towardsdatascience.com/tagged/sports-analytics)

### Academic References
- **Player Valuation**: Decroos et al. (2019) - "Actions Speak Louder Than Goals" (VAEP paper)
- **Scouting Frameworks**: Pappalardo et al. (2019) - "PlayeRank: Data-driven Performance Evaluation"
- **Transfer Market Efficiency**: Peeters (2018) - "Testing the Wisdom of Crowds in Football Transfer Markets"

---

## 15. Final Notes

This plan prioritizes reproducibility and academic rigor while maintaining industry relevance. Adjust timeline based on your specific course requirements and available time.

**Important**: Turn on web search in Search and tools menu when using Claude. Otherwise, links provided may not be accurate or up to date.

---

*Document created: January 2026*
*Source: Claude AI conversation from December 11, 2025*
