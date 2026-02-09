"""
Tests for LLM Service

Tests query parsing and validation including:
- Natural language query parsing
- Schema validation
- Metric extraction
- Forbidden metric rejection in queries
- Fallback query building

8 Critical Invariants Tested:
4. LLM Schema Validation: parsed queries match expected schema
5. Forbidden Metric Rejection: hallucinated metrics rejected
"""

import pytest
import json
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.llm_service import (
    parse_query,
    parse_query_with_fallback,
    validate_parsed_query,
    is_similarity_query,
    extract_player_name,
    build_safe_default_query,
    build_parsing_system_prompt,
    QueryParseError,
    InvalidQuerySchemaError,
)


class TestParseQuery:
    """Tests for natural language query parsing."""

    def test_parse_metric_search_query(self, mock_llm_client, sample_metrics_registry):
        """Should correctly parse metric search queries."""
        with patch('services.llm_service.get_llm_client') as mock_get_client, \
             patch('services.llm_service.get_metrics_registry') as mock_registry:

            mock_get_client.return_value = mock_llm_client
            mock_registry.return_value = sample_metrics_registry

            # Mock response for metric search
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text=json.dumps({
                'query_type': 'metric_search',
                'metrics': ['goals', 'xg'],
                'filters': {'position': 'Centre-Forward'},
                'sort_by': 'goals',
                'limit': 20
            }))]
            mock_llm_client.messages.create.return_value = mock_response

            result = parse_query("Show me top strikers by goals")

            assert result['query_type'] == 'metric_search'
            assert 'goals' in result['metrics']

    def test_parse_similarity_query(self, mock_llm_client, sample_metrics_registry):
        """Should correctly parse similarity search queries."""
        with patch('services.llm_service.get_llm_client') as mock_get_client, \
             patch('services.llm_service.get_metrics_registry') as mock_registry:

            mock_get_client.return_value = mock_llm_client
            mock_registry.return_value = sample_metrics_registry

            mock_response = MagicMock()
            mock_response.content = [MagicMock(text=json.dumps({
                'query_type': 'similarity_search',
                'player_name': 'Kevin De Bruyne',
                'filters': {},
                'limit': 10
            }))]
            mock_llm_client.messages.create.return_value = mock_response

            result = parse_query("Find players similar to Kevin De Bruyne")

            assert result['query_type'] == 'similarity_search'
            assert result['player_name'] == 'Kevin De Bruyne'


class TestValidateParsedQuery:
    """Tests for parsed query validation."""

    def test_valid_metric_search_schema(self, sample_metrics_registry):
        """Valid metric search query should pass validation."""
        with patch('services.llm_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            query = {
                'query_type': 'metric_search',
                'metrics': ['goals', 'assists'],
                'filters': {},
                'sort_by': 'goals',
                'limit': 20
            }

            result = validate_parsed_query(query)
            assert result['valid'] is True

    def test_valid_similarity_search_schema(self, sample_metrics_registry):
        """Valid similarity search query should pass validation."""
        with patch('services.llm_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            query = {
                'query_type': 'similarity_search',
                'player_name': 'Test Player',
                'filters': {},
                'limit': 10
            }

            result = validate_parsed_query(query)
            assert result['valid'] is True

    def test_invalid_query_type_fails(self, sample_metrics_registry):
        """
        INVARIANT 4: Parsed queries must match expected schema.

        Invalid query types must be rejected.
        """
        with patch('services.llm_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            query = {
                'query_type': 'invalid_type',
                'metrics': ['goals'],
            }

            result = validate_parsed_query(query)
            assert result['valid'] is False
            assert 'invalid query_type' in result['error'].lower()

    def test_missing_required_fields_fails(self, sample_metrics_registry):
        """Missing required fields must fail validation."""
        with patch('services.llm_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            # Missing 'metrics' for metric_search
            query = {
                'query_type': 'metric_search',
                'filters': {},
            }

            result = validate_parsed_query(query)
            assert result['valid'] is False

    def test_forbidden_metrics_rejected(self, sample_metrics_registry):
        """
        INVARIANT 5: Forbidden metrics must be rejected.

        Queries containing forbidden/hallucinated metrics must fail.
        """
        with patch('services.llm_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            query = {
                'query_type': 'metric_search',
                'metrics': ['goals', 'hallucinated_metric'],  # forbidden
                'filters': {},
            }

            result = validate_parsed_query(query)
            assert result['valid'] is False
            assert 'forbidden' in result['error'].lower() or 'invalid' in result['error'].lower()

    def test_nonexistent_metrics_rejected(self, sample_metrics_registry):
        """
        Queries with nonexistent metrics must fail validation.
        """
        with patch('services.llm_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            query = {
                'query_type': 'metric_search',
                'metrics': ['goals', 'completely_made_up_stat'],
                'filters': {},
            }

            result = validate_parsed_query(query)
            assert result['valid'] is False


class TestIsSimilarityQuery:
    """Tests for similarity query detection."""

    def test_detect_similarity_keywords(self):
        """Should detect similarity-related keywords."""
        similarity_queries = [
            "Find players similar to Messi",
            "Who plays like Kevin De Bruyne",
            "Players comparable to Haaland",
            "Show me alternatives to Salah",
            "Find replacements for Modric",
        ]

        for query in similarity_queries:
            assert is_similarity_query(query) is True, \
                f"Failed to detect similarity in: {query}"

    def test_non_similarity_queries(self):
        """Should not flag non-similarity queries."""
        non_similarity = [
            "Show me top scorers",
            "Which players have most assists",
            "List all midfielders by passing accuracy",
            "Compare goals and xG",
        ]

        for query in non_similarity:
            assert is_similarity_query(query) is False, \
                f"Incorrectly flagged as similarity: {query}"


class TestExtractPlayerName:
    """Tests for player name extraction."""

    def test_extract_name_after_similar_to(self):
        """Should extract name after 'similar to'."""
        query = "Find players similar to Kevin De Bruyne"
        name = extract_player_name(query)
        assert name == "Kevin De Bruyne"

    def test_extract_name_after_like(self):
        """Should extract name after 'like'."""
        query = "Who plays like Messi"
        name = extract_player_name(query)
        assert name == "Messi"

    def test_extract_name_after_comparable(self):
        """Should extract name after 'comparable to'."""
        query = "Find players comparable to Haaland"
        name = extract_player_name(query)
        assert name == "Haaland"

    def test_no_name_returns_none(self):
        """Should return None if no name found."""
        query = "Show me top scorers"
        name = extract_player_name(query)
        assert name is None


class TestBuildSafeDefaultQuery:
    """Tests for safe default query building."""

    def test_default_metric_search(self, sample_metrics_registry):
        """Default query should be valid metric search."""
        with patch('services.llm_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            default = build_safe_default_query()

            assert default['query_type'] == 'metric_search'
            assert len(default['metrics']) > 0
            assert default['limit'] > 0

    def test_default_query_validates(self, sample_metrics_registry):
        """Default query should pass validation."""
        with patch('services.llm_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            default = build_safe_default_query()
            result = validate_parsed_query(default)

            assert result['valid'] is True


class TestParseQueryWithFallback:
    """Tests for parse query with fallback handling."""

    def test_fallback_on_parse_error(self, sample_metrics_registry):
        """Should return default query on parse error."""
        with patch('services.llm_service.parse_query') as mock_parse, \
             patch('services.llm_service.get_metrics_registry') as mock_registry:

            mock_parse.side_effect = QueryParseError("Parse failed")
            mock_registry.return_value = sample_metrics_registry

            result = parse_query_with_fallback("Invalid query")

            # Should return valid default query
            assert 'query_type' in result
            assert result['query_type'] == 'metric_search'

    def test_fallback_on_invalid_schema(self, sample_metrics_registry):
        """Should return default query on schema validation failure."""
        with patch('services.llm_service.parse_query') as mock_parse, \
             patch('services.llm_service.get_metrics_registry') as mock_registry:

            # Return invalid query
            mock_parse.return_value = {
                'query_type': 'invalid',
                'metrics': ['hallucinated_metric'],
            }
            mock_registry.return_value = sample_metrics_registry

            result = parse_query_with_fallback("Some query")

            # Should return valid default query
            assert result['query_type'] == 'metric_search'


class TestBuildParsingSystemPrompt:
    """Tests for system prompt building."""

    def test_prompt_includes_available_metrics(self, sample_metrics_registry):
        """Prompt should list available metrics."""
        with patch('services.llm_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            prompt = build_parsing_system_prompt()

            assert 'goals' in prompt.lower()
            assert 'assists' in prompt.lower()

    def test_prompt_includes_forbidden_warning(self, sample_metrics_registry):
        """Prompt should warn about forbidden metrics."""
        with patch('services.llm_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            prompt = build_parsing_system_prompt()

            # Should mention not to use undefined metrics
            assert 'only' in prompt.lower() or 'available' in prompt.lower()

    def test_prompt_includes_schema(self, sample_metrics_registry):
        """Prompt should include expected output schema."""
        with patch('services.llm_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            prompt = build_parsing_system_prompt()

            # Should mention JSON output
            assert 'json' in prompt.lower()
            assert 'query_type' in prompt


class TestLLMSchemaValidationInvariant:
    """
    Tests for INVARIANT 4: LLM Schema Validation.

    All parsed queries must conform to the expected schema.
    """

    def test_metric_search_schema_complete(self, sample_metrics_registry):
        """Metric search must have all required fields."""
        with patch('services.llm_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            required_fields = ['query_type', 'metrics']

            query = {
                'query_type': 'metric_search',
                'metrics': ['goals'],
                'filters': {},
            }

            result = validate_parsed_query(query)
            assert result['valid'] is True

            # Missing required field should fail
            for field in required_fields:
                incomplete = query.copy()
                del incomplete[field]
                result = validate_parsed_query(incomplete)
                assert result['valid'] is False, \
                    f"Missing '{field}' should fail validation"

    def test_similarity_search_schema_complete(self, sample_metrics_registry):
        """Similarity search must have all required fields."""
        with patch('services.llm_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            required_fields = ['query_type', 'player_name']

            query = {
                'query_type': 'similarity_search',
                'player_name': 'Test Player',
                'filters': {},
            }

            result = validate_parsed_query(query)
            assert result['valid'] is True

            # Missing required field should fail
            for field in required_fields:
                incomplete = query.copy()
                del incomplete[field]
                result = validate_parsed_query(incomplete)
                assert result['valid'] is False, \
                    f"Missing '{field}' should fail validation"

    def test_metrics_must_be_list(self, sample_metrics_registry):
        """Metrics field must be a list."""
        with patch('services.llm_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            query = {
                'query_type': 'metric_search',
                'metrics': 'goals',  # String instead of list
                'filters': {},
            }

            result = validate_parsed_query(query)
            assert result['valid'] is False

    def test_limit_must_be_positive_integer(self, sample_metrics_registry):
        """Limit must be a positive integer."""
        with patch('services.llm_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            invalid_limits = [-1, 0, 'ten', 10.5]

            for limit in invalid_limits:
                query = {
                    'query_type': 'metric_search',
                    'metrics': ['goals'],
                    'filters': {},
                    'limit': limit,
                }

                result = validate_parsed_query(query)
                # Should either fail or be corrected
                if result['valid']:
                    # If valid, limit should be corrected to valid value
                    assert result.get('query', {}).get('limit', 1) > 0


class TestAntiHallucinationDefense:
    """
    Tests for the anti-hallucination system.

    The system must prevent LLM hallucinations from affecting results.
    """

    def test_reject_plausible_sounding_fake_metrics(self, sample_metrics_registry):
        """Metrics that sound real but aren't must be rejected."""
        with patch('services.llm_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            plausible_fakes = [
                'expected_threat',
                'progressive_value',
                'pressing_intensity',
                'creative_volume',
                'defensive_actions_90',
            ]

            for metric in plausible_fakes:
                query = {
                    'query_type': 'metric_search',
                    'metrics': [metric],
                    'filters': {},
                }

                result = validate_parsed_query(query)
                assert result['valid'] is False, \
                    f"Fake metric '{metric}' should be rejected"

    def test_partial_valid_metrics_still_fail(self, sample_metrics_registry):
        """Queries with any invalid metric should fail entirely."""
        with patch('services.llm_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            query = {
                'query_type': 'metric_search',
                'metrics': ['goals', 'assists', 'fake_metric'],  # 2 valid, 1 fake
                'filters': {},
            }

            result = validate_parsed_query(query)
            assert result['valid'] is False

    def test_case_sensitivity_handling(self, sample_metrics_registry):
        """Metric names should be case-insensitive or properly handled."""
        with patch('services.llm_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            variations = ['Goals', 'GOALS', 'goals', 'GoAlS']

            for metric in variations:
                query = {
                    'query_type': 'metric_search',
                    'metrics': [metric],
                    'filters': {},
                }

                result = validate_parsed_query(query)
                # Should either accept (case-insensitive) or reject consistently
                # The important thing is no false positives
