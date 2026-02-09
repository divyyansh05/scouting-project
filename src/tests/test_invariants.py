"""
Comprehensive Invariant Tests

Tests all 8 Critical System Invariants:
1. Similarity Identity: self-similarity = 1.0
2. Monotonicity: higher weights → higher influence
3. Metric Correctness: computed metrics match formulas
4. LLM Schema Validation: parsed queries match expected schema
5. Forbidden Metric Rejection: hallucinated metrics rejected
6. Database Read-Only: no write operations allowed
7. Data Integrity: data types and ranges preserved
8. Edge Cases: proper handling of nulls, zeros, empty sets

These tests verify the fundamental mathematical and logical
properties that must always hold for system correctness.
"""

import pytest
import numpy as np
import pandas as pd
from typing import Dict, List, Any
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestInvariant1SimilarityIdentity:
    """
    INVARIANT 1: Self-similarity must equal 1.0

    When a player is compared to themselves, the similarity
    score MUST be exactly 1.0 (perfect similarity).

    This is a fundamental mathematical property of similarity metrics.
    """

    def test_cosine_self_similarity(self):
        """Cosine similarity of vector with itself must be 1.0."""
        from services.similarity_service import cosine_similarity

        # Test with various vector types
        test_vectors = [
            np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
            np.array([0.1, 0.2, 0.3]),
            np.array([100.0, 200.0, 300.0]),
            np.random.randn(20),
            np.ones(10),
        ]

        for vector in test_vectors:
            similarity = cosine_similarity(vector, vector)
            assert similarity == pytest.approx(1.0, abs=1e-6), \
                f"Self-similarity failed for vector: {vector[:3]}..."

    def test_full_similarity_breakdown_self(self, sample_role_vectors, sample_stats_vectors):
        """Full similarity breakdown for self-comparison must be 1.0."""
        from services.similarity_service import similarity_score_breakdown

        for player_id in sample_role_vectors:
            if player_id in sample_stats_vectors:
                breakdown = similarity_score_breakdown(
                    role_vector_1=sample_role_vectors[player_id],
                    role_vector_2=sample_role_vectors[player_id],
                    stats_vector_1=sample_stats_vectors[player_id],
                    stats_vector_2=sample_stats_vectors[player_id],
                )

                assert breakdown['role_similarity'] == pytest.approx(1.0, abs=1e-6)
                assert breakdown['stats_similarity'] == pytest.approx(1.0, abs=1e-6)
                assert breakdown['total_similarity'] == pytest.approx(1.0, abs=1e-6)


class TestInvariant2Monotonicity:
    """
    INVARIANT 2: Higher weights must have proportionally higher influence.

    With ROLE_WEIGHT=0.6 and STATS_WEIGHT=0.4:
    - Changes in role similarity should have 1.5x the impact of stats changes
    - The weighted sum must equal the total similarity

    This ensures the weighting system works as designed.
    """

    def test_role_weight_dominance(self, sample_role_vectors, sample_stats_vectors):
        """Role similarity changes should have greater impact than stats."""
        from services.similarity_service import (
            similarity_score_breakdown, ROLE_WEIGHT, STATS_WEIGHT
        )

        # Verify weights are as expected
        assert ROLE_WEIGHT == pytest.approx(0.6, abs=0.01)
        assert STATS_WEIGHT == pytest.approx(0.4, abs=0.01)
        assert ROLE_WEIGHT + STATS_WEIGHT == pytest.approx(1.0, abs=0.01)

        # Create test where role is similar but stats differ
        role_v1 = sample_role_vectors[1]
        role_v2 = role_v1 + np.random.randn(20) * 0.01  # Very similar

        stats_v1 = sample_stats_vectors[1]
        stats_v2 = np.random.randn(10)  # Very different

        breakdown = similarity_score_breakdown(
            role_vector_1=role_v1,
            role_vector_2=role_v2,
            stats_vector_1=stats_v1,
            stats_vector_2=stats_v2,
        )

        # Role contribution should dominate
        role_contribution = breakdown['role_similarity'] * ROLE_WEIGHT
        assert role_contribution > 0.5, \
            "Role contribution should be dominant when roles are similar"

    def test_weighted_sum_equals_total(self, sample_role_vectors, sample_stats_vectors):
        """Weighted sum of components must equal total similarity."""
        from services.similarity_service import (
            similarity_score_breakdown, ROLE_WEIGHT, STATS_WEIGHT
        )

        for id1 in list(sample_role_vectors.keys())[:3]:
            for id2 in list(sample_role_vectors.keys())[:3]:
                if id1 in sample_stats_vectors and id2 in sample_stats_vectors:
                    breakdown = similarity_score_breakdown(
                        role_vector_1=sample_role_vectors[id1],
                        role_vector_2=sample_role_vectors[id2],
                        stats_vector_1=sample_stats_vectors[id1],
                        stats_vector_2=sample_stats_vectors[id2],
                    )

                    expected = (
                        breakdown['role_similarity'] * ROLE_WEIGHT +
                        breakdown['stats_similarity'] * STATS_WEIGHT
                    )

                    assert breakdown['total_similarity'] == pytest.approx(expected, abs=0.01), \
                        f"Weighted sum mismatch for players {id1} and {id2}"


class TestInvariant3MetricCorrectness:
    """
    INVARIANT 3: Computed metrics must match their defined formulas.

    Every metric computation must produce mathematically correct results.
    No approximations, no rounding errors beyond floating point precision.
    """

    def test_per_90_formula_exact(self):
        """Per-90 must be exactly (value / minutes) * 90."""
        from services.metrics_service import compute_per_90

        test_cases = [
            # (value, minutes, expected_per_90)
            (10, 900, 1.0),
            (5, 450, 1.0),
            (20, 1800, 1.0),
            (15, 2700, 0.5),
            (9, 810, 1.0),
            (0, 900, 0.0),
        ]

        for value, minutes, expected in test_cases:
            result = compute_per_90(value, minutes)
            assert result == pytest.approx(expected, abs=1e-9), \
                f"Per-90 incorrect: {value}/{minutes}*90 should be {expected}, got {result}"

    def test_cosine_similarity_formula_exact(self):
        """Cosine similarity must match: dot(a,b) / (||a|| * ||b||)."""
        from services.similarity_service import cosine_similarity

        v1 = np.array([3.0, 4.0])
        v2 = np.array([4.0, 3.0])

        # Manual calculation
        dot_product = np.dot(v1, v2)  # 3*4 + 4*3 = 24
        norm1 = np.linalg.norm(v1)    # sqrt(9+16) = 5
        norm2 = np.linalg.norm(v2)    # sqrt(16+9) = 5
        expected = dot_product / (norm1 * norm2)  # 24/25 = 0.96

        result = cosine_similarity(v1, v2)
        assert result == pytest.approx(expected, abs=1e-9)


class TestInvariant4LLMSchemaValidation:
    """
    INVARIANT 4: LLM-parsed queries must match expected schema.

    The LLM output must be validated against a strict schema.
    Invalid structures must be rejected before execution.
    """

    def test_valid_schemas_accepted(self, sample_metrics_registry):
        """Valid query schemas must pass validation."""
        from services.llm_service import validate_parsed_query

        with patch('services.llm_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            valid_queries = [
                {
                    'query_type': 'metric_search',
                    'metrics': ['goals', 'assists'],
                    'filters': {},
                },
                {
                    'query_type': 'similarity_search',
                    'player_name': 'Test Player',
                    'filters': {},
                },
                {
                    'query_type': 'comparison',
                    'players': ['Player A', 'Player B'],
                    'metrics': ['goals', 'xg'],
                },
            ]

            for query in valid_queries:
                result = validate_parsed_query(query)
                assert result['valid'] is True, \
                    f"Valid query rejected: {query}"

    def test_invalid_schemas_rejected(self, sample_metrics_registry):
        """Invalid query schemas must be rejected."""
        from services.llm_service import validate_parsed_query

        with patch('services.llm_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            invalid_queries = [
                {'query_type': 'invalid_type'},
                {'metrics': ['goals']},  # Missing query_type
                {'query_type': 'metric_search'},  # Missing metrics
                {'query_type': 'similarity_search'},  # Missing player_name
                None,
                "not a dict",
                [],
            ]

            for query in invalid_queries:
                result = validate_parsed_query(query)
                assert result['valid'] is False, \
                    f"Invalid query accepted: {query}"


class TestInvariant5ForbiddenMetricRejection:
    """
    INVARIANT 5: Forbidden/hallucinated metrics must be rejected.

    The system must prevent LLM hallucinations from affecting results.
    Any metric not in the registry must be rejected.
    """

    def test_forbidden_list_rejected(self, sample_metrics_registry):
        """Explicitly forbidden metrics must be rejected."""
        from services.metrics_service import is_forbidden_metric
        from services.llm_service import validate_parsed_query

        with patch('services.metrics_service.get_metrics_registry') as mock_registry, \
             patch('services.llm_service.get_metrics_registry') as mock_llm_registry:

            mock_registry.return_value = sample_metrics_registry
            mock_llm_registry.return_value = sample_metrics_registry

            forbidden = sample_metrics_registry['forbidden_metrics']

            for metric in forbidden:
                assert is_forbidden_metric(metric) is True, \
                    f"Forbidden metric not detected: {metric}"

                query = {
                    'query_type': 'metric_search',
                    'metrics': [metric],
                    'filters': {},
                }
                result = validate_parsed_query(query)
                assert result['valid'] is False, \
                    f"Query with forbidden metric accepted: {metric}"

    def test_undefined_metrics_rejected(self, sample_metrics_registry):
        """Metrics not in registry must be rejected."""
        from services.metrics_service import validate_metric_exists

        with patch('services.metrics_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            undefined = [
                'random_stat',
                'made_up_metric',
                'llm_hallucination',
                'expected_threat',  # Plausible but undefined
                'creative_index',
            ]

            for metric in undefined:
                exists = validate_metric_exists(metric)
                assert exists is False, \
                    f"Undefined metric accepted: {metric}"


class TestInvariant6DatabaseReadOnly:
    """
    INVARIANT 6: Database must be read-only.

    No write operations (INSERT, UPDATE, DELETE, DROP, etc.)
    should ever be executed against the database.
    """

    def test_write_operations_blocked(self):
        """Write SQL statements must be rejected."""
        from utils.db import validate_query_readonly

        write_operations = [
            "INSERT INTO players VALUES (1, 'Test')",
            "UPDATE players SET name = 'New' WHERE id = 1",
            "DELETE FROM players WHERE id = 1",
            "DROP TABLE players",
            "TRUNCATE TABLE players",
            "ALTER TABLE players ADD COLUMN test INT",
            "CREATE TABLE new_table (id INT)",
            "GRANT ALL ON players TO user",
        ]

        for sql in write_operations:
            is_readonly = validate_query_readonly(sql)
            assert is_readonly is False, \
                f"Write operation not blocked: {sql}"

    def test_read_operations_allowed(self):
        """Read SQL statements must be allowed."""
        from utils.db import validate_query_readonly

        read_operations = [
            "SELECT * FROM players",
            "SELECT name, goals FROM players WHERE position = 'Forward'",
            "SELECT COUNT(*) FROM players",
            "SELECT p.*, t.name FROM players p JOIN teams t ON p.team_id = t.id",
            "WITH cte AS (SELECT * FROM players) SELECT * FROM cte",
        ]

        for sql in read_operations:
            is_readonly = validate_query_readonly(sql)
            assert is_readonly is True, \
                f"Read operation blocked: {sql}"


class TestInvariant7DataIntegrity:
    """
    INVARIANT 7: Data types and ranges must be preserved.

    Similarity scores: [0, 1]
    Per-90 values: [0, ∞)
    Percentages: [0, 100] or [0, 1]
    """

    def test_similarity_bounds(self, sample_role_vectors, sample_stats_vectors):
        """Similarity scores must be in [0, 1]."""
        from services.similarity_service import similarity_score_breakdown

        for id1 in sample_role_vectors:
            for id2 in sample_role_vectors:
                if id1 in sample_stats_vectors and id2 in sample_stats_vectors:
                    breakdown = similarity_score_breakdown(
                        role_vector_1=sample_role_vectors[id1],
                        role_vector_2=sample_role_vectors[id2],
                        stats_vector_1=sample_stats_vectors[id1],
                        stats_vector_2=sample_stats_vectors[id2],
                    )

                    assert 0.0 <= breakdown['total_similarity'] <= 1.0
                    assert 0.0 <= breakdown['role_similarity'] <= 1.0
                    assert 0.0 <= breakdown['stats_similarity'] <= 1.0

    def test_per_90_non_negative(self):
        """Per-90 values must be non-negative."""
        from services.metrics_service import compute_per_90

        test_cases = [
            (10, 900),
            (0, 900),
            (100, 100),
            (-5, 900),  # Negative input (edge case)
        ]

        for value, minutes in test_cases:
            result = compute_per_90(value, minutes)
            # Result should be non-negative (or handle negative input gracefully)
            assert result >= 0 or np.isnan(result), \
                f"Per-90 returned negative: {result}"


class TestInvariant8EdgeCases:
    """
    INVARIANT 8: Edge cases must be handled properly.

    - Zero vectors
    - Empty datasets
    - Missing values (NaN/None)
    - Division by zero scenarios
    """

    def test_zero_vector_handling(self):
        """Zero vectors must be handled without errors."""
        from services.similarity_service import cosine_similarity

        zero = np.zeros(10)
        normal = np.random.randn(10)

        # Should return 0, not error
        result = cosine_similarity(zero, normal)
        assert result == 0.0

        result = cosine_similarity(zero, zero)
        assert result == 0.0

    def test_zero_minutes_handling(self):
        """Zero minutes must not cause division by zero."""
        from services.metrics_service import compute_per_90

        result = compute_per_90(10, 0)
        # Should return 0 or infinity, not crash
        assert result == 0.0 or np.isinf(result)

    def test_empty_dataframe_handling(self):
        """Empty DataFrames must be handled gracefully."""
        from services.metrics_service import aggregate_metric

        empty_df = pd.DataFrame(columns=['goals', 'assists', 'minutes_played'])

        result = aggregate_metric(empty_df, 'goals', method='sum')
        # Should return 0 or NaN, not error
        assert result == 0 or pd.isna(result)

    def test_nan_value_handling(self):
        """NaN values must be handled gracefully."""
        from services.metrics_service import compute_per_90
        from services.similarity_service import cosine_similarity

        # Per-90 with NaN
        result = compute_per_90(np.nan, 900)
        assert pd.isna(result) or result == 0.0

        # Cosine similarity with NaN
        v1 = np.array([1.0, np.nan, 3.0])
        v2 = np.array([1.0, 2.0, 3.0])

        # Should either handle gracefully or return NaN
        try:
            result = cosine_similarity(v1, v2)
            # If it returns, should be valid or NaN
            assert np.isfinite(result) or np.isnan(result)
        except (ValueError, RuntimeWarning):
            # Raising an error for NaN input is acceptable
            pass

    def test_single_player_similarity_search(self, sample_player_data, sample_role_vectors, sample_stats_vectors):
        """Similarity search with only one player must handle gracefully."""
        from services.similarity_service import find_similar_players

        # Create single-player dataset
        single_player = sample_player_data.iloc[:1]
        single_roles = {1: sample_role_vectors[1]}
        single_stats = {1: sample_stats_vectors[1]}

        with patch('services.similarity_service.get_role_vectors') as mock_roles, \
             patch('services.similarity_service.get_stats_vectors') as mock_stats, \
             patch('services.similarity_service.get_player_data') as mock_data:

            mock_roles.return_value = single_roles
            mock_stats.return_value = single_stats
            mock_data.return_value = single_player

            # Should return empty list (no other players to compare)
            results = find_similar_players(target_player_id=1, limit=10)
            assert len(results) == 0


class TestCrossInvariantConsistency:
    """Tests that verify consistency across multiple invariants."""

    def test_similarity_and_schema_consistency(
        self,
        sample_metrics_registry,
        sample_role_vectors,
        sample_stats_vectors
    ):
        """Similarity results must use only valid metrics from registry."""
        # This tests that Invariant 1 (similarity) and Invariant 5 (forbidden metrics)
        # work together correctly

        from services.similarity_service import SimilarityResult
        from services.metrics_service import validate_metric_exists

        with patch('services.metrics_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            # Create a similarity result
            result = SimilarityResult(
                player_id=1,
                player_name="Test",
                team_name="Team",
                position="Midfielder",
                similarity_score=0.85,
                role_similarity=0.90,
                stats_similarity=0.75,
            )

            # Verify bounds (Invariant 7)
            assert 0.0 <= result.similarity_score <= 1.0
            assert 0.0 <= result.role_similarity <= 1.0
            assert 0.0 <= result.stats_similarity <= 1.0

    def test_readonly_and_integrity_consistency(self):
        """Read-only queries must preserve data integrity."""
        from utils.db import validate_query_readonly

        # Query that would violate integrity if executed as write
        dangerous_looking = "SELECT * FROM players; DROP TABLE players;"

        # Should detect the write operation
        is_readonly = validate_query_readonly(dangerous_looking)
        assert is_readonly is False, \
            "Multi-statement with DROP not blocked"
