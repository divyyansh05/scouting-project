# Football Scouting Data Pipeline - Development Plan

> **Created**: 2026-02-07
> **Goal**: Build a production-ready scouting data pipeline with weekly automated updates
> **Target**: Complete data coverage for 8 leagues with all must-have scouting metrics

---

## Current State Analysis

### What We Have
| Component | Status | Notes |
|-----------|--------|-------|
| Database | ✅ Running | PostgreSQL 15, 116 columns in player_season_stats |
| FotMob Scraper | ⚠️ Partial | Basic collection works, deep stats NOT extracted |
| API-Football | ⚠️ Limited | 100 req/day, secondary source |
| StatsBomb | ✅ Working | Historical data only |
| Understat | ❌ Broken | Page structure changed |
| Scheduler | ❌ Not Running | Jobs defined but not activated |

### Critical Data Gaps (MUST FIX)
| Data Point | Available In | Currently Collected |
|------------|-------------|---------------------|
| xG | FotMob ✅ | ❌ No |
| xA | FotMob ✅ | ❌ No |
| npxG | FotMob ✅ | ❌ No |
| Progressive Passes | FotMob ✅ | ❌ No |
| Progressive Carries | FotMob ✅ | ❌ No |
| Pressures | FotMob ✅ | ❌ No |
| Market Value | FotMob ❌ / Transfermarkt ✅ | ❌ No |
| Contract End Date | FotMob ✅ | ❌ No |
| Height/Weight | FotMob ✅ | ❌ No |
| Percentile Rankings | FotMob ✅ | ❌ No |
| Shot Maps (xG per shot) | FotMob ✅ | ❌ No |

### Database Reality Check
```
players with fotmob_id:        0 (should be 1,889)
players with market_value:     0 (critical gap)
players with contract_end:     0 (critical gap)
player_stats with xg:          0 (critical gap)
player_stats with xa:          0 (critical gap)
player_stats with pressures:   0 (critical gap)
```

---

## Development Phases

### Phase 1: Fix FotMob Deep Stats Extraction (Priority: CRITICAL)
**Duration**: 1-2 days
**Goal**: Extract ALL available stats from FotMob player data

#### 1.1 Update FotMob Parser
FotMob provides rich data in `firstSeasonStats.statsSection`:
- Shooting: goals, xG, xGOT, npxG, shots, shots on target
- Passing: assists, xA, accurate passes, key passes, progressive passes
- Defending: tackles, interceptions, clearances, blocks
- Possession: touches, dribbles, carries, progressive carries
- Plus: percentile ranks for all stats!

**Files to modify**:
- `scrapers/fotmob/data_parser.py` - Add `parse_player_deep_stats()`
- `etl/fotmob_etl.py` - Call deep stats parser, update DB

#### 1.2 Extract Player Bio Data
FotMob provides:
- `contractEnd.utcTime` - Contract expiration
- `playerInformation` - Height, preferred foot, nationality
- `positionDescription` - Primary/secondary positions
- `injuryInformation` - Current injury status

#### 1.3 Store fotmob_id for ALL Players
Currently 0 players have fotmob_id stored - must fix.

---

### Phase 2: Add Transfermarkt Integration (Priority: HIGH)
**Duration**: 2-3 days
**Goal**: Get market values, contract details, transfer history

#### 2.1 Create Transfermarkt Scraper
Web scraping transfermarkt.com for:
- Market value (current + historical)
- Contract end date
- Transfer history
- Agent information

**Files to create**:
- `scrapers/transfermarkt/__init__.py`
- `scrapers/transfermarkt/client.py`
- `etl/transfermarkt_etl.py`

#### 2.2 Player Matching
Match players between FotMob and Transfermarkt using:
- Name similarity (fuzzy matching)
- Team + position
- Age/DOB

---

### Phase 3: Automated Weekly Updates (Priority: HIGH)
**Duration**: 1-2 days
**Goal**: Self-updating pipeline with no manual intervention

#### 3.1 Scheduler Configuration
```python
# scheduler/jobs.py - Weekly update schedule
SCHEDULE = {
    'fotmob_full_refresh': 'every Monday 2am',
    'fotmob_deep_stats': 'every Tuesday 2am',
    'transfermarkt_values': 'every Wednesday 2am',
    'data_validation': 'every Thursday 2am',
    'backup_database': 'every Friday 2am',
}
```

#### 3.2 Update Strategy
- **Match days**: Collect match results same day
- **Weekly**: Full player stats refresh
- **Monthly**: Market value updates
- **Quarterly**: Historical data backfill

#### 3.3 Monitoring & Alerts
- Data freshness checks
- Missing data alerts
- API health monitoring
- Slack/email notifications

---

### Phase 4: Data Quality & Validation (Priority: MEDIUM)
**Duration**: 1-2 days

#### 4.1 Data Completeness Checks
- % of players with xG data
- % of players with market value
- % of matches with stats
- Flag incomplete records

#### 4.2 Deduplication
- Merge duplicate player records
- Standardize team names
- Fix cross-source ID mapping

#### 4.3 Historical Backfill
- Collect 2020-2024 seasons
- Fill gaps in player careers
- Import StatsBomb historical data

---

### Phase 5: API & Dashboard (Priority: MEDIUM)
**Duration**: 2-3 days

#### 5.1 Enhanced API Endpoints
- `/api/players/search` - Full-text search
- `/api/players/{id}/stats` - Complete stats with percentiles
- `/api/players/compare` - Side-by-side comparison
- `/api/players/similar` - Find similar players
- `/api/scouting/shortlist` - Save player lists

#### 5.2 Dashboard Features
- Player radar charts
- League percentile rankings
- Transfer market tracker
- Injury status monitoring

---

## Implementation Priority Order

```
Week 1:
├── Day 1-2: Phase 1.1 - Fix FotMob deep stats parser
├── Day 3: Phase 1.2 - Extract player bio data
└── Day 4-5: Phase 1.3 - Run full data collection

Week 2:
├── Day 1-2: Phase 2 - Transfermarkt integration
├── Day 3-4: Phase 3 - Scheduler setup
└── Day 5: Phase 4 - Data validation

Week 3:
├── Day 1-2: Phase 5 - API enhancements
├── Day 3-4: Testing & bug fixes
└── Day 5: Documentation & deployment
```

---

## Must-Have Scouting Metrics (Checklist)

### Player Profile
- [ ] Name, DOB, Age, Nationality
- [ ] Height, Weight, Preferred Foot
- [ ] Position (primary + secondary)
- [ ] Current Team, Shirt Number
- [ ] Contract End Date
- [ ] Market Value (current + history)
- [ ] Photo URL
- [ ] Injury Status

### Performance Stats (per season)
- [ ] Matches, Starts, Minutes
- [ ] Goals, Assists, G+A
- [ ] xG, xA, xG+xA
- [ ] npxG (non-penalty xG)
- [ ] xGOT (xG on target)
- [ ] Shots, Shots on Target, Shot Accuracy
- [ ] Goals/Shot, Goals/xG (finishing)

### Passing & Creativity
- [ ] Passes Completed, Pass Accuracy
- [ ] Key Passes, Through Balls
- [ ] Progressive Passes
- [ ] Passes into Final Third
- [ ] Passes into Penalty Area
- [ ] Crosses, Cross Accuracy

### Possession & Dribbling
- [ ] Touches, Touches in Box
- [ ] Dribbles Attempted, Success Rate
- [ ] Progressive Carries
- [ ] Carries into Final Third
- [ ] Carries into Penalty Area

### Defending
- [ ] Tackles, Tackle Success Rate
- [ ] Interceptions
- [ ] Blocks, Clearances
- [ ] Aerials Won, Aerial Win %
- [ ] Pressures, Pressure Regains (PPDA)

### Discipline
- [ ] Yellow Cards, Red Cards
- [ ] Fouls Committed, Fouls Won

### Percentile Rankings
- [ ] Percentile vs position peers
- [ ] Percentile vs league
- [ ] Per 90 stats with percentiles

---

## Data Sources Summary

| Source | Data Points | Limit | Priority |
|--------|------------|-------|----------|
| FotMob | xG, xA, deep stats, bio | Unlimited | PRIMARY |
| Transfermarkt | Market value, contracts | Scraping | HIGH |
| API-Football | Injuries, lineups | 100/day | SECONDARY |
| StatsBomb | Historical events | Unlimited | HISTORICAL |

---

## Success Criteria

### Data Completeness Targets
| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| Players with fotmob_id | 0% | 100% | Week 1 |
| Players with xG data | 0% | 95% | Week 1 |
| Players with market value | 0% | 80% | Week 2 |
| Players with contract date | 0% | 80% | Week 2 |
| Weekly auto-updates | No | Yes | Week 2 |

### System Health Targets
- API response time < 500ms
- Data freshness < 7 days
- Zero duplicate players
- 99% uptime for scheduler

---

## Files to Create/Modify

### New Files
```
scrapers/transfermarkt/__init__.py
scrapers/transfermarkt/client.py
etl/transfermarkt_etl.py
utils/player_matching.py
utils/data_quality.py
scheduler/run_scheduler.py (update)
```

### Modified Files
```
scrapers/fotmob/data_parser.py - Add deep stats parsing
etl/fotmob_etl.py - Collect deep stats, store fotmob_id
scheduler/jobs.py - Enable weekly jobs
cli.py - Add new commands
```

---

## Immediate Next Steps

1. **FIX: FotMob deep stats extraction** - The data is there, we're just not parsing it
2. **FIX: Store fotmob_id on players** - Critical for deduplication
3. **RUN: Full deep collection** - `python cli.py fotmob collect-deep --league premier-league`
4. **ENABLE: Weekly scheduler** - Automated updates
5. **ADD: Transfermarkt scraper** - Market values

---

*This plan will be executed starting Phase 1 immediately.*
