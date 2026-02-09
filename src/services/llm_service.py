"""
LLM Service - services/llm_service.py

RESPONSIBILITIES:
-----------------
Convert natural language queries into structured JSON for the analytics engine.

CRITICAL SCOPE LIMITATION:
-------------------------
This service ONLY does QUERY PARSING.
It does NOT:
- Compute metrics (that's metrics_service.py)
- Execute SQL (that's utils/db.py)
- Generate explanations (future feature)
- Create visualizations (that's visualization/)

ARCHITECTURE:
------------
    User: "Find players similar to Rodri but younger"
        |
    LLM Service: Parse query
        |
    Output: {"base_player": "Rodri", "age_max": 25, ...}
        |
    Other services: Execute the parsed query

LLM ROLE:
--------
The LLM is a PARSER, not a COMPUTER.
- Parses text -> JSON
- Validates metric names against registry
- Returns structured filters
- NO calculations, NO database access, NO explanations

CRITICAL RULES:
--------------
- LOW TEMPERATURE (0.1-0.3) for deterministic parsing
- STRICT VALIDATION against metrics_registry.yaml
- REJECT unknown metrics (don't hallucinate)
- FALLBACK to safe defaults on unclear queries
- NEVER compute metrics or execute queries
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import validation utilities
from utils.validation import (
    validate_requested_metrics,
    resolve_metric_synonyms,
    get_all_metrics,
    get_metrics_by_category,
    get_preset_group,
    validate_llm_metric_request
)

logger = logging.getLogger(__name__)


# ============================================================================
# LLM API CONFIGURATION
# ============================================================================

# Default LLM settings for query parsing
DEFAULT_LLM_CONFIG = {
    'provider': 'anthropic',  # or 'openai'
    'model': 'claude-sonnet-4',
    'temperature': 0.1,  # Low for deterministic parsing
    'max_tokens': 1000,
    'timeout': 30
}


# ============================================================================
# QUERY PARSING SYSTEM PROMPT
# ============================================================================

def build_parsing_system_prompt() -> str:
    """
    Build system prompt for LLM query parsing.

    This prompt instructs the LLM to parse queries into structured JSON.
    It includes the metrics registry so the LLM knows what metrics exist.

    Returns:
        System prompt string
    """
    # Get available metrics from registry
    all_metrics = get_all_metrics()

    # Build metric reference for LLM
    metric_reference = {}
    for metric_id, metadata in all_metrics.items():
        metric_reference[metric_id] = {
            'display_name': metadata.get('display_name'),
            'category': metadata.get('category'),
            'synonyms': metadata.get('synonyms', [])
        }

    # Get preset groups
    preset_groups = {
        'striker_profile': get_preset_group('striker_profile'),
        'creative_midfielder_profile': get_preset_group('creative_midfielder_profile'),
        'defensive_midfielder_profile': get_preset_group('defensive_midfielder_profile'),
        'winger_profile': get_preset_group('winger_profile'),
        'center_back_profile': get_preset_group('center_back_profile')
    }

    system_prompt = f"""You are a football analytics query parser.

Your ONLY job is to parse natural language queries into structured JSON.
You do NOT compute metrics, execute queries, or generate explanations.

AVAILABLE METRICS (these are the ONLY valid metrics):
{json.dumps(metric_reference, indent=2)}

PRESET METRIC GROUPS:
{json.dumps(preset_groups, indent=2)}

VALID POSITIONS:
- GK (Goalkeeper)
- DF (Defender)
- DM (Defensive Midfielder)
- MF (Midfielder)
- AM (Attacking Midfielder)
- FW (Forward)
- Specific: CB, LB, RB, LWB, RWB, CM, LM, RM, LW, RW, ST, CF

QUERY PARSING RULES:
1. Extract player name (if mentioned)
2. Extract position filters
3. Extract age filters (min/max)
4. Extract league filters
5. Extract metric preferences
6. Map user-friendly terms to exact metric IDs

CRITICAL RULES:
- Use ONLY metric IDs from the available metrics list above
- NEVER invent metric names
- If unsure about a metric, omit it or use preset group
- Use preset groups when user mentions role types
- Low confidence = minimal filters, let the system use defaults

OUTPUT FORMAT (JSON only, no explanations):
{{
  "base_player_name": "Player Name" or null,
  "position": "MF" or null,
  "age_min": int or null,
  "age_max": int or null,
  "leagues": ["League Name"] or null,
  "metrics": ["metric_id_1", "metric_id_2"] or null,
  "metric_groups": ["defending", "possession"] or null,
  "preset_profile": "striker_profile" or null,
  "min_minutes": int or null,
  "similarity_search": true/false,
  "n_results": int or null
}}

EXAMPLES:

Input: "Find players similar to Rodri but younger"
Output:
{{
  "base_player_name": "Rodri",
  "age_max": 25,
  "similarity_search": true,
  "preset_profile": "defensive_midfielder_profile"
}}

Input: "Show me creative midfielders under 23"
Output:
{{
  "position": "MF",
  "age_max": 23,
  "preset_profile": "creative_midfielder_profile"
}}

Input: "Find strikers with high goals and assists"
Output:
{{
  "position": "FW",
  "metrics": ["goals_per90", "assists_per90"]
}}

Input: "Who are the best defenders in La Liga?"
Output:
{{
  "position": "DF",
  "leagues": ["La Liga"],
  "preset_profile": "center_back_profile"
}}

IMPORTANT:
- Return ONLY valid JSON
- No markdown code blocks
- No explanations
- Use exact metric IDs from the list
"""

    return system_prompt


# ============================================================================
# LLM API CALLS (Placeholder - requires actual API integration)
# ============================================================================

def call_llm_api(
    user_message: str,
    system_prompt: str,
    config: Optional[Dict] = None
) -> str:
    """
    Call LLM API for query parsing.

    NOTE: This is a placeholder. In production, replace with actual API calls:
    - Anthropic Claude API
    - OpenAI GPT API

    Args:
        user_message: User's natural language query
        system_prompt: System prompt with instructions
        config: LLM configuration (temperature, model, etc.)

    Returns:
        LLM response (JSON string)

    Example:
        >>> response = call_llm_api(
        ...     "Find players like Rodri",
        ...     system_prompt,
        ...     {'temperature': 0.1}
        ... )
        >>> parsed = json.loads(response)
    """
    if config is None:
        config = DEFAULT_LLM_CONFIG

    # PLACEHOLDER: Replace with actual API call
    #
    # For Anthropic Claude:
    # import anthropic
    # client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    # message = client.messages.create(
    #     model=config['model'],
    #     max_tokens=config['max_tokens'],
    #     temperature=config['temperature'],
    #     system=system_prompt,
    #     messages=[{"role": "user", "content": user_message}]
    # )
    # return message.content[0].text
    #
    # For OpenAI:
    # import openai
    # response = openai.ChatCompletion.create(
    #     model=config['model'],
    #     temperature=config['temperature'],
    #     messages=[
    #         {"role": "system", "content": system_prompt},
    #         {"role": "user", "content": user_message}
    #     ]
    # )
    # return response.choices[0].message.content

    logger.warning("Using mock LLM response - replace with actual API call")

    # Mock response for development/testing
    # In production, this should be replaced with actual API call
    mock_response = {
        "base_player_name": None,
        "position": None,
        "age_min": None,
        "age_max": None,
        "leagues": None,
        "metrics": None,
        "metric_groups": None,
        "preset_profile": None,
        "min_minutes": 450,
        "similarity_search": False,
        "n_results": 10
    }

    return json.dumps(mock_response)


# ============================================================================
# MAIN PARSING FUNCTION
# ============================================================================

def parse_query(
    user_query: str,
    config: Optional[Dict] = None,
    strict_validation: bool = True
) -> Dict:
    """
    Parse natural language query into structured filters.

    This is the PRIMARY FUNCTION of the LLM service.

    WORKFLOW:
    1. Build system prompt with metrics registry
    2. Call LLM API to parse query
    3. Parse LLM response as JSON
    4. Validate metric names against registry
    5. Return validated structured query

    Args:
        user_query: Natural language query from user
        config: Optional LLM configuration
        strict_validation: If True, reject unknown metrics

    Returns:
        Dict with structured query parameters:
        {
            'base_player_name': str or None,
            'position': str or None,
            'age_min': int or None,
            'age_max': int or None,
            'leagues': List[str] or None,
            'metrics': List[str] (validated),
            'metric_groups': List[str] or None,
            'preset_profile': str or None,
            'min_minutes': int,
            'similarity_search': bool,
            'n_results': int,
            'validation_warnings': List[str]
        }

    Raises:
        ValueError: If query cannot be parsed or validation fails

    Example:
        >>> result = parse_query("Find players like Rodri but younger")
        >>> print(result['base_player_name'])
        'Rodri'
        >>> print(result['age_max'])
        25
        >>> print(result['similarity_search'])
        True
    """
    logger.info(f"Parsing query: {user_query}")

    if config is None:
        config = DEFAULT_LLM_CONFIG

    # Step 1: Build system prompt
    system_prompt = build_parsing_system_prompt()

    # Step 2: Call LLM API
    try:
        llm_response = call_llm_api(user_query, system_prompt, config)
    except Exception as e:
        logger.error(f"LLM API call failed: {e}")
        raise ValueError(f"Failed to parse query: {e}")

    # Step 3: Parse JSON response
    try:
        # Strip markdown code blocks if present
        llm_response = llm_response.strip()
        if llm_response.startswith('```'):
            # Remove markdown code blocks
            llm_response = llm_response.replace('```json', '').replace('```', '').strip()

        parsed = json.loads(llm_response)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"LLM response was: {llm_response}")
        raise ValueError(f"LLM returned invalid JSON: {e}")

    # Step 4: Validate and clean
    validated = validate_parsed_query(parsed, strict=strict_validation)

    logger.info(
        f"Successfully parsed query: "
        f"position={validated.get('position')}, "
        f"similarity_search={validated.get('similarity_search')}, "
        f"metrics={len(validated.get('metrics', []))}"
    )

    return validated


def validate_parsed_query(parsed: Dict, strict: bool = True) -> Dict:
    """
    Validate parsed query against metrics registry.

    This ensures the LLM didn't hallucinate metric names.

    Args:
        parsed: Dict from LLM parsing
        strict: If True, reject unknown metrics

    Returns:
        Validated and cleaned query dict
    """
    validated = {}
    validation_warnings = []

    # Basic fields (no validation needed)
    validated['base_player_name'] = parsed.get('base_player_name')
    validated['position'] = parsed.get('position')
    validated['age_min'] = parsed.get('age_min')
    validated['age_max'] = parsed.get('age_max')
    validated['leagues'] = parsed.get('leagues')
    validated['min_minutes'] = parsed.get('min_minutes', 450)
    validated['similarity_search'] = parsed.get('similarity_search', False)
    validated['n_results'] = parsed.get('n_results', 10)

    # Validate metrics
    requested_metrics = parsed.get('metrics', [])
    if requested_metrics:
        # Use validation service
        validation_result = validate_llm_metric_request(
            requested_metrics,
            position=validated['position'],
            return_suggestions=True
        )

        validated['metrics'] = validation_result['valid']

        # Record warnings
        if validation_result['invalid']:
            warning = f"Invalid metrics rejected: {', '.join(validation_result['invalid'])}"
            validation_warnings.append(warning)

            # Add suggestions
            for invalid, suggestions in validation_result['suggestions'].items():
                if suggestions:
                    validation_warnings.append(
                        f"  Did you mean: {', '.join(suggestions[:3])}?"
                    )

        if validation_result['errors']:
            validation_warnings.extend(validation_result['errors'])
    else:
        validated['metrics'] = []

    # Validate metric groups
    metric_groups = parsed.get('metric_groups', [])
    validated_groups = []
    if metric_groups:
        valid_categories = ['passing', 'shooting', 'defending', 'possession',
                          'discipline', 'physical', 'creative']
        for group in metric_groups:
            if group in valid_categories:
                validated_groups.append(group)
            else:
                validation_warnings.append(f"Unknown metric group: {group}")

    validated['metric_groups'] = validated_groups if validated_groups else None

    # Validate preset profile
    preset = parsed.get('preset_profile')
    if preset:
        # Check if preset exists
        preset_metrics = get_preset_group(preset)
        if preset_metrics:
            validated['preset_profile'] = preset
        else:
            validation_warnings.append(f"Unknown preset profile: {preset}")
            validated['preset_profile'] = None
    else:
        validated['preset_profile'] = None

    # If no metrics specified but metric groups or preset given, expand them
    if not validated['metrics']:
        if validated['metric_groups']:
            # Expand metric groups
            for group in validated['metric_groups']:
                group_metrics = get_metrics_by_category(group)
                validated['metrics'].extend(group_metrics)

        if validated['preset_profile']:
            # Expand preset
            preset_metrics = get_preset_group(validated['preset_profile'])
            if preset_metrics:
                validated['metrics'] = preset_metrics

    # Add validation warnings
    validated['validation_warnings'] = validation_warnings

    # Add metadata
    validated['_parsed_at'] = datetime.now().isoformat()
    validated['_original_query'] = parsed

    return validated


# ============================================================================
# FALLBACK QUERY CONSTRUCTION
# ============================================================================

def build_safe_default_query(position: Optional[str] = None) -> Dict:
    """
    Build a safe default query when parsing fails or is unclear.

    Args:
        position: Optional position filter

    Returns:
        Dict with safe default parameters

    Example:
        >>> default = build_safe_default_query(position="FW")
        >>> print(default['preset_profile'])
        'striker_profile'
    """
    default = {
        'base_player_name': None,
        'position': position,
        'age_min': None,
        'age_max': None,
        'leagues': None,
        'metrics': [],
        'metric_groups': None,
        'preset_profile': None,
        'min_minutes': 450,
        'similarity_search': False,
        'n_results': 10,
        'validation_warnings': ['Using safe defaults - query was unclear']
    }

    # Set appropriate preset based on position
    if position:
        preset_map = {
            'FW': 'striker_profile',
            'ST': 'striker_profile',
            'CF': 'striker_profile',
            'AM': 'creative_midfielder_profile',
            'MF': 'creative_midfielder_profile',
            'DM': 'defensive_midfielder_profile',
            'LW': 'winger_profile',
            'RW': 'winger_profile',
            'DF': 'center_back_profile',
            'CB': 'center_back_profile'
        }

        preset = preset_map.get(position)
        if preset:
            default['preset_profile'] = preset
            default['metrics'] = get_preset_group(preset) or []

    return default


# ============================================================================
# QUERY PARSING WITH FALLBACK
# ============================================================================

def parse_query_with_fallback(
    user_query: str,
    config: Optional[Dict] = None
) -> Dict:
    """
    Parse query with automatic fallback to safe defaults.

    This is the RECOMMENDED function to use in production.
    It never fails - always returns a valid query.

    Args:
        user_query: Natural language query
        config: Optional LLM configuration

    Returns:
        Validated query dict (guaranteed to be valid)

    Example:
        >>> result = parse_query_with_fallback("Find me some strikers")
        >>> # Even if parsing fails, returns valid defaults
    """
    try:
        # Try to parse normally
        return parse_query(user_query, config, strict_validation=False)
    except Exception as e:
        logger.error(f"Query parsing failed: {e}")
        logger.info("Falling back to safe defaults")

        # Extract position if mentioned (simple fallback)
        position = None
        query_lower = user_query.lower()

        position_keywords = {
            'striker': 'FW', 'forward': 'FW', 'attacker': 'FW',
            'midfielder': 'MF', 'midfield': 'MF',
            'defender': 'DF', 'defense': 'DF',
            'winger': 'FW', 'wing': 'FW',
            'goalkeeper': 'GK'
        }

        for keyword, pos in position_keywords.items():
            if keyword in query_lower:
                position = pos
                break

        return build_safe_default_query(position)


# ============================================================================
# QUERY VALIDATION HELPERS
# ============================================================================

def is_similarity_query(user_query: str) -> bool:
    """
    Detect if query is asking for similar players.

    Args:
        user_query: User's query

    Returns:
        True if similarity search is implied

    Example:
        >>> is_similarity_query("Find players like Rodri")
        True
        >>> is_similarity_query("Show me midfielders")
        False
    """
    similarity_keywords = [
        'similar', 'like', 'comparable', 'alternative',
        'replacement', 'instead of', 'style of'
    ]

    query_lower = user_query.lower()
    return any(keyword in query_lower for keyword in similarity_keywords)


def extract_player_name(user_query: str) -> Optional[str]:
    """
    Simple extraction of player name from query.

    This is a basic fallback if LLM fails to extract.

    Args:
        user_query: User's query

    Returns:
        Potential player name or None
    """
    # This is very basic - in production, use NER or LLM parsing
    # Look for capitalized words after "like" or "similar to"
    import re

    patterns = [
        r'like\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'similar to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'instead of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
    ]

    for pattern in patterns:
        match = re.search(pattern, user_query)
        if match:
            return match.group(1)

    return None


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    """
    Example usage of LLM query parsing service.
    """

    print("=" * 80)
    print("LLM SERVICE - QUERY PARSING EXAMPLES")
    print("=" * 80)

    # Example queries
    example_queries = [
        "Find players similar to Rodri but younger",
        "Show me creative midfielders under 23",
        "Who are the best strikers with high goals and assists?",
        "Find defenders in La Liga",
        "Players like Kevin De Bruyne",
        "Young wingers with good dribbling"
    ]

    for i, query in enumerate(example_queries, 1):
        print(f"\n[Example {i}] Query: \"{query}\"")
        print("-" * 40)

        try:
            result = parse_query_with_fallback(query)

            print(f"Base Player: {result.get('base_player_name')}")
            print(f"Position: {result.get('position')}")
            print(f"Age Filter: {result.get('age_min')}-{result.get('age_max')}")
            print(f"Leagues: {result.get('leagues')}")
            print(f"Preset Profile: {result.get('preset_profile')}")
            print(f"Metrics: {result.get('metrics', [])[:5]}...")  # First 5
            print(f"Similarity Search: {result.get('similarity_search')}")

            if result.get('validation_warnings'):
                print(f"\nWarnings:")
                for warning in result['validation_warnings']:
                    print(f"  - {warning}")

        except Exception as e:
            print(f"ERROR: {e}")

    print("\n" + "=" * 80)
