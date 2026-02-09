# Football Scouting Analytics Platform - Implementation Reference

## What I Gathered From The Chat

### Architecture Overview
```
Raw SQL Tables (read-only) → Analytics Module (pure Python) → Dash App (presentation) → LLM Layer (query parsing only)
```

### Core Principles
1. **No Scraping** - All data from existing PostgreSQL tables
2. **No SQL Writes** - Read-only database access
3. **Deterministic Analytics** - Pure Python computations, no randomness
4. **LLM Boundaries** - LLM parses queries, NEVER computes metrics
5. **Service Isolation** - Each service has single responsibility
6. **No Callback Logic in Dash** - Callbacks only wire services to UI

### Complete System Overview (8 Modules, 5,500+ lines)

| Module | File | Lines | Status |
|--------|------|-------|--------|
| Database Layer | `utils/db.py` | 400+ | Need full code |
| Metrics Registry | `config/metrics_registry.yaml` + `utils/validation.py` | 500+ | Need full code |
| Metrics Service | `services/metrics_service.py` | 600+ | Need full code |
| Role Service | `services/role_service.py` | 700+ | Need full code |
| Similarity Service | `services/similarity_service.py` | 800+ | Need full code |
| LLM Service | `services/llm_service.py` | 600+ | Need full code |
| Visualizations | `visualization/*.py` (4 files) | 1000+ | Need full code |
| Dash Application | `app.py` | 900+ | Need full code |

### Project Structure
```
scouting_app/
├── app.py                          # Main Dash application (900+ lines)
├── config/
│   └── metrics_registry.yaml       # Metrics configuration (500+ entries)
├── utils/
│   ├── db.py                       # Database access layer (400+ lines)
│   └── validation.py               # Metrics validation
├── services/
│   ├── metrics_service.py          # Metrics computations (600+ lines)
│   ├── role_service.py             # Role vector system (700+ lines)
│   ├── similarity_service.py       # Player similarity (800+ lines)
│   └── llm_service.py              # Natural language parsing (600+ lines)
├── visualization/
│   ├── radar.py                    # Radar charts
│   ├── scatter.py                  # Scatter plots
│   ├── heatmaps.py                 # Heatmaps
│   └── tables.py                   # Data tables
├── tests/
│   ├── test_critical_invariants.py # 8 critical test classes (600+ lines)
│   ├── test_db.py
│   ├── test_validation.py
│   ├── test_metrics_service.py
│   ├── test_role_service.py
│   ├── test_similarity_service.py
│   ├── test_llm_service.py
│   ├── integration/
│   │   ├── test_end_to_end.py
│   │   └── test_similarity_pipeline.py
│   └── conftest.py
├── requirements.txt
└── README.md
```

### Key Technical Details

#### Database Layer (`utils/db.py`)
- Connection pooling with `ThreadedConnectionPool`
- 4-layer read-only enforcement
- Functions: `fetch_dataframe()`, `execute_query()`, `startup_db()`, `shutdown_db()`

#### Metrics Registry (`config/metrics_registry.yaml`)
- 60+ football metrics across 7 categories
- 6 preset groups (striker_profile, creative_midfielder_profile, etc.)
- Validation rules for position-specific restrictions
- Categories: shooting, passing, defending, possession, physical, goalkeeper, advanced

#### Role Service (`services/role_service.py`)
- 20-dimensional role vector with components:
  - Position encoding (4D)
  - Positional spread (2D)
  - Vertical zones (3D: def_third, mid_third, att_third)
  - Horizontal zones (3D: left, center, right)
  - Pass directions (4D: forward, backward, lateral, progressive)
  - Progressive tendency (1D)
  - Spatial per90s (2D)
  - Derived metrics (1D)

#### Similarity Service (`services/similarity_service.py`)
- Two-component cosine similarity:
  - Role vectors: 60% weight
  - Stats vectors: 40% weight
- Position filtering and minimum minutes filtering
- Function: `find_similar_players(player_id, season, n_similar=10, filters=...)`

#### LLM Service (`services/llm_service.py`)
- Low temperature (0.1) for deterministic outputs
- 4-layer anti-hallucination defense:
  1. LLM prompt includes metrics registry
  2. Synonym resolution
  3. Post-parsing validation
  4. Position/compatibility checks
- Functions: `parse_query()`, `validate_parsed_query()`, `build_safe_default_query()`

### Testing Infrastructure

#### 8 Critical Invariant Test Classes
1. `TestSimilarityIdentity` - Player vs self = 1.0
2. `TestSimilarityMonotonicity` - Order preserved
3. `TestMetricCorrectness` - Math exact
4. `TestLLMSchemaValidation` - Output validated
5. `TestForbiddenMetricRejection` - Invalid blocked
6. `TestDatabaseReadOnly` - No writes
7. `TestDataIntegrity` - No NaN/Inf
8. `TestEdgeCases` - Real data handled

#### Test Commands
```bash
# Critical tests (3 seconds)
pytest tests/test_critical_invariants.py -v

# All tests
pytest tests/ -v

# Coverage check (80% target)
pytest tests/ --cov=services --cov-fail-under=80
```

### Dependencies (requirements.txt)
```
dash>=2.14.0
plotly>=5.18.0
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
psycopg2-binary>=2.9.9
python-dotenv>=1.0.0
PyYAML>=6.0.1
anthropic>=0.18.0  # or openai for LLM
pytest>=7.4.0
pytest-cov>=4.1.0
```

---

## WHAT I NEED FROM YOU

I was able to see the architecture, structure, and high-level details, but the actual code content in the artifacts wasn't fully visible/copyable from the shared chat.

### Please provide the following code files:

1. **`utils/db.py`** - Full database layer code
2. **`config/metrics_registry.yaml`** - Full metrics configuration
3. **`utils/validation.py`** - Metrics validation code
4. **`services/metrics_service.py`** - Full metrics service
5. **`services/role_service.py`** - Full role service
6. **`services/similarity_service.py`** - Full similarity service
7. **`services/llm_service.py`** - Full LLM service
8. **`visualization/radar.py`** - Radar chart code
9. **`visualization/scatter.py`** - Scatter plot code
10. **`visualization/heatmaps.py`** - Heatmap code
11. **`visualization/tables.py`** - Table code
12. **`app.py`** - Main Dash application
13. **`tests/test_critical_invariants.py`** - Critical tests

### You can either:
- **Option A**: Download the artifacts from the Claude chat as `.md` files and share them
- **Option B**: Copy-paste the code directly here
- **Option C**: If you have the code exported somewhere, point me to the files

Once you provide the code, I'll immediately set up the complete project structure and implement everything properly.
