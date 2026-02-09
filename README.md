# Chelsea FC Data-Driven Scouting System

A comprehensive football scouting platform that combines advanced analytics, LLM-powered natural language queries, and data visualization to identify and evaluate player talent.

## Features

- **Natural Language Queries**: Ask questions like "Find me a left-footed striker under 25 with good aerial ability"
- **Player Similarity Analysis**: 20-dimensional role vectors to find players with similar playing styles
- **Interactive Dashboard**: Dash + Plotly-powered analytics interface
- **Data Pipeline**: Automated ETL from API-Football with FBref enrichment
- **Metrics Registry**: 60+ validated metrics with anti-hallucination safeguards

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Dash, Plotly |
| Backend | Python, Flask |
| Database | PostgreSQL |
| LLM | Anthropic Claude API |
| Data Source | API-Football, FBref |
| ETL | Custom Python pipeline |

## Project Structure

```
scouting-project/
├── src/                    # Main scouting application
│   ├── app.py             # Dash application entry point
│   ├── services/          # Business logic (LLM, similarity, metrics)
│   ├── visualization/     # Chart components
│   ├── utils/             # Helpers (database, validation)
│   └── config/            # Configuration management
├── Data-ETL-Pipeline/     # Data collection & processing
│   ├── cli.py             # CLI for ETL operations
│   ├── etl/               # Extract, Transform, Load modules
│   ├── database/          # DB schema & migrations
│   ├── scheduler/         # Automated data updates
│   └── server/            # Monitoring dashboard
├── tests/                 # Test suites
├── docs/                  # Documentation
└── DEVELOPMENT_PLAN.md    # Roadmap & implementation guide
```

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- API-Football API key
- Anthropic API key (for LLM features)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/scouting-project.git
   cd scouting-project
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r src/requirements.txt
   pip install -r Data-ETL-Pipeline/requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp src/.env.example src/.env
   cp Data-ETL-Pipeline/.env.example Data-ETL-Pipeline/.env
   # Edit both .env files with your credentials
   ```

5. **Initialize database**
   ```bash
   cd Data-ETL-Pipeline
   python cli.py db init
   ```

6. **Collect initial data**
   ```bash
   python cli.py collect --league premier-league --season 2024
   ```

7. **Run the scouting application**
   ```bash
   cd ../src
   python app.py
   ```
   Open http://localhost:8050 in your browser.

## Data Pipeline

### ETL Commands

```bash
# Collect league data
python cli.py collect --league premier-league --season 2024

# Run full pipeline
python cli.py pipeline run

# Check data health
python cli.py status

# Start monitoring dashboard
python cli.py server start
```

### Scheduler

Automate data collection with the built-in scheduler:

```bash
python run_scheduler.py
```

## Current Data Coverage

| Metric | Count |
|--------|-------|
| Leagues | 6 |
| Teams | 112 |
| Players | 1,373 |
| Matches | 3,006 |
| Player Stats | 2,201 |

**Primary Focus**: Premier League (1,354 players with full statistics)

## Development

See [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) for the complete roadmap and implementation guide.

### Running Tests

```bash
pytest tests/ -v
```

### Code Quality

```bash
# Linting
ruff check .

# Type checking
mypy src/
```

## API Documentation

### LLM Query Interface

```python
from services.llm_service import LLMService

llm = LLMService()
result = llm.parse_query("strikers with 15+ goals this season")
# Returns: structured filter criteria
```

### Similarity Search

```python
from services.similarity_service import SimilarityService

similarity = SimilarityService()
similar_players = similarity.find_similar(player_id=123, top_n=10)
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [API-Football](https://www.api-football.com/) for comprehensive football data
- [FBref](https://fbref.com/) for advanced statistics
- [Anthropic](https://anthropic.com/) for Claude LLM capabilities
