"""Tests for app.compute.spatial_analysis — zone assignment and spatial utilities."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


class TestZoneAssignment:
    """assign_zone returns (row, col) for StatsBomb coordinates."""

    def test_defensive_left_corner(self) -> None:
        from app.compute.spatial_analysis import assign_zone
        assert assign_zone(0, 0) == (0, 0)

    def test_defensive_center(self) -> None:
        from app.compute.spatial_analysis import assign_zone
        assert assign_zone(6, 40) == (0, 1)

    def test_midfield_center(self) -> None:
        from app.compute.spatial_analysis import assign_zone
        assert assign_zone(60, 40) == (2, 1)

    def test_attacking_right(self) -> None:
        from app.compute.spatial_analysis import assign_zone
        assert assign_zone(110, 70) == (3, 2)

    def test_out_of_bounds_clamps(self) -> None:
        from app.compute.spatial_analysis import assign_zone
        assert assign_zone(200, 200) == (3, 2)
        assert assign_zone(-10, -10) == (0, 0)


class TestZoneNames:
    """assign_zone_name returns human-readable zone labels."""

    def test_known_zone(self) -> None:
        from app.compute.spatial_analysis import assign_zone_name
        assert assign_zone_name(6, 40) == "defensive_center"

    def test_attacking_zone(self) -> None:
        from app.compute.spatial_analysis import assign_zone_name
        assert assign_zone_name(100, 40) == "attacking_center"


class TestThirdAssignment:
    """assign_third returns defensive/middle/attacking."""

    def test_defensive_third(self) -> None:
        from app.compute.spatial_analysis import assign_third
        assert assign_third(5) == "defensive"

    def test_middle_third(self) -> None:
        from app.compute.spatial_analysis import assign_third
        assert assign_third(60) == "middle"

    def test_attacking_third(self) -> None:
        from app.compute.spatial_analysis import assign_third
        assert assign_third(110) == "attacking"


class TestWidthAssignment:
    """assign_width returns left/center/right."""

    def test_left_flank(self) -> None:
        from app.compute.spatial_analysis import assign_width
        assert assign_width(5) == "left"

    def test_center(self) -> None:
        from app.compute.spatial_analysis import assign_width
        assert assign_width(40) == "center"

    def test_right_flank(self) -> None:
        from app.compute.spatial_analysis import assign_width
        assert assign_width(75) == "right"


class TestPitchConstants:
    """Verify pitch dimensions are correct."""

    def test_pitch_dimensions(self) -> None:
        from app.compute.spatial_analysis import PITCH_LENGTH, PITCH_WIDTH
        assert PITCH_LENGTH == 120.0
        assert PITCH_WIDTH == 80.0

    def test_zone_names_complete(self) -> None:
        from app.compute.spatial_analysis import ZONE_COLS, ZONE_NAMES, ZONE_ROWS
        assert len(ZONE_NAMES) == ZONE_ROWS * ZONE_COLS
