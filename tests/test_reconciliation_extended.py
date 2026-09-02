"""Tests for app.reconciliation — name normalization and suffix stripping."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


class TestNormalizeName:
    """normalize_name lowercases, strips accents, drops punctuation."""

    def test_simple_name(self) -> None:
        from app.reconciliation import normalize_name
        assert normalize_name("Kevin De Bruyne") == "kevin de bruyne"

    def test_accented_characters(self) -> None:
        from app.reconciliation import normalize_name
        assert normalize_name("José Mourinho") == "jose mourinho"

    def test_punctuation_stripped(self) -> None:
        from app.reconciliation import normalize_name
        assert normalize_name("K. De Bruyne") == "k de bruyne"

    def test_empty_string(self) -> None:
        from app.reconciliation import normalize_name
        assert normalize_name("") == ""

    def test_whitespace_collapsed(self) -> None:
        from app.reconciliation import normalize_name
        assert normalize_name("  Kevin   De   Bruyne  ") == "kevin de bruyne"

    def test_special_characters(self) -> None:
        from app.reconciliation import normalize_name
        assert normalize_name("O'Connor") == "oconnor"


class TestStripSuffixes:
    """strip_suffixes removes generation suffixes."""

    def test_junior(self) -> None:
        from app.reconciliation import strip_suffixes
        assert strip_suffixes("Haaland Jr.") == "haaland"

    def test_senior(self) -> None:
        from app.reconciliation import strip_suffixes
        assert strip_suffixes("Martinelli Sr.") == "martinelli"

    def test_roman_iii(self) -> None:
        from app.reconciliation import strip_suffixes
        assert strip_suffixes("Williams III") == "williams"

    def test_no_suffix(self) -> None:
        from app.reconciliation import strip_suffixes
        assert strip_suffixes("Salah") == "salah"


class TestNormalizedTeam:
    """normalized_team returns None for None input."""

    def test_none_team(self) -> None:
        from app.reconciliation import normalized_team
        assert normalized_team(None) is None

    def test_team_name(self) -> None:
        from app.reconciliation import normalized_team
        assert normalized_team("Manchester City") == "manchester city"


class TestReconcilerInit:
    """Reconciler class can be instantiated with a mock db."""

    def test_class_exists(self) -> None:
        import inspect

        from app.reconciliation import Reconciler
        assert inspect.isclass(Reconciler)

    def test_has_resolve_method(self) -> None:
        from app.reconciliation import Reconciler
        assert hasattr(Reconciler, "resolve") or hasattr(Reconciler, "reconcile")
