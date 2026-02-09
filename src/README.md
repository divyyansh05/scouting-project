# Chelsea FC Data-Driven Scouting System

A comprehensive football scouting platform with player similarity search, metrics analysis, and natural language query capabilities.

## Architecture

```
Raw SQL Tables (READ-ONLY) → Analytics Module (Pure Python) → Dash App (Presentation) → LLM Layer (Query Parsing Only)
```

### Core Components

- **Database Layer** (`utils/db.py`): Read-only PostgreSQL connection with query validation
- **Metrics Service** (`services/metrics_service.py`): Metric computation and validation
- **Role Service** (`services/role_service.py`): 20-dimensional role vector analysis
- **Similarity Service** (`services/similarity_service.py`): Cosine similarity with weighted vectors
- **LLM Service** (`services/llm_service.py`): Natural language query parsing (NO computation)
- **Visualization** (`visualization/`): Plotly-based charts and tables
- **Dash Application** (`app.py`): Interactive web interface

## Similarity Algorithm

```
Total Similarity = (Role Similarity × 0.6) + (Stats Similarity × 0.4)
```

### Role Vectors (20 dimensions)
- Position encoding (dims 0-3)
- Spread metrics (dims 4-7)
- Zone preferences (dims 8-15)
- Pass directions (dims 16-19)

### Cosine Similarity
```python
similarity = dot(v1, v2) / (||v1|| × ||v2||)
# Clipped to [0, 1] range
```

## 8 Critical Invariants

1. **Similarity Identity**: Self-similarity = 1.0
2. **Monotonicity**: Higher weights → higher influence
3. **Metric Correctness**: Computed metrics match formulas
4. **LLM Schema Validation**: Parsed queries match expected schema
5. **Forbidden Metric Rejection**: Hallucinated metrics rejected
6. **Database Read-Only**: No write operations allowed
7. **Data Integrity**: Data types and ranges preserved
8. **Edge Cases**: Proper handling of nulls, zeros, empty sets

## Anti-Hallucination System

4-layer defense using Metrics Registry as single source of truth:

1. **Metrics Registry** (`config/metrics_registry.yaml`): Defines all valid metrics
2. **Validation Layer**: Rejects undefined/forbidden metrics
3. **LLM Prompting**: Instructs LLM to only use available metrics
4. **Query Validation**: Final check before execution

## Installation

```bash
# Clone repository
git clone https://github.com/chelseafc/scouting-system.git
cd scouting-system/src

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or install with development dependencies
pip install -e ".[dev]"

# Or install with LLM support
pip install -e ".[llm]"
```

## Configuration

1. Copy environment template:
```bash
cp .env.example .env
```

2. Configure database connection:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=scouting_db
DB_USER=your_username
DB_PASSWORD=your_password
```

3. (Optional) Configure LLM for natural language queries:
```env
ANTHROPIC_API_KEY=your_api_key
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4
```

## Running the Application

```bash
# Start the Dash server
python app.py

# Or with custom host/port
python app.py --host 0.0.0.0 --port 8050
```

Access the application at: `http://localhost:8050`

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=services --cov=utils --cov=visualization

# Run specific test file
pytest tests/test_similarity_service.py

# Run invariant tests only
pytest tests/test_invariants.py -v

# Run with markers
pytest -m "unit"           # Unit tests only
pytest -m "integration"    # Integration tests only
pytest -m "not slow"       # Skip slow tests
```

## Project Structure

```
src/
├── app.py                      # Main Dash application
├── config/
│   └── metrics_registry.yaml   # Metric definitions (single source of truth)
├── services/
│   ├── __init__.py
│   ├── metrics_service.py      # Metric computation
│   ├── role_service.py         # Role vector analysis
│   ├── similarity_service.py   # Player similarity
│   └── llm_service.py          # Query parsing
├── utils/
│   ├── __init__.py
│   ├── db.py                   # Database utilities
│   └── validation.py           # Data validation
├── visualization/
│   ├── __init__.py
│   ├── radar.py                # Radar charts
│   ├── scatter.py              # Scatter plots
│   ├── heatmaps.py             # Heatmaps
│   └── tables.py               # Data tables
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Test fixtures
│   ├── test_similarity_service.py
│   ├── test_metrics_service.py
│   ├── test_llm_service.py
│   └── test_invariants.py      # Critical invariant tests
├── requirements.txt
├── setup.py
├── pyproject.toml
└── README.md
```

## Key Features

### Player Search
- Browse by League → Team → Player
- Filter by position, age, minutes played
- Sort by any available metric

### Similarity Search
- Find similar players using cosine similarity
- Weighted combination of role vectors and stats
- Position compatibility filtering
- Detailed similarity breakdown

### Player Dashboard
- Comprehensive player profile
- Radar chart comparisons
- Statistical breakdowns by category
- Season-by-season trends

### Natural Language Queries
- "Show me top strikers by goals per 90"
- "Find players similar to Kevin De Bruyne"
- "Compare Haaland and Kane on attacking metrics"

## API Reference

### Similarity Service

```python
from services import find_similar_players, similarity_score_breakdown

# Find similar players
results = find_similar_players(
    target_player_id=123,
    position_filter='same_group',
    limit=10
)

# Get detailed breakdown
breakdown = similarity_score_breakdown(
    role_vector_1, role_vector_2,
    stats_vector_1, stats_vector_2
)
```

### Metrics Service

```python
from services import compute_per_90, validate_metric_exists

# Compute per-90 value
per_90 = compute_per_90(goals=10, minutes=900)  # Returns 1.0

# Validate metric
exists = validate_metric_exists('goals')  # Returns True
exists = validate_metric_exists('fake_metric')  # Returns False
```

### LLM Service

```python
from services import parse_query, validate_parsed_query

# Parse natural language query
parsed = parse_query("Find players similar to Messi")

# Validate parsed query
result = validate_parsed_query(parsed)
if result['valid']:
    # Execute query
    pass
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all invariant tests pass
5. Submit a pull request

## License

MIT License - See LICENSE file for details.

## Acknowledgments

- StatsBomb for data inspiration
- Chelsea FC Analytics Team
- Plotly/Dash community
