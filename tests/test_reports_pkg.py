"""Tests for app.reports_pkg — confidence, narrators, pipeline, verification."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


class TestReportsConfidence:
    """Test reports confidence module."""

    def test_module_importable(self) -> None:
        import app.reports_pkg.confidence as mod
        assert hasattr(mod, "__file__")

    def test_module_has_functions(self) -> None:
        import inspect

        import app.reports_pkg.confidence as mod
        funcs = [name for name, obj in inspect.getmembers(mod) if inspect.isfunction(obj)]
        assert len(funcs) > 0


class TestReportsNarrators:
    """Test reports narrators module."""

    def test_module_importable(self) -> None:
        import app.reports_pkg.narrators as mod
        assert hasattr(mod, "__file__")

    def test_module_has_functions(self) -> None:
        import inspect

        import app.reports_pkg.narrators as mod
        funcs = [name for name, obj in inspect.getmembers(mod) if inspect.isfunction(obj)]
        assert len(funcs) > 0


class TestReportsPipeline:
    """Test reports pipeline module."""

    def test_module_importable(self) -> None:
        import app.reports_pkg.pipeline as mod
        assert hasattr(mod, "__file__")

    def test_module_has_functions(self) -> None:
        import inspect

        import app.reports_pkg.pipeline as mod
        funcs = [name for name, obj in inspect.getmembers(mod) if inspect.isfunction(obj)]
        assert len(funcs) > 0


class TestReportsVerification:
    """Test reports verification module."""

    def test_module_importable(self) -> None:
        import app.reports_pkg.verification as mod
        assert hasattr(mod, "__file__")

    def test_module_has_functions(self) -> None:
        import inspect

        import app.reports_pkg.verification as mod
        funcs = [name for name, obj in inspect.getmembers(mod) if inspect.isfunction(obj)]
        assert len(funcs) > 0


class TestReportsContext:
    """Test reports context module."""

    def test_module_importable(self) -> None:
        import app.reports_pkg.context as mod
        assert hasattr(mod, "__file__")

    def test_module_has_functions(self) -> None:
        import inspect

        import app.reports_pkg.context as mod
        funcs = [name for name, obj in inspect.getmembers(mod) if inspect.isfunction(obj)]
        assert len(funcs) > 0


class TestReportsRisk:
    """Test reports risk module."""

    def test_module_importable(self) -> None:
        import app.reports_pkg.risk as mod
        assert hasattr(mod, "__file__")


class TestReportsQuota:
    """Test reports quota module."""

    def test_module_importable(self) -> None:
        import app.reports_pkg.quota as mod
        assert hasattr(mod, "__file__")


class TestReportExport:
    """Test report export module."""

    def test_module_importable(self) -> None:
        import app.report_export as mod
        assert hasattr(mod, "__file__")


class TestReportStyles:
    """Test report styles module."""

    def test_module_importable(self) -> None:
        import app.report_styles as mod
        assert hasattr(mod, "__file__")
