"""Test package — makes `tests` importable so conftest helpers and shared
fixture factories (e.g. `from tests.test_integration import _fixtures`) resolve.
pytest.ini sets `pythonpath = .`, so `tests` is importable as a package from
the project root.
"""
