"""Tests for app.auth — password strength, hashing, and token generation."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


class TestPasswordStrength:
    """validate_password_strength enforces complexity rules."""

    def test_valid_password(self) -> None:
        from app.auth import validate_password_strength
        assert validate_password_strength("MyStr0ng!Pass") == "MyStr0ng!Pass"

    def test_too_short(self) -> None:
        from app.auth import validate_password_strength
        with pytest.raises(ValueError, match="at least"):
            validate_password_strength("Ab1!")

    def test_too_long(self) -> None:
        from app.auth import validate_password_strength
        with pytest.raises(ValueError, match="at most"):
            validate_password_strength("A" * 201 + "b1!")

    def test_no_uppercase(self) -> None:
        from app.auth import validate_password_strength
        with pytest.raises(ValueError, match="uppercase"):
            validate_password_strength("lowercase1!")

    def test_no_lowercase(self) -> None:
        from app.auth import validate_password_strength
        with pytest.raises(ValueError, match="lowercase"):
            validate_password_strength("UPPERCASE1!")

    def test_no_digit(self) -> None:
        from app.auth import validate_password_strength
        with pytest.raises(ValueError, match="digit"):
            validate_password_strength("NoDigitHere!")

    def test_no_special_char(self) -> None:
        from app.auth import validate_password_strength
        with pytest.raises(ValueError, match="special"):
            validate_password_strength("NoSpecial1")


class TestPasswordHashing:
    """hash_password and verify_password round-trip."""

    def test_hash_and_verify(self) -> None:
        from app.auth import hash_password, verify_password
        pwd = "MyStr0ng!Pass"
        hashed = hash_password(pwd)
        assert verify_password(pwd, hashed) is True

    def test_wrong_password_fails(self) -> None:
        from app.auth import hash_password, verify_password
        hashed = hash_password("Correct1!")
        assert verify_password("Wrong1!", hashed) is False

    def test_different_hashes_for_same_password(self) -> None:
        from app.auth import hash_password
        h1 = hash_password("Same1!Pass")
        h2 = hash_password("Same1!Pass")
        assert h1 != h2  # random salt

    def test_hash_format(self) -> None:
        from app.auth import hash_password
        h = hash_password("Test1!Pass")
        parts = h.split("$")
        assert len(parts) == 3
        assert parts[0].isdigit()  # iterations


class TestPasswordConstants:
    """Verify security constants are documented."""

    def test_iterations(self) -> None:
        from app.auth import PBKDF2_ITERATIONS
        assert PBKDF2_ITERATIONS >= 100_000

    def test_token_bytes(self) -> None:
        from app.auth import TOKEN_BYTES
        assert TOKEN_BYTES >= 16

    def test_special_chars_defined(self) -> None:
        from app.auth import SPECIAL_CHARS
        assert len(SPECIAL_CHARS) > 0
        assert "!" in SPECIAL_CHARS
