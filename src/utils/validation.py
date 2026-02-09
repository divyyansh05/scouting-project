"""
Metrics Validation Module - utils/validation.py

PURPOSE:
--------
This module enforces the metric registry as the SINGLE SOURCE OF TRUTH.
It prevents:
  1. LLM hallucinations (can't request fake metrics)
  2. Typos in metric names
  3. Invalid metric combinations
  4. Requests for metrics we can't compute

CRITICAL PRINCIPLE:
------------------
If a metric is not in the registry, it DOES NOT EXIST.
No exceptions.

USAGE PATTERN:
-------------
# In services/llm_service.py
from utils.validation import validate_requested_metrics, get_metric_metadata

# LLM parsed this from user query
requested_metrics = ["goals_per90", "xg_per90", "fake_metric"]

# Validate before processing
try:
    valid_metrics = validate_requested_metrics(requested_metrics)
    # Continue with valid_metrics...
except ValueError as e:
    # Tell user (via LLM) that metric doesn't exist
    return f"Error: {e}"
"""

import yaml
import logging
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from functools import lru_cache

logger = logging.getLogger(__name__)


# ============================================================================
# REGISTRY LOADING
# ============================================================================

@lru_cache(maxsize=1)
def load_metrics_registry() -> dict:
    """
    Load metrics registry from YAML file.

    Cached to avoid repeated file I/O.

    Returns:
        Dict containing full registry

    Raises:
        FileNotFoundError: If registry file doesn't exist
        yaml.YAMLError: If YAML is malformed
    """
    registry_path = Path(__file__).parent.parent / 'config' / 'metrics_registry.yaml'

    if not registry_path.exists():
        raise FileNotFoundError(
            f"Metrics registry not found at {registry_path}. "
            f"Cannot validate metrics without registry."
        )

    try:
        with open(registry_path, 'r') as f:
            registry = yaml.safe_load(f)

        logger.info(
            f"Loaded metrics registry v{registry.get('version', 'unknown')} "
            f"with {len(registry.get('metrics', {}))} metrics"
        )

        return registry

    except yaml.YAMLError as e:
        logger.error(f"Failed to parse metrics registry: {e}")
        raise


def reload_metrics_registry():
    """
    Force reload of metrics registry (clears cache).

    Use this during development when registry is updated.
    """
    load_metrics_registry.cache_clear()
    logger.info("Metrics registry cache cleared")


# ============================================================================
# CORE VALIDATION FUNCTIONS
# ============================================================================

def validate_metric_exists(metric_id: str) -> bool:
    """
    Check if a metric exists in the registry.

    Args:
        metric_id: Metric identifier (e.g., 'goals_per90')

    Returns:
        True if metric exists, False otherwise
    """
    registry = load_metrics_registry()
    return metric_id in registry.get('metrics', {})


def validate_requested_metrics(
    requested_metrics: List[str],
    strict: bool = True
) -> List[str]:
    """
    Validate a list of requested metrics against the registry.

    This is the PRIMARY FUNCTION to prevent LLM hallucinations.

    Args:
        requested_metrics: List of metric identifiers to validate
        strict: If True, raise error on invalid metrics.
                If False, filter out invalid and return only valid ones.

    Returns:
        List of valid metric identifiers

    Raises:
        ValueError: If strict=True and any metric is invalid

    Example:
        >>> validate_requested_metrics(['goals_per90', 'xg_per90'])
        ['goals_per90', 'xg_per90']

        >>> validate_requested_metrics(['goals_per90', 'fake_metric'])
        ValueError: Invalid metrics: fake_metric

        >>> validate_requested_metrics(['goals_per90', 'fake_metric'], strict=False)
        ['goals_per90']
    """
    registry = load_metrics_registry()
    valid_metrics = set(registry.get('metrics', {}).keys())

    # Find invalid metrics
    requested_set = set(requested_metrics)
    invalid_metrics = requested_set - valid_metrics

    if invalid_metrics:
        if strict:
            raise ValueError(
                f"Invalid metrics requested: {', '.join(sorted(invalid_metrics))}. "
                f"These metrics do not exist in the registry. "
                f"Valid metrics are: {', '.join(sorted(list(valid_metrics)[:10]))}..."
            )
        else:
            logger.warning(
                f"Filtered out invalid metrics: {', '.join(sorted(invalid_metrics))}"
            )

    # Return only valid metrics (preserving order)
    valid_requested = [m for m in requested_metrics if m in valid_metrics]

    logger.info(f"Validated {len(valid_requested)}/{len(requested_metrics)} metrics")

    return valid_requested


def resolve_metric_synonyms(user_input: str) -> Optional[str]:
    """
    Resolve user-friendly names to metric identifiers.

    Useful for LLM query parsing where users might say:
    - "goals per game" -> "goals_per90"
    - "pass accuracy" -> "pass_completion_pct"
    - "xG" -> "xg_per90"

    Args:
        user_input: User's metric name or synonym

    Returns:
        Metric identifier if found, None otherwise

    Example:
        >>> resolve_metric_synonyms("pass accuracy")
        'pass_completion_pct'

        >>> resolve_metric_synonyms("xG")
        'xg_per90'
    """
    registry = load_metrics_registry()
    metrics = registry.get('metrics', {})

    # Normalize input
    normalized_input = user_input.lower().strip()

    # Check exact match first
    if normalized_input in metrics:
        return normalized_input

    # Check display names
    for metric_id, metadata in metrics.items():
        display_name = metadata.get('display_name', '').lower()
        if normalized_input == display_name:
            return metric_id

    # Check synonyms
    for metric_id, metadata in metrics.items():
        synonyms = metadata.get('synonyms', [])
        if normalized_input in [s.lower() for s in synonyms]:
            return metric_id

    logger.debug(f"Could not resolve metric synonym: {user_input}")
    return None


def validate_metric_combination(metrics: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate that a combination of metrics is compatible.

    Some metrics shouldn't be compared together (e.g., GK vs FW metrics).

    Args:
        metrics: List of metric identifiers to check

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> validate_metric_combination(['goals_per90', 'assists_per90'])
        (True, None)

        >>> validate_metric_combination(['saves_per90', 'goals_per90'])
        (False, "Cannot combine goalkeeper and outfield metrics")
    """
    registry = load_metrics_registry()
    validation_rules = registry.get('validation_rules', {})
    incompatible = validation_rules.get('incompatible_combinations', [])

    # Check incompatible combinations
    metrics_set = set(metrics)
    for incompatible_pair in incompatible:
        incompatible_set = set(incompatible_pair)
        if len(metrics_set & incompatible_set) > 1:
            return False, (
                f"Cannot combine metrics: {', '.join(incompatible_pair)}. "
                f"These metrics are incompatible."
            )

    return True, None


# ============================================================================
# METADATA RETRIEVAL
# ============================================================================

def get_metric_metadata(metric_id: str) -> Optional[Dict]:
    """
    Get full metadata for a metric.

    Args:
        metric_id: Metric identifier

    Returns:
        Dict of metric metadata, or None if not found

    Example:
        >>> meta = get_metric_metadata('goals_per90')
        >>> print(meta['display_name'])
        'Goals per 90'
        >>> print(meta['description'])
        'Goals scored per 90 minutes'
    """
    registry = load_metrics_registry()
    return registry.get('metrics', {}).get(metric_id)


def get_all_metrics() -> Dict[str, Dict]:
    """
    Get all metrics from registry.

    Returns:
        Dict mapping metric_id to metadata
    """
    registry = load_metrics_registry()
    return registry.get('metrics', {})


def get_metrics_by_category(category: str) -> List[str]:
    """
    Get all metric IDs in a category.

    Args:
        category: Category name (passing, shooting, defending, etc.)

    Returns:
        List of metric identifiers in that category

    Example:
        >>> get_metrics_by_category('shooting')
        ['goals_per90', 'xg_per90', 'shots_per90', 'shots_on_target_per90', ...]
    """
    registry = load_metrics_registry()
    metrics = registry.get('metrics', {})

    return [
        metric_id
        for metric_id, metadata in metrics.items()
        if metadata.get('category') == category
    ]


def get_all_categories() -> List[Dict]:
    """
    Get all metric categories.

    Returns:
        List of category metadata dicts
    """
    registry = load_metrics_registry()
    return registry.get('categories', {})


def get_preset_group(group_name: str) -> Optional[List[str]]:
    """
    Get a preset group of metrics.

    Args:
        group_name: Name of preset group (e.g., 'striker_profile')

    Returns:
        List of metric identifiers, or None if group doesn't exist

    Example:
        >>> get_preset_group('striker_profile')
        ['goals_per90', 'xg_per90', 'shots_per90', 'shot_on_target_pct', ...]
    """
    registry = load_metrics_registry()
    presets = registry.get('preset_groups', {})
    group = presets.get(group_name)

    if group:
        return group.get('metrics', [])
    return None


def get_role_template(role_name: str) -> Optional[Dict]:
    """
    Get a role template from the registry.

    Args:
        role_name: Name of role (e.g., 'defensive_midfielder')

    Returns:
        Dict with role metadata, metrics, and weights
    """
    registry = load_metrics_registry()
    roles = registry.get('roles', {})
    return roles.get(role_name)


def get_all_roles() -> Dict[str, Dict]:
    """
    Get all role templates from the registry.

    Returns:
        Dict mapping role_name to role metadata
    """
    registry = load_metrics_registry()
    return registry.get('roles', {})


# ============================================================================
# POSITION-SPECIFIC VALIDATION
# ============================================================================

def validate_metrics_for_position(
    metrics: List[str],
    position: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate that metrics are appropriate for a position.

    Args:
        metrics: List of metric identifiers
        position: Position code (GK, DF, MF, FW)

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> validate_metrics_for_position(['goals_per90', 'shots_per90'], 'FW')
        (True, None)

        >>> validate_metrics_for_position(['goals_per90'], 'GK')
        (False, "Metric 'goals_per90' not allowed for position GK")
    """
    registry = load_metrics_registry()
    validation_rules = registry.get('validation_rules', {})
    position_restrictions = validation_rules.get('position_restrictions', {})

    if position not in position_restrictions:
        # No restrictions for this position
        return True, None

    restrictions = position_restrictions[position]
    forbidden = restrictions.get('forbidden_metrics', [])

    # Check if any requested metrics are forbidden
    for metric in metrics:
        if metric in forbidden:
            return False, (
                f"Metric '{metric}' is not allowed for position {position}. "
                f"This metric is not applicable to this position."
            )

    return True, None


# ============================================================================
# LLM INTEGRATION HELPERS
# ============================================================================

def validate_llm_metric_request(
    requested_metrics: List[str],
    position: Optional[str] = None,
    return_suggestions: bool = True
) -> Dict:
    """
    Comprehensive validation for LLM-parsed metric requests.

    This is the HIGH-LEVEL function to use in LLM service layer.

    Args:
        requested_metrics: Metrics parsed from user query
        position: Optional position filter
        return_suggestions: If True, suggest similar metrics for invalid ones

    Returns:
        Dict with validation results:
        {
            'valid': List[str] - Valid metrics
            'invalid': List[str] - Invalid metrics
            'suggestions': Dict[str, List[str]] - Suggested alternatives
            'warnings': List[str] - Any warnings
            'errors': List[str] - Any errors
        }

    Example:
        >>> result = validate_llm_metric_request(
        ...     ['goals_per90', 'fake_metric', 'xG'],
        ...     position='FW'
        ... )
        >>> print(result['valid'])
        ['goals_per90', 'xg_per90']  # 'xG' resolved to 'xg_per90'
        >>> print(result['invalid'])
        ['fake_metric']
        >>> print(result['suggestions']['fake_metric'])
        ['goals_per90', 'xg_per90']  # Similar metrics
    """
    result = {
        'valid': [],
        'invalid': [],
        'suggestions': {},
        'warnings': [],
        'errors': []
    }

    # Step 1: Resolve synonyms
    resolved_metrics = []
    for metric in requested_metrics:
        resolved = resolve_metric_synonyms(metric)
        if resolved:
            resolved_metrics.append(resolved)
        else:
            result['invalid'].append(metric)

    # Step 2: Validate existence
    try:
        valid_metrics = validate_requested_metrics(resolved_metrics, strict=False)
        result['valid'] = valid_metrics
    except ValueError as e:
        result['errors'].append(str(e))

    # Step 3: Check compatibility
    if len(result['valid']) > 1:
        is_compatible, error = validate_metric_combination(result['valid'])
        if not is_compatible:
            result['warnings'].append(error)

    # Step 4: Position validation
    if position and result['valid']:
        is_valid, error = validate_metrics_for_position(result['valid'], position)
        if not is_valid:
            result['errors'].append(error)

    # Step 5: Generate suggestions for invalid metrics
    if return_suggestions and result['invalid']:
        for invalid_metric in result['invalid']:
            suggestions = suggest_similar_metrics(invalid_metric, n=3)
            if suggestions:
                result['suggestions'][invalid_metric] = suggestions

    return result


def suggest_similar_metrics(user_input: str, n: int = 5) -> List[str]:
    """
    Suggest similar metrics based on fuzzy matching.

    Useful when user makes typos or uses non-standard names.

    Args:
        user_input: User's input
        n: Number of suggestions to return

    Returns:
        List of suggested metric identifiers

    Example:
        >>> suggest_similar_metrics('goal per 90', n=3)
        ['goals_per90', 'xg_per90', 'npxg_per90']
    """
    from difflib import get_close_matches

    registry = load_metrics_registry()
    metrics = registry.get('metrics', {})

    # Create searchable strings (metric_id + display_name + synonyms)
    searchable = {}
    for metric_id, metadata in metrics.items():
        search_terms = [
            metric_id,
            metadata.get('display_name', '').lower(),
            *[s.lower() for s in metadata.get('synonyms', [])]
        ]
        searchable[metric_id] = ' '.join(search_terms)

    # Find close matches
    user_input_lower = user_input.lower()
    matches = []

    # Try exact substring matches first
    for metric_id, search_str in searchable.items():
        if user_input_lower in search_str:
            matches.append(metric_id)

    # If not enough matches, use fuzzy matching
    if len(matches) < n:
        all_search_strs = list(searchable.values())
        fuzzy_matches = get_close_matches(user_input_lower, all_search_strs, n=n*2, cutoff=0.4)

        for fuzzy in fuzzy_matches:
            for metric_id, search_str in searchable.items():
                if search_str == fuzzy and metric_id not in matches:
                    matches.append(metric_id)

    return matches[:n]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_metric_display_name(metric_id: str) -> str:
    """
    Get human-readable display name for a metric.

    Args:
        metric_id: Metric identifier

    Returns:
        Display name, or metric_id if not found
    """
    metadata = get_metric_metadata(metric_id)
    if metadata:
        return metadata.get('display_name', metric_id)
    return metric_id


def is_higher_better(metric_id: str) -> bool:
    """
    Check if higher values are better for this metric.

    Important for percentile calculations and rankings.

    Args:
        metric_id: Metric identifier

    Returns:
        True if higher is better, False if lower is better
    """
    metadata = get_metric_metadata(metric_id)
    if metadata:
        return metadata.get('higher_is_better', True)
    return True  # Default to higher is better


def get_minimum_minutes_required(metric_id: str) -> int:
    """
    Get minimum minutes required for meaningful metric calculation.

    Args:
        metric_id: Metric identifier

    Returns:
        Minimum minutes required
    """
    metadata = get_metric_metadata(metric_id)
    if metadata:
        return metadata.get('requires_minimum_minutes', 450)
    return 450  # Default to ~5 matches


def format_metric_value(metric_id: str, value: float) -> str:
    """
    Format a metric value for display.

    Args:
        metric_id: Metric identifier
        value: Metric value

    Returns:
        Formatted string

    Example:
        >>> format_metric_value('goals_per90', 0.75)
        '0.75'
        >>> format_metric_value('pass_completion_pct', 87.3)
        '87.3%'
    """
    metadata = get_metric_metadata(metric_id)
    if not metadata:
        return str(value)

    precision = metadata.get('precision', 1)
    unit = metadata.get('unit', '')

    formatted = f"{value:.{precision}f}"

    if unit == 'percent':
        formatted += '%'
    elif unit and unit not in ['goals', 'passes', 'shots']:
        formatted += f' {unit}'

    return formatted


# ============================================================================
# DEBUGGING AND DEVELOPMENT
# ============================================================================

def list_all_metrics(verbose: bool = False) -> None:
    """
    Print all available metrics (for debugging).

    Args:
        verbose: If True, print full metadata
    """
    registry = load_metrics_registry()
    metrics = registry.get('metrics', {})

    print(f"\n{'='*80}")
    print(f"AVAILABLE METRICS ({len(metrics)} total)")
    print(f"{'='*80}\n")

    # Group by category
    categories = {}
    for metric_id, metadata in metrics.items():
        category = metadata.get('category', 'uncategorized')
        if category not in categories:
            categories[category] = []
        categories[category].append((metric_id, metadata))

    # Print by category
    for category, items in sorted(categories.items()):
        print(f"\n{category.upper()}")
        print("-" * 40)
        for metric_id, metadata in sorted(items):
            if verbose:
                print(f"  {metric_id}")
                print(f"    Display: {metadata.get('display_name')}")
                print(f"    Description: {metadata.get('description')}")
                print(f"    Synonyms: {', '.join(metadata.get('synonyms', []))}")
            else:
                print(f"  {metric_id:40} - {metadata.get('display_name')}")

    print(f"\n{'='*80}\n")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    """
    Example usage and testing.
    """

    print("METRICS VALIDATION MODULE - Examples")
    print("=" * 80)

    # Example 1: Basic validation
    print("\n1. Basic Validation")
    print("-" * 40)
    try:
        valid = validate_requested_metrics(['goals_per90', 'xg_per90', 'assists_per90'])
        print(f"Valid metrics: {valid}")
    except ValueError as e:
        print(f"Error: {e}")

    # Example 2: Invalid metric
    print("\n2. Invalid Metric (strict mode)")
    print("-" * 40)
    try:
        valid = validate_requested_metrics(['goals_per90', 'fake_metric'])
        print(f"Valid metrics: {valid}")
    except ValueError as e:
        print(f"Error: {e}")

    # Example 3: Invalid metric (non-strict)
    print("\n3. Invalid Metric (non-strict mode)")
    print("-" * 40)
    valid = validate_requested_metrics(
        ['goals_per90', 'fake_metric', 'xg_per90'],
        strict=False
    )
    print(f"Valid metrics: {valid}")

    # Example 4: Synonym resolution
    print("\n4. Synonym Resolution")
    print("-" * 40)
    synonyms_to_test = ['xG', 'pass accuracy', 'goals per game']
    for syn in synonyms_to_test:
        resolved = resolve_metric_synonyms(syn)
        print(f"  '{syn}' -> {resolved}")

    # Example 5: LLM request validation
    print("\n5. LLM Request Validation")
    print("-" * 40)
    result = validate_llm_metric_request(
        ['goals_per90', 'xG', 'fake_metric'],
        position='FW',
        return_suggestions=True
    )
    print(f"Valid: {result['valid']}")
    print(f"Invalid: {result['invalid']}")
    print(f"Suggestions: {result['suggestions']}")

    # Example 6: Get metrics by category
    print("\n6. Metrics by Category")
    print("-" * 40)
    shooting_metrics = get_metrics_by_category('shooting')
    print(f"Shooting metrics ({len(shooting_metrics)}): {shooting_metrics[:5]}...")

    # Example 7: Preset groups
    print("\n7. Preset Groups")
    print("-" * 40)
    striker_profile = get_preset_group('striker_profile')
    print(f"Striker profile metrics: {striker_profile}")

    print("\n" + "=" * 80)
