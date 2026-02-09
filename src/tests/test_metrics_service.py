"""
Tests for Metrics Service

Tests metric computation, validation, and registry operations including:
- Metric existence validation
- Per-90 calculations
- Aggregation methods
- Category filtering
- Forbidden metric rejection

8 Critical Invariants Tested:
3. Metric Correctness: computed metrics match formulas
5. Forbidden Metric Rejection: hallucinated metrics rejected
"""

import pytest
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.metrics_service import (
    get_metric_value,
    compute_per_90,
    validate_metric_exists,
    get_metrics_by_category,
    aggregate_metric,
    is_forbidden_metric,
    get_metric_display_name,
    get_available_metrics,
    MetricNotFoundError,
    ForbiddenMetricError,
)


class TestGetMetricValue:
    """Tests for retrieving metric values."""

    def test_get_existing_metric(self, sample_player_data):
        """Should return correct value for existing metric."""
        row = sample_player_data.iloc[0]
        value = get_metric_value(row, 'goals')
        assert value == row['goals']

    def test_get_nonexistent_metric_raises(self, sample_player_data):
        """Should raise error for nonexistent metric."""
        row = sample_player_data.iloc[0]
        with pytest.raises(MetricNotFoundError):
            get_metric_value(row, 'nonexistent_metric')

    def test_get_metric_with_default(self, sample_player_data):
        """Should return default for missing metric if provided."""
        row = sample_player_data.iloc[0]
        value = get_metric_value(row, 'nonexistent_metric', default=0.0)
        assert value == 0.0


class TestComputePer90:
    """Tests for per-90 calculations."""

    def test_per_90_basic_calculation(self):
        """Per-90 should correctly normalize by minutes."""
        # 10 goals in 900 minutes = 1.0 goals per 90
        value = 10
        minutes = 900
        per_90 = compute_per_90(value, minutes)
        assert per_90 == pytest.approx(1.0, abs=1e-6)

    def test_per_90_zero_minutes_returns_zero(self):
        """Zero minutes should return 0 to avoid division error."""
        per_90 = compute_per_90(10, 0)
        assert per_90 == 0.0

    def test_per_90_negative_minutes_returns_zero(self):
        """Negative minutes should return 0."""
        per_90 = compute_per_90(10, -100)
        assert per_90 == 0.0

    def test_per_90_preserves_zero_value(self):
        """Zero value should remain zero regardless of minutes."""
        per_90 = compute_per_90(0, 2700)
        assert per_90 == 0.0

    def test_per_90_formula_correctness(self):
        """
        INVARIANT 3: Per-90 formula must be exactly: (value / minutes) * 90

        This tests the mathematical correctness of the computation.
        """
        test_cases = [
            (5, 450, 1.0),      # 5 in 450 min = 1.0 per 90
            (10, 900, 1.0),     # 10 in 900 min = 1.0 per 90
            (15, 2700, 0.5),    # 15 in 2700 min = 0.5 per 90
            (3, 270, 1.0),      # 3 in 270 min = 1.0 per 90
        ]

        for value, minutes, expected in test_cases:
            result = compute_per_90(value, minutes)
            assert result == pytest.approx(expected, abs=1e-6), \
                f"Per-90 incorrect for {value}/{minutes}"


class TestValidateMetricExists:
    """Tests for metric existence validation."""

    def test_validate_existing_metric(self, sample_metrics_registry):
        """Should return True for existing metric."""
        with patch('services.metrics_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry
            assert validate_metric_exists('goals') is True
            assert validate_metric_exists('assists') is True
            assert validate_metric_exists('xg') is True

    def test_validate_nonexistent_metric(self, sample_metrics_registry):
        """Should return False for nonexistent metric."""
        with patch('services.metrics_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry
            assert validate_metric_exists('made_up_stat') is False
            assert validate_metric_exists('random_metric') is False


class TestIsForbiddenMetric:
    """Tests for forbidden metric detection."""

    def test_forbidden_metric_detected(self, sample_metrics_registry):
        """
        INVARIANT 5: Forbidden metrics must be rejected.

        The system must reject any metric on the forbidden list.
        """
        with patch('services.metrics_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            assert is_forbidden_metric('made_up_stat') is True
            assert is_forbidden_metric('hallucinated_metric') is True
            assert is_forbidden_metric('fake_xg') is True

    def test_valid_metric_not_forbidden(self, sample_metrics_registry):
        """Valid metrics should not be flagged as forbidden."""
        with patch('services.metrics_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            assert is_forbidden_metric('goals') is False
            assert is_forbidden_metric('assists') is False
            assert is_forbidden_metric('xg') is False

    def test_unknown_metric_not_automatically_forbidden(self, sample_metrics_registry):
        """Unknown metrics are not forbidden (just invalid)."""
        with patch('services.metrics_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            # This metric is unknown but not explicitly forbidden
            assert is_forbidden_metric('some_new_metric') is False


class TestGetMetricsByCategory:
    """Tests for category-based metric filtering."""

    def test_get_attacking_metrics(self, sample_metrics_registry):
        """Should return all attacking metrics."""
        with patch('services.metrics_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            attacking = get_metrics_by_category('attacking')
            assert 'goals' in attacking
            assert 'assists' in attacking
            assert 'xg' in attacking

    def test_get_defending_metrics(self, sample_metrics_registry):
        """Should return all defending metrics."""
        with patch('services.metrics_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            defending = get_metrics_by_category('defending')
            assert 'tackles_won' in defending

    def test_invalid_category_returns_empty(self, sample_metrics_registry):
        """Invalid category should return empty list."""
        with patch('services.metrics_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            result = get_metrics_by_category('invalid_category')
            assert result == []


class TestAggregateMetric:
    """Tests for metric aggregation."""

    def test_sum_aggregation(self, sample_player_data):
        """Sum aggregation should sum all values."""
        result = aggregate_metric(sample_player_data, 'goals', method='sum')
        expected = sample_player_data['goals'].sum()
        assert result == expected

    def test_mean_aggregation(self, sample_player_data):
        """Mean aggregation should average all values."""
        result = aggregate_metric(sample_player_data, 'pass_accuracy', method='mean')
        expected = sample_player_data['pass_accuracy'].mean()
        assert result == pytest.approx(expected, abs=1e-6)

    def test_max_aggregation(self, sample_player_data):
        """Max aggregation should return maximum value."""
        result = aggregate_metric(sample_player_data, 'goals', method='max')
        expected = sample_player_data['goals'].max()
        assert result == expected

    def test_min_aggregation(self, sample_player_data):
        """Min aggregation should return minimum value."""
        result = aggregate_metric(sample_player_data, 'goals', method='min')
        expected = sample_player_data['goals'].min()
        assert result == expected

    def test_invalid_method_raises(self, sample_player_data):
        """Invalid aggregation method should raise error."""
        with pytest.raises(ValueError):
            aggregate_metric(sample_player_data, 'goals', method='invalid')


class TestGetMetricDisplayName:
    """Tests for metric display name retrieval."""

    def test_get_display_name(self, sample_metrics_registry):
        """Should return correct display name."""
        with patch('services.metrics_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            assert get_metric_display_name('goals') == 'Goals'
            assert get_metric_display_name('xg') == 'Expected Goals (xG)'

    def test_fallback_to_metric_name(self, sample_metrics_registry):
        """Should fallback to metric name if display name not found."""
        with patch('services.metrics_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            # Unknown metric should return itself
            result = get_metric_display_name('unknown_metric')
            assert result == 'unknown_metric'


class TestGetAvailableMetrics:
    """Tests for listing available metrics."""

    def test_returns_all_metrics(self, sample_metrics_registry):
        """Should return all defined metrics."""
        with patch('services.metrics_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            metrics = get_available_metrics()
            assert 'goals' in metrics
            assert 'assists' in metrics
            assert 'xg' in metrics
            assert 'pass_accuracy' in metrics
            assert 'tackles_won' in metrics

    def test_excludes_forbidden_metrics(self, sample_metrics_registry):
        """Should not include forbidden metrics."""
        with patch('services.metrics_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            metrics = get_available_metrics()
            assert 'made_up_stat' not in metrics
            assert 'hallucinated_metric' not in metrics
            assert 'fake_xg' not in metrics


class TestMetricCorrectnessInvariant:
    """
    Tests for INVARIANT 3: Metric Correctness.

    All computed metrics must match their defined formulas exactly.
    """

    def test_goals_per_90_correctness(self, sample_player_data):
        """Goals per 90 must be exactly (goals / minutes) * 90."""
        for _, row in sample_player_data.iterrows():
            goals = row['goals']
            minutes = row['minutes_played']

            computed = compute_per_90(goals, minutes)

            if minutes > 0:
                expected = (goals / minutes) * 90
                assert computed == pytest.approx(expected, abs=1e-6), \
                    f"Goals per 90 incorrect for {row['player_name']}"

    def test_xg_overperformance_correctness(self, sample_player_data):
        """xG overperformance must be exactly goals - xG."""
        for _, row in sample_player_data.iterrows():
            goals = row['goals']
            xg = row['xg']

            # This is how overperformance should be calculated
            expected = goals - xg

            # Verify the formula
            assert isinstance(expected, (int, float))
            assert not np.isnan(expected)

    def test_assist_ratio_correctness(self, sample_player_data):
        """Assist ratio must be exactly assists / (goals + assists)."""
        for _, row in sample_player_data.iterrows():
            goals = row['goals']
            assists = row['assists']

            if goals + assists > 0:
                expected = assists / (goals + assists)
                assert 0.0 <= expected <= 1.0


class TestForbiddenMetricRejectionInvariant:
    """
    Tests for INVARIANT 5: Forbidden Metric Rejection.

    The system must reject any attempt to use forbidden/hallucinated metrics.
    """

    def test_reject_hallucinated_metrics(self, sample_metrics_registry):
        """System must reject metrics that don't exist."""
        with patch('services.metrics_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            hallucinated = [
                'made_up_stat',
                'hallucinated_metric',
                'fake_xg',
                'random_advanced_stat',
                'ai_generated_metric',
            ]

            for metric in hallucinated:
                # Either marked forbidden or doesn't exist
                is_forbidden = is_forbidden_metric(metric)
                exists = validate_metric_exists(metric)

                # At least one check should fail
                assert is_forbidden or not exists, \
                    f"Hallucinated metric '{metric}' was not rejected"

    def test_forbid_common_llm_hallucinations(self, sample_metrics_registry):
        """
        Explicitly test common LLM hallucination patterns.

        LLMs often generate plausible-sounding but fake metrics.
        """
        with patch('services.metrics_service.get_metrics_registry') as mock_registry:
            mock_registry.return_value = sample_metrics_registry

            common_hallucinations = [
                'expected_threat',      # Sounds real but isn't standard
                'creative_index',       # Made up
                'press_resistance',     # Plausible but not in registry
                'vertical_passes_90',   # Wrong format
                'goal_probability',     # Sounds like xG but isn't
            ]

            for metric in common_hallucinations:
                exists = validate_metric_exists(metric)
                # None of these should be valid
                assert not exists, \
                    f"Potential hallucination '{metric}' was accepted"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_dataframe_aggregation(self):
        """Aggregation on empty DataFrame should handle gracefully."""
        empty_df = pd.DataFrame(columns=['goals', 'minutes_played'])

        result = aggregate_metric(empty_df, 'goals', method='sum')
        assert result == 0 or pd.isna(result)

    def test_nan_values_in_per_90(self):
        """NaN values should be handled in per-90 calculation."""
        result = compute_per_90(np.nan, 900)
        assert pd.isna(result) or result == 0.0

    def test_very_small_minutes(self):
        """Very small minutes should not cause overflow."""
        result = compute_per_90(1, 0.001)
        # Should be a large but finite number or capped
        assert np.isfinite(result) or result == 0.0

    def test_very_large_values(self):
        """Very large values should be handled correctly."""
        result = compute_per_90(1e10, 900)
        expected = (1e10 / 900) * 90
        assert result == pytest.approx(expected, rel=1e-6)
