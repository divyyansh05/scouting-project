# Data-ETL-Pipeline - Known Issues & Bug Tracker

> This file tracks all known issues, bugs, and improvements needed in the project.
> Issues are categorized by severity and component.

---

## Critical Issues (Blocking Functionality)

_No critical issues currently blocking functionality._

---

## High Severity Issues

### ISSUE-002: API-Football Free Plan Pagination Limit
**Status**: Open (mitigated)
**Severity**: High
**Component**: Scrapers / API-Football
**First Seen**: 2026-02-03

**Error Message**:
```json
{"plan": "Free plans are limited to a maximum value of 3 for the Page parameter"}
```

**Location**: `scrapers/api_football/client.py:320`

**Root Cause**: Free API-Football plans only allow pagination up to page 3 (60 players per team). Many teams have 60+ players in their squad data.

**Impact**:
- Cannot fetch complete player rosters via API-Football
- Missing ~25-40% of squad data for large teams

**Mitigation**: FotMob is now the primary data source and has no pagination limits. Full squad data is available via `python cli.py fotmob collect-deep`.

**Long-term Solution**: Upgrade to paid API-Football plan if needed for secondary data enrichment.

---

### ISSUE-003: API-Football Rate Limit Retry Behavior
**Status**: Open (mitigated)
**Severity**: High
**Component**: Scrapers / API-Football

**Observed Behavior**: After hitting rate limit, the client waits 60 seconds and retries 3 times. If all fail, it silently moves to the next team.

**Impact**:
- Wasted API requests on failed retries
- Missing data for teams that hit rate limits

**Mitigation**: FotMob is now primary with no rate limit issues. API-Football is secondary.

---

### ISSUE-004: Missing `api_football_id` Columns
**Status**: Resolved
**Severity**: High
**Component**: Database Schema
**Date Fixed**: 2026-02-07

**Location**: `etl/api_football_etl.py:193-203`

**Root Cause**: The API-Football ETL tries to store `api_football_id` on leagues, teams, players, and `api_football_fixture_id` on matches, but these columns don't exist.

**Resolution**: Ran `database/migration_001_api_football_ids.sql` which added all required columns and indexes.

---

## Medium Severity Issues

### ISSUE-008: Inconsistent Season Name Formatting
**Status**: Resolved
**Severity**: Medium
**Component**: ETL / Data Consistency
**Date Fixed**: 2026-02-07

**Observed**:
- Database has: `2023-24`, `2024-25`
- StatsBomb uses: `2020/2021`
- API-Football uses: `2023` (single year)
- FotMob uses: `2024/2025`

**Resolution**: Created centralized `utils/season_utils.py` with `SeasonUtils` class providing:
- `to_db_format()` - Convert any format to DB format (2024-25)
- `to_fotmob_format()` - Convert to FotMob format (2024/2025)
- `to_single_year()` - Convert to single year (2024)
- `normalize_season()` - Alias for to_db_format()
- `are_same_season()` - Compare seasons in different formats

---

### ISSUE-010: Server Missing HTML Templates
**Status**: Resolved (Verified)
**Severity**: Medium
**Component**: Server

**Location**: `server/app.py` references templates like `index.html`, `teams.html`, etc.

**Verification**: All templates exist in `server/templates/`:
- `index.html` (29KB) - Main dashboard
- `layout.html` (6KB) - Base template
- `teams.html` (2KB) - Team listing
- `team_detail.html` (10KB) - Team details
- `players.html` (14KB) - Player listing
- `player_detail.html` (10KB) - Player details
- `matches.html` (2KB) - Match listing
- `match_detail.html` (4KB) - Match details

---

### ISSUE-013: Understat Web Scraping Not Working
**Status**: Open
**Severity**: Medium
**Component**: Scrapers / Understat
**First Seen**: 2026-02-07

**Root Cause**: Understat.com has changed their page structure. The `playersData` and `teamsData` JavaScript variables are no longer embedded in the HTML as `JSON.parse()` calls.

**Impact**: Cannot collect xA, npxG, xGChain, xGBuildup metrics from Understat.

**Workaround**: Use FotMob xG data (available) and StatsBomb for historical advanced stats.

**Proposed Fix**: Need to investigate new page structure - data may now be loaded via AJAX or different embedding format.

---

### ISSUE-014: FotMob API Response Format Change
**Status**: Resolved
**Severity**: Medium
**Component**: Scrapers / FotMob
**Date Fixed**: 2026-02-07

**Root Cause**: FotMob API changed response structure:
- Old: `table.data[0].table.all[]`
- New: `table[0].data.table.all[]`

**Resolution**: Updated `scrapers/fotmob/data_parser.py` to handle both formats in `parse_league_standings()` and `parse_xg_table()`.

---

### ISSUE-015: StatsBomb NaN Player Names
**Status**: Resolved
**Severity**: Medium
**Component**: ETL / StatsBomb
**Date Fixed**: 2026-02-07

**Error**: `operator does not exist: character varying = double precision` when player_name is NaN.

**Resolution**: Added NaN/None check in `_get_player_id_by_name()` in `etl/statsbomb_advanced_etl.py`.

---

## Low Severity Issues

### ISSUE-011: Hardcoded Database Port
**Status**: Open
**Severity**: Low
**Component**: Configuration

**Location**: `config/settings.py`
```python
DB_PORT = os.getenv('DB_PORT', '5434')
```

**Note**: Port 5434 is non-standard (PostgreSQL default is 5432). This is intentional to avoid conflicts but should be documented.

---

## Proposed Migrations

### Migration 001: Add API-Football ID Columns
```sql
-- migration_001_api_football_ids.sql
ALTER TABLE leagues ADD COLUMN IF NOT EXISTS api_football_id INTEGER;
ALTER TABLE teams ADD COLUMN IF NOT EXISTS api_football_id INTEGER;
ALTER TABLE players ADD COLUMN IF NOT EXISTS api_football_id INTEGER;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS api_football_fixture_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_leagues_api_football_id ON leagues(api_football_id);
CREATE INDEX IF NOT EXISTS idx_teams_api_football_id ON teams(api_football_id);
CREATE INDEX IF NOT EXISTS idx_players_api_football_id ON players(api_football_id);
CREATE INDEX IF NOT EXISTS idx_matches_api_football_fixture_id ON matches(api_football_fixture_id);
```

### Migration 002: FotMob + New Leagues (COMPLETED)
```sql
-- database/migration_002_fotmob_and_leagues.sql
-- Already created and available. Adds:
-- - fotmob_id columns to leagues, teams, players, matches
-- - Eredivisie, Brasileiro Serie A, Argentina Primera leagues
-- - 'fotmob' data source
-- - Drops legacy fbref_id/understat_id columns
```

---

## Issue Resolution Log

| Issue | Date Fixed | Fixed By | Notes |
|-------|------------|----------|-------|
| ISSUE-001 | 2026-02-04 | Claude | Changed `standings` to `team_season_stats` in cli.py system_stats |
| ISSUE-005 | 2026-02-04 | Claude | Resolved by migration_002 (fotmob_match_id added) |
| ISSUE-006 | 2026-02-04 | Claude | Resolved by migration_002 (fotmob_id replaces fbref_id on teams) |
| ISSUE-007 | 2026-02-04 | Claude | Resolved by migration_002 (fotmob_id replaces fbref_id on players) |
| ISSUE-010 | 2026-02-06 | Claude | Verified all 8 templates exist in server/templates/ |
| ISSUE-012 | 2026-02-04 | Claude | Cleaned up imports during FBref/Soccerway removal |
| ISSUE-004 | 2026-02-07 | Claude | Ran migration_001_api_football_ids.sql |
| ISSUE-008 | 2026-02-07 | Claude | Created utils/season_utils.py for format conversion |
| ISSUE-014 | 2026-02-07 | Claude | Updated FotMob parser for new API format |
| ISSUE-015 | 2026-02-07 | Claude | Added NaN check in StatsBomb ETL |

---

## How to Report New Issues

1. Add issue with next available ISSUE-XXX number
2. Include:
   - Status (Open/In Progress/Fixed)
   - Severity (Critical/High/Medium/Low)
   - Component affected
   - Error message (if applicable)
   - Location in code
   - Root cause analysis
   - Proposed fix
3. Update this file when issues are fixed
