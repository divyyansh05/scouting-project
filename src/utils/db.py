"""
Database Access Layer - utils/db.py

ARCHITECTURE PRINCIPLE: ISOLATION OF DATA ACCESS
================================================

This module is the SINGLE POINT OF CONTACT with the database.
All database operations MUST flow through these functions.

WHY ISOLATION MATTERS:
---------------------
1. SECURITY: Enforces read-only access at the architectural level
2. MAINTAINABILITY: Database changes only affect this one file
3. TESTABILITY: Easy to mock for unit tests
4. AUDITABILITY: All queries logged in one place
5. PREVENTS DRIFT: Services cannot accidentally write to DB

STRICT RULES:
------------
- NO INSERT, UPDATE, DELETE, DROP operations
- NO transaction management (read-only doesn't need it)
- NO business logic (just data retrieval)
- ALL queries must be parameterized (SQL injection prevention)

USAGE PATTERN:
-------------
    # In services/metrics_service.py
    from utils.db import fetch_dataframe

    df = fetch_dataframe(
        "SELECT * FROM player_stats WHERE player_id = %s",
        params=(player_id,)
    )
    # Now compute metrics on df...
"""

import psycopg2
from psycopg2 import pool, extras
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import pandas as pd
import logging
from typing import Optional, Tuple, List, Dict, Any
from contextlib import contextmanager
import os
import yaml
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION LOADING
# ============================================================================

def load_db_config() -> dict:
    """
    Load database configuration from environment and settings.yaml.

    Priority: Environment variables > settings.yaml > defaults

    Returns:
        Dict with database connection parameters
    """
    config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'scouting_raw'),
        'user': os.getenv('DB_USER', 'readonly_user'),
        'password': os.getenv('DB_PASSWORD', ''),
    }

    # Try to load from settings.yaml if it exists
    config_path = Path(__file__).parent.parent / 'config' / 'settings.yaml'
    if config_path.exists():
        with open(config_path, 'r') as f:
            settings = yaml.safe_load(f)
            db_settings = settings.get('database', {})

            # Only override if not set in environment
            for key in ['host', 'port', 'database', 'user', 'password']:
                env_key = f'DB_{key.upper()}'
                if env_key not in os.environ and key in db_settings:
                    config[key] = db_settings[key]

    # Validate required fields
    if not config['password']:
        logger.warning("Database password not set! Connection will likely fail.")

    return config


# ============================================================================
# CONNECTION POOL MANAGEMENT
# ============================================================================

class DatabasePool:
    """
    Singleton connection pool manager.

    Uses psycopg2's ThreadedConnectionPool for safe concurrent access.
    All connections are configured as READ-ONLY.
    """

    _instance = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabasePool, cls).__new__(cls)
        return cls._instance

    def initialize(self, min_conn: int = 1, max_conn: int = 10):
        """
        Initialize the connection pool.

        Args:
            min_conn: Minimum number of connections to maintain
            max_conn: Maximum number of connections allowed
        """
        if self._pool is not None:
            logger.warning("Connection pool already initialized")
            return

        config = load_db_config()

        try:
            self._pool = pool.ThreadedConnectionPool(
                minconn=min_conn,
                maxconn=max_conn,
                host=config['host'],
                port=config['port'],
                database=config['database'],
                user=config['user'],
                password=config['password'],
                # Additional safety settings
                options='-c default_transaction_read_only=on'  # ENFORCE READ-ONLY
            )
            logger.info(
                f"Database pool initialized: {config['user']}@{config['host']}:"
                f"{config['port']}/{config['database']} (READ-ONLY)"
            )
        except psycopg2.Error as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise

    def get_connection(self):
        """
        Get a connection from the pool.

        Returns:
            psycopg2 connection object (READ-ONLY)

        Raises:
            RuntimeError: If pool not initialized
            psycopg2.Error: If connection fails
        """
        if self._pool is None:
            raise RuntimeError(
                "Database pool not initialized. Call initialize() first."
            )

        try:
            conn = self._pool.getconn()
            # Double-check read-only mode
            conn.set_session(readonly=True, autocommit=True)
            return conn
        except psycopg2.Error as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise

    def return_connection(self, conn):
        """
        Return a connection to the pool.

        Args:
            conn: psycopg2 connection to return
        """
        if self._pool is not None and conn is not None:
            self._pool.putconn(conn)

    def close_all(self):
        """Close all connections in the pool."""
        if self._pool is not None:
            self._pool.closeall()
            logger.info("All database connections closed")
            self._pool = None


# Global pool instance
_db_pool = DatabasePool()


def initialize_db_pool(min_conn: int = 1, max_conn: int = 10):
    """
    Initialize the global database connection pool.

    Call this once at application startup.

    Args:
        min_conn: Minimum number of connections
        max_conn: Maximum number of connections
    """
    _db_pool.initialize(min_conn, max_conn)


def close_db_pool():
    """Close the global database connection pool."""
    _db_pool.close_all()


# ============================================================================
# CONNECTION CONTEXT MANAGER
# ============================================================================

@contextmanager
def get_connection():
    """
    Context manager for safe database connections.

    Automatically returns connection to pool on exit.
    Handles errors gracefully.

    Usage:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ...")

    Yields:
        psycopg2 connection object (READ-ONLY)
    """
    conn = None
    try:
        conn = _db_pool.get_connection()
        yield conn
    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn is not None:
            _db_pool.return_connection(conn)


# ============================================================================
# QUERY VALIDATION
# ============================================================================

def validate_query_is_readonly(query: str) -> bool:
    """
    Validate that a query is read-only.

    SECURITY CRITICAL: Prevents accidental writes to database.

    Args:
        query: SQL query string

    Returns:
        True if valid read-only query

    Raises:
        ValueError: If query contains write operations
    """
    query_upper = query.upper().strip()

    # List of forbidden operations
    forbidden_keywords = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
        'TRUNCATE', 'REPLACE', 'MERGE', 'GRANT', 'REVOKE'
    ]

    for keyword in forbidden_keywords:
        if keyword in query_upper:
            raise ValueError(
                f"FORBIDDEN: Query contains write operation '{keyword}'. "
                f"This application is READ-ONLY."
            )

    # Must start with SELECT, WITH, or EXPLAIN
    valid_starts = ['SELECT', 'WITH', 'EXPLAIN', '(SELECT', '(WITH']
    if not any(query_upper.startswith(start) for start in valid_starts):
        raise ValueError(
            f"Invalid query: Must start with SELECT, WITH, or EXPLAIN. "
            f"Got: {query[:50]}..."
        )

    return True


# ============================================================================
# CORE QUERY FUNCTIONS
# ============================================================================

def execute_query(
    query: str,
    params: Optional[Tuple] = None,
    fetch_size: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Execute a read-only SQL query and return results as list of dicts.

    Args:
        query: SQL query string (must be SELECT)
        params: Query parameters (use %s placeholders)
        fetch_size: Number of rows to fetch (None = all)

    Returns:
        List of dicts, where each dict is a row with column names as keys

    Raises:
        ValueError: If query is not read-only
        psycopg2.Error: If query execution fails

    Example:
        >>> results = execute_query(
        ...     "SELECT * FROM players WHERE position = %s",
        ...     params=('MF',)
        ... )
        >>> print(results[0])
        {'player_id': 123, 'name': 'Player Name', 'position': 'MF', ...}
    """
    # Validate query safety
    validate_query_is_readonly(query)

    results = []
    with get_connection() as conn:
        # Use RealDictCursor to get dict results
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            try:
                logger.debug(f"Executing query: {query[:100]}... with params: {params}")
                cursor.execute(query, params)

                if fetch_size:
                    results = cursor.fetchmany(fetch_size)
                else:
                    results = cursor.fetchall()

                logger.debug(f"Query returned {len(results)} rows")

            except psycopg2.Error as e:
                logger.error(f"Query execution failed: {e}")
                logger.error(f"Query: {query}")
                logger.error(f"Params: {params}")
                raise

    # Convert to list of dicts (RealDictCursor returns RealDictRow objects)
    return [dict(row) for row in results]


def fetch_dataframe(
    query: str,
    params: Optional[Tuple] = None,
    parse_dates: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Execute a read-only SQL query and return results as pandas DataFrame.

    This is the PRIMARY function to use in service layers.

    Args:
        query: SQL query string (must be SELECT)
        params: Query parameters (use %s placeholders)
        parse_dates: List of column names to parse as datetime

    Returns:
        pandas DataFrame with query results

    Raises:
        ValueError: If query is not read-only
        psycopg2.Error: If query execution fails

    Example:
        >>> df = fetch_dataframe(
        ...     "SELECT * FROM player_stats WHERE player_id = %s",
        ...     params=(123,),
        ...     parse_dates=['match_date']
        ... )
        >>> print(df.head())
    """
    # Validate query safety
    validate_query_is_readonly(query)

    with get_connection() as conn:
        try:
            logger.debug(f"Fetching DataFrame: {query[:100]}... with params: {params}")

            df = pd.read_sql_query(
                query,
                conn,
                params=params,
                parse_dates=parse_dates
            )

            logger.debug(f"DataFrame shape: {df.shape}")
            return df

        except psycopg2.Error as e:
            logger.error(f"DataFrame fetch failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise


def fetch_single_value(query: str, params: Optional[Tuple] = None) -> Any:
    """
    Execute query and return single value (first column of first row).

    Useful for COUNT queries, single metric lookups, etc.

    Args:
        query: SQL query string
        params: Query parameters

    Returns:
        Single value (can be any type), or None if no results

    Example:
        >>> count = fetch_single_value(
        ...     "SELECT COUNT(*) FROM players WHERE position = %s",
        ...     params=('MF',)
        ... )
        >>> print(count)  # e.g., 450
    """
    validate_query_is_readonly(query)

    with get_connection() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute(query, params)
                result = cursor.fetchone()
                return result[0] if result else None
            except psycopg2.Error as e:
                logger.error(f"Single value fetch failed: {e}")
                raise


def test_connection() -> bool:
    """
    Test database connection.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result[0] == 1:
                    logger.info("Database connection test: SUCCESS")
                    return True
    except Exception as e:
        logger.error(f"Database connection test: FAILED - {e}")
        return False


# ============================================================================
# HELPER FUNCTIONS FOR COMMON QUERIES
# ============================================================================

def get_table_columns(table_name: str) -> List[str]:
    """
    Get list of column names for a table.

    Args:
        table_name: Name of the table

    Returns:
        List of column names
    """
    query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """

    results = execute_query(query, params=(table_name,))
    return [row['column_name'] for row in results]


def table_exists(table_name: str) -> bool:
    """
    Check if a table exists in the database.

    Args:
        table_name: Name of the table

    Returns:
        True if table exists
    """
    query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = %s
        )
    """

    return fetch_single_value(query, params=(table_name,))


# ============================================================================
# APPLICATION LIFECYCLE
# ============================================================================

def startup_db():
    """
    Initialize database connections at application startup.

    Call this in app.py before starting the Dash server.
    """
    logger.info("Starting database connection pool...")

    # Load pool size from config
    config_path = Path(__file__).parent.parent / 'config' / 'settings.yaml'
    pool_size = 5
    max_overflow = 10

    if config_path.exists():
        with open(config_path, 'r') as f:
            settings = yaml.safe_load(f)
            db_settings = settings.get('database', {})
            pool_size = db_settings.get('pool_size', 5)
            max_overflow = db_settings.get('max_overflow', 10)

    initialize_db_pool(min_conn=pool_size, max_conn=pool_size + max_overflow)

    # Test connection
    if test_connection():
        logger.info("Database ready for queries (READ-ONLY mode)")
    else:
        logger.error("Database connection failed! Check configuration.")
        raise RuntimeError("Database initialization failed")


def shutdown_db():
    """
    Close database connections at application shutdown.

    Call this in cleanup handlers.
    """
    logger.info("Shutting down database connection pool...")
    close_db_pool()


# ============================================================================
# EXAMPLE USAGE (for documentation)
# ============================================================================

if __name__ == "__main__":
    """
    Example usage of the database layer.

    DO NOT use this in production - this is for testing only.
    """

    # Initialize
    startup_db()

    try:
        # Test connection
        print("Testing connection...")
        test_connection()

        # Example 1: Fetch as DataFrame
        print("\nExample 1: Fetch player data")
        df = fetch_dataframe(
            """
            SELECT player_id, name, position, age
            FROM players
            WHERE position = %s
            LIMIT 5
            """,
            params=('MF',)
        )
        print(df)

        # Example 2: Fetch as list of dicts
        print("\nExample 2: Fetch as dicts")
        results = execute_query(
            "SELECT COUNT(*) as count FROM players WHERE position = %s",
            params=('MF',)
        )
        print(results)

        # Example 3: Single value
        print("\nExample 3: Single value")
        count = fetch_single_value(
            "SELECT COUNT(*) FROM players WHERE position = %s",
            params=('MF',)
        )
        print(f"Midfielder count: {count}")

        # Example 4: Check table exists
        print("\nExample 4: Table exists")
        exists = table_exists('players')
        print(f"Table 'players' exists: {exists}")

        # Example 5: Get columns
        print("\nExample 5: Get table columns")
        columns = get_table_columns('players')
        print(f"Columns: {columns}")

        # Example 6: Try invalid query (should fail)
        print("\nExample 6: Test read-only enforcement")
        try:
            execute_query("DELETE FROM players WHERE player_id = 1")
        except ValueError as e:
            print(f"Correctly blocked: {e}")

    finally:
        # Cleanup
        shutdown_db()
