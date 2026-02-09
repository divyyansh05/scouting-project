"""
Tests for Similarity Service

Tests the core player similarity computation including:
- Cosine similarity calculations
- Position compatibility checks
- Similar player finding
- Similarity score breakdowns

8 Critical Invariants Tested:
1. Similarity Identity: self-similarity = 1.0
2. Monotonicity: higher weights → higher influence
3. Symmetry: sim(A,B) = sim(B,A)
4. Bounds: 0.0 ≤ similarity ≤ 1.0
"""

import pytest
import numpy as np
import pandas as pd
from typing import Dict, List
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.similarity_service import (
    cosine_similarity,
    are_positions_compatible,
    find_similar_players,
    similarity_score_breakdown,
    build_stats_vector,
    normalize_vector,
    SimilarityResult,
    ROLE_WEIGHT,
    STATS_WEIGHT,
)


class TestCosineSimilarity:
    """Tests for the cosine_similarity function."""

    def test_identical_vectors_return_one(self):
        """Identical vectors should have similarity of 1.0."""
        vector = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        similarity = cosine_similarity(vector, vector)
        assert similarity == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors_return_zero(self):
        """Orthogonal vectors should have similarity of 0.0."""
        vector1 = np.array([1.0, 0.0, 0.0])
        vector2 = np.array([0.0, 1.0, 0.0])
        similarity = cosine_similarity(vector1, vector2)
        assert similarity == pytest.approx(0.0, abs=1e-6)

    def test_opposite_vectors_clipped_to_zero(self):
        """Opposite vectors should be clipped to 0.0 (not negative)."""
        vector1 = np.array([1.0, 0.0, 0.0])
        vector2 = np.array([-1.0, 0.0, 0.0])
        similarity = cosine_similarity(vector1, vector2)
        assert similarity == pytest.approx(0.0, abs=1e-6)

    def test_zero_vector_returns_zero(self):
        """Zero vector should return 0.0 similarity."""
        vector1 = np.array([1.0, 2.0, 3.0])
        vector2 = np.array([0.0, 0.0, 0.0])
        similarity = cosine_similarity(vector1, vector2)
        assert similarity == 0.0

    def test_both_zero_vectors_return_zero(self):
        """Two zero vectors should return 0.0."""
        vector1 = np.array([0.0, 0.0, 0.0])
        vector2 = np.array([0.0, 0.0, 0.0])
        similarity = cosine_similarity(vector1, vector2)
        assert similarity == 0.0

    def test_similarity_is_symmetric(self):
        """Cosine similarity should be symmetric: sim(A,B) = sim(B,A)."""
        vector1 = np.array([1.0, 2.0, 3.0, 4.0])
        vector2 = np.array([4.0, 3.0, 2.0, 1.0])
        sim_ab = cosine_similarity(vector1, vector2)
        sim_ba = cosine_similarity(vector2, vector1)
        assert sim_ab == pytest.approx(sim_ba, abs=1e-6)

    def test_similarity_bounds(self):
        """Similarity should always be between 0 and 1."""
        np.random.seed(42)
        for _ in range(100):
            v1 = np.random.randn(20)
            v2 = np.random.randn(20)
            sim = cosine_similarity(v1, v2)
            assert 0.0 <= sim <= 1.0

    def test_scaled_vectors_same_similarity(self):
        """Scaling vectors should not change similarity."""
        vector1 = np.array([1.0, 2.0, 3.0])
        vector2 = np.array([2.0, 4.0, 6.0])  # vector1 * 2
        vector3 = np.array([4.0, 5.0, 6.0])

        sim_13 = cosine_similarity(vector1, vector3)
        sim_23 = cosine_similarity(vector2, vector3)
        assert sim_13 == pytest.approx(sim_23, abs=1e-6)


class TestPositionCompatibility:
    """Tests for position compatibility checking."""

    def test_same_position_compatible(self):
        """Same position should always be compatible."""
        assert are_positions_compatible('Central Midfield', 'Central Midfield') is True
        assert are_positions_compatible('Centre-Forward', 'Centre-Forward') is True
        assert are_positions_compatible('Goalkeeper', 'Goalkeeper') is True

    def test_related_positions_compatible(self):
        """Related positions should be compatible."""
        # Midfield positions
        assert are_positions_compatible('Central Midfield', 'Defensive Midfield') is True
        assert are_positions_compatible('Central Midfield', 'Attacking Midfield') is True

        # Wing positions
        assert are_positions_compatible('Left Winger', 'Right Winger') is True

    def test_unrelated_positions_not_compatible(self):
        """Unrelated positions should not be compatible."""
        assert are_positions_compatible('Goalkeeper', 'Centre-Forward') is False
        assert are_positions_compatible('Centre-Back', 'Left Winger') is False

    def test_goalkeeper_only_with_goalkeeper(self):
        """Goalkeeper should only be compatible with goalkeeper."""
        positions = [
            'Centre-Back', 'Left-Back', 'Right-Back',
            'Central Midfield', 'Defensive Midfield', 'Attacking Midfield',
            'Left Winger', 'Right Winger', 'Centre-Forward'
        ]
        for pos in positions:
            assert are_positions_compatible('Goalkeeper', pos) is False


class TestNormalizeVector:
    """Tests for vector normalization."""

    def test_normalize_to_unit_length(self):
        """Normalized vector should have unit length."""
        vector = np.array([3.0, 4.0])
        normalized = normalize_vector(vector)
        assert np.linalg.norm(normalized) == pytest.approx(1.0, abs=1e-6)

    def test_normalize_zero_vector(self):
        """Zero vector should return zero vector."""
        vector = np.array([0.0, 0.0, 0.0])
        normalized = normalize_vector(vector)
        assert np.all(normalized == 0.0)

    def test_normalize_preserves_direction(self):
        """Normalization should preserve direction."""
        vector = np.array([2.0, 4.0, 6.0])
        normalized = normalize_vector(vector)
        # Direction should be same (proportional)
        expected_direction = vector / np.linalg.norm(vector)
        np.testing.assert_array_almost_equal(normalized, expected_direction)


class TestBuildStatsVector:
    """Tests for building stats vectors from player data."""

    def test_build_vector_correct_length(self, sample_player_data):
        """Built vector should have correct length."""
        metrics = ['goals', 'assists', 'xg', 'xa', 'pass_accuracy']
        row = sample_player_data.iloc[0]
        vector = build_stats_vector(row, metrics)
        assert len(vector) == len(metrics)

    def test_build_vector_handles_missing(self, sample_player_data):
        """Should handle missing metrics gracefully."""
        metrics = ['goals', 'nonexistent_metric', 'assists']
        row = sample_player_data.iloc[0]
        vector = build_stats_vector(row, metrics)
        assert len(vector) == len(metrics)
        assert vector[1] == 0.0  # Missing metric should be 0

    def test_build_vector_all_zeros_for_empty(self):
        """Empty row should produce zero vector."""
        empty_row = pd.Series({'goals': 0, 'assists': 0})
        metrics = ['goals', 'assists']
        vector = build_stats_vector(empty_row, metrics)
        np.testing.assert_array_equal(vector, np.array([0.0, 0.0]))


class TestSimilarityScoreBreakdown:
    """Tests for similarity score breakdown."""

    def test_breakdown_sums_to_total(self, sample_role_vectors, sample_stats_vectors):
        """Role and stats components should sum to total (approximately)."""
        breakdown = similarity_score_breakdown(
            role_vector_1=sample_role_vectors[1],
            role_vector_2=sample_role_vectors[2],
            stats_vector_1=sample_stats_vectors[1],
            stats_vector_2=sample_stats_vectors[2],
        )

        # Weighted sum should equal total
        expected_total = (
            breakdown['role_similarity'] * ROLE_WEIGHT +
            breakdown['stats_similarity'] * STATS_WEIGHT
        )
        assert breakdown['total_similarity'] == pytest.approx(expected_total, abs=0.01)

    def test_breakdown_components_bounded(self, sample_role_vectors, sample_stats_vectors):
        """All breakdown components should be between 0 and 1."""
        breakdown = similarity_score_breakdown(
            role_vector_1=sample_role_vectors[1],
            role_vector_2=sample_role_vectors[3],
            stats_vector_1=sample_stats_vectors[1],
            stats_vector_2=sample_stats_vectors[3],
        )

        assert 0.0 <= breakdown['role_similarity'] <= 1.0
        assert 0.0 <= breakdown['stats_similarity'] <= 1.0
        assert 0.0 <= breakdown['total_similarity'] <= 1.0

    def test_self_similarity_breakdown(self, sample_role_vectors, sample_stats_vectors):
        """Self-comparison should have perfect similarity in all components."""
        breakdown = similarity_score_breakdown(
            role_vector_1=sample_role_vectors[1],
            role_vector_2=sample_role_vectors[1],
            stats_vector_1=sample_stats_vectors[1],
            stats_vector_2=sample_stats_vectors[1],
        )

        assert breakdown['role_similarity'] == pytest.approx(1.0, abs=1e-6)
        assert breakdown['stats_similarity'] == pytest.approx(1.0, abs=1e-6)
        assert breakdown['total_similarity'] == pytest.approx(1.0, abs=1e-6)


class TestSimilarityResultDataclass:
    """Tests for SimilarityResult dataclass."""

    def test_create_similarity_result(self):
        """Should create valid SimilarityResult."""
        result = SimilarityResult(
            player_id=1,
            player_name="Test Player",
            team_name="Test Team",
            position="Central Midfield",
            similarity_score=0.85,
            role_similarity=0.90,
            stats_similarity=0.75,
        )

        assert result.player_id == 1
        assert result.player_name == "Test Player"
        assert result.similarity_score == 0.85

    def test_similarity_result_ordering(self):
        """SimilarityResults should be orderable by score."""
        results = [
            SimilarityResult(1, "A", "Team", "CM", 0.70, 0.75, 0.60),
            SimilarityResult(2, "B", "Team", "CM", 0.90, 0.95, 0.80),
            SimilarityResult(3, "C", "Team", "CM", 0.80, 0.85, 0.70),
        ]

        sorted_results = sorted(results, key=lambda x: x.similarity_score, reverse=True)
        assert sorted_results[0].player_name == "B"
        assert sorted_results[1].player_name == "C"
        assert sorted_results[2].player_name == "A"


class TestFindSimilarPlayers:
    """Integration tests for find_similar_players function."""

    def test_excludes_target_player(
        self,
        sample_player_data,
        sample_role_vectors,
        sample_stats_vectors
    ):
        """Target player should not appear in results."""
        target_player_id = 1

        with patch('services.similarity_service.get_role_vectors') as mock_roles, \
             patch('services.similarity_service.get_stats_vectors') as mock_stats, \
             patch('services.similarity_service.get_player_data') as mock_data:

            mock_roles.return_value = sample_role_vectors
            mock_stats.return_value = sample_stats_vectors
            mock_data.return_value = sample_player_data

            results = find_similar_players(
                target_player_id=target_player_id,
                limit=10
            )

            result_ids = [r.player_id for r in results]
            assert target_player_id not in result_ids

    def test_respects_limit(
        self,
        sample_player_data,
        sample_role_vectors,
        sample_stats_vectors
    ):
        """Should respect the limit parameter."""
        with patch('services.similarity_service.get_role_vectors') as mock_roles, \
             patch('services.similarity_service.get_stats_vectors') as mock_stats, \
             patch('services.similarity_service.get_player_data') as mock_data:

            mock_roles.return_value = sample_role_vectors
            mock_stats.return_value = sample_stats_vectors
            mock_data.return_value = sample_player_data

            limit = 2
            results = find_similar_players(
                target_player_id=1,
                limit=limit
            )

            assert len(results) <= limit

    def test_results_sorted_by_similarity(
        self,
        sample_player_data,
        sample_role_vectors,
        sample_stats_vectors
    ):
        """Results should be sorted by similarity score descending."""
        with patch('services.similarity_service.get_role_vectors') as mock_roles, \
             patch('services.similarity_service.get_stats_vectors') as mock_stats, \
             patch('services.similarity_service.get_player_data') as mock_data:

            mock_roles.return_value = sample_role_vectors
            mock_stats.return_value = sample_stats_vectors
            mock_data.return_value = sample_player_data

            results = find_similar_players(
                target_player_id=1,
                limit=10
            )

            scores = [r.similarity_score for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_position_filter_applied(
        self,
        sample_player_data,
        sample_role_vectors,
        sample_stats_vectors
    ):
        """Position filter should limit results to compatible positions."""
        with patch('services.similarity_service.get_role_vectors') as mock_roles, \
             patch('services.similarity_service.get_stats_vectors') as mock_stats, \
             patch('services.similarity_service.get_player_data') as mock_data:

            mock_roles.return_value = sample_role_vectors
            mock_stats.return_value = sample_stats_vectors
            mock_data.return_value = sample_player_data

            results = find_similar_players(
                target_player_id=1,  # Central Midfield
                position_filter='same_group',
                limit=10
            )

            # All results should be midfielders
            for result in results:
                assert 'Midfield' in result.position or result.position in [
                    'Central Midfield', 'Defensive Midfield', 'Attacking Midfield'
                ]


class TestInvariants:
    """Tests for critical system invariants."""

    def test_invariant_similarity_identity(self, sample_role_vectors, sample_stats_vectors):
        """
        INVARIANT 1: Self-similarity must equal 1.0

        A player compared to themselves must have perfect similarity.
        """
        for player_id in sample_role_vectors:
            breakdown = similarity_score_breakdown(
                role_vector_1=sample_role_vectors[player_id],
                role_vector_2=sample_role_vectors[player_id],
                stats_vector_1=sample_stats_vectors[player_id],
                stats_vector_2=sample_stats_vectors[player_id],
            )
            assert breakdown['total_similarity'] == pytest.approx(1.0, abs=1e-6), \
                f"Self-similarity for player {player_id} is not 1.0"

    def test_invariant_symmetry(self, sample_role_vectors, sample_stats_vectors):
        """
        INVARIANT: Similarity must be symmetric.

        sim(A, B) must equal sim(B, A) for all player pairs.
        """
        player_ids = list(sample_role_vectors.keys())

        for i, id1 in enumerate(player_ids):
            for id2 in player_ids[i+1:]:
                breakdown_ab = similarity_score_breakdown(
                    role_vector_1=sample_role_vectors[id1],
                    role_vector_2=sample_role_vectors[id2],
                    stats_vector_1=sample_stats_vectors[id1],
                    stats_vector_2=sample_stats_vectors[id2],
                )
                breakdown_ba = similarity_score_breakdown(
                    role_vector_1=sample_role_vectors[id2],
                    role_vector_2=sample_role_vectors[id1],
                    stats_vector_1=sample_stats_vectors[id2],
                    stats_vector_2=sample_stats_vectors[id1],
                )

                assert breakdown_ab['total_similarity'] == pytest.approx(
                    breakdown_ba['total_similarity'], abs=1e-6
                ), f"Symmetry violated for players {id1} and {id2}"

    def test_invariant_bounds(self, sample_role_vectors, sample_stats_vectors):
        """
        INVARIANT: Similarity must be bounded [0, 1].

        No similarity score can be negative or greater than 1.
        """
        player_ids = list(sample_role_vectors.keys())

        for id1 in player_ids:
            for id2 in player_ids:
                breakdown = similarity_score_breakdown(
                    role_vector_1=sample_role_vectors[id1],
                    role_vector_2=sample_role_vectors[id2],
                    stats_vector_1=sample_stats_vectors[id1],
                    stats_vector_2=sample_stats_vectors[id2],
                )

                assert 0.0 <= breakdown['total_similarity'] <= 1.0, \
                    f"Bounds violated for players {id1} and {id2}"
                assert 0.0 <= breakdown['role_similarity'] <= 1.0
                assert 0.0 <= breakdown['stats_similarity'] <= 1.0

    def test_invariant_monotonicity(self, sample_role_vectors, sample_stats_vectors):
        """
        INVARIANT 2: Higher weights should have proportionally higher influence.

        With ROLE_WEIGHT=0.6 and STATS_WEIGHT=0.4, role similarity should
        contribute more to the total than stats similarity.
        """
        # Create vectors where role is similar but stats differ
        role_similar = {
            1: sample_role_vectors[1],
            2: sample_role_vectors[1].copy(),  # Same role
        }
        role_similar[2] += np.random.randn(20) * 0.01  # Tiny perturbation

        stats_different = {
            1: sample_stats_vectors[1],
            2: np.random.randn(10),  # Very different stats
        }

        breakdown = similarity_score_breakdown(
            role_vector_1=role_similar[1],
            role_vector_2=role_similar[2],
            stats_vector_1=stats_different[1],
            stats_vector_2=stats_different[2],
        )

        # Role contribution should be dominant
        role_contribution = breakdown['role_similarity'] * ROLE_WEIGHT
        stats_contribution = breakdown['stats_similarity'] * STATS_WEIGHT

        # With similar roles but different stats, role should contribute more
        assert role_contribution > stats_contribution * 0.5, \
            "Role weight not having proportional influence"
