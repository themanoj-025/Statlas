
from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

"""Tests for app.csrf — token generation, verification, and edge cases."""

import time
from unittest.mock import patch

from app.csrf import (
    CSRF_TOKEN_TTL,
    generate_csrf_token,
    verify_csrf_token,
)


class TestGenerateCsrfToken:
    def test_returns_string_with_colon_separator(self) -> None:
        token = generate_csrf_token("session-abc")
        assert ":" in token
        parts = token.split(":")
        assert len(parts) == 2

    def test_timestamp_is_numeric(self) -> None:
        token = generate_csrf_token("session-abc")
        ts_str, _ = token.split(":")
        assert ts_str.isdigit()

    def test_signature_is_hex(self) -> None:
        token = generate_csrf_token("session-abc")
        _, sig = token.split(":")
        assert len(sig) == 32
        assert all(c in "0123456789abcdef" for c in sig)

    def test_different_sessions_produce_different_tokens(self) -> None:
        t1 = generate_csrf_token("session-1")
        t2 = generate_csrf_token("session-2")
        # The signatures should differ (different session IDs)
        _, sig1 = t1.split(":")
        _, sig2 = t2.split(":")
        assert sig1 != sig2

    def test_same_session_same_second_same_token(self) -> None:
        """Same session ID + same second = same token (deterministic)."""
        t1 = generate_csrf_token("session-abc")
        t2 = generate_csrf_token("session-abc")
        assert t1 == t2


class TestVerifyCsrfToken:
    def test_valid_token_accepted(self) -> None:
        session_id = "test-session-123"
        token = generate_csrf_token(session_id)
        assert verify_csrf_token(token, session_id) is True

    def test_wrong_session_rejected(self) -> None:
        token = generate_csrf_token("session-1")
        assert verify_csrf_token(token, "session-2") is False

    def test_tampered_signature_rejected(self) -> None:
        session_id = "test-session"
        token = generate_csrf_token(session_id)
        ts, _ = token.split(":")
        tampered = f"{ts}:00000000000000000000000000000000"
        assert verify_csrf_token(tampered, session_id) is False

    def test_tampered_timestamp_rejected(self) -> None:
        session_id = "test-session"
        token = generate_csrf_token(session_id)
        _, sig = token.split(":")
        tampered = f"0000000000:{sig}"
        assert verify_csrf_token(tampered, session_id) is False

    def test_empty_token_rejected(self) -> None:
        assert verify_csrf_token("", "session") is False

    def test_no_colon_rejected(self) -> None:
        assert verify_csrf_token("nocolonhere", "session") is False

    def test_too_many_colons_rejected(self) -> None:
        assert verify_csrf_token("a:b:c", "session") is False

    def test_non_numeric_timestamp_rejected(self) -> None:
        assert verify_csrf_token("notanumber:abcdef1234567890", "session") is False

    def test_empty_session_id(self) -> None:
        token = generate_csrf_token("")
        assert verify_csrf_token(token, "") is True

    def test_expired_token_rejected(self) -> None:
        """Token older than CSRF_TOKEN_TTL should be rejected."""
        session_id = "test-session"
        # Forge an old token
        str(int(time.time()) - CSRF_TOKEN_TTL - 100)
        # We can't forge the signature without the secret, but we can test
        # that verify_csrf_token returns False for old timestamps.
        # The signature check happens before expiry, but let's generate with
        # the correct signature for a future timestamp and verify expiry logic.
        token = generate_csrf_token(session_id)

        # Patch time.time to simulate expiry
        with patch("app.csrf.time") as mock_time:
            ts_str, _ = token.split(":")
            # Set time to be after the token's TTL
            mock_time.time.return_value = int(ts_str) + CSRF_TOKEN_TTL + 100
            # The function uses time.time() for expiry check
            assert verify_csrf_token(token, session_id) is False


class TestCsrfConstants:
    def test_ttl_is_one_hour(self) -> None:
        assert CSRF_TOKEN_TTL == 3600

    def test_header_name(self) -> None:
        from app.csrf import CSRF_TOKEN_HEADER

        assert CSRF_TOKEN_HEADER == "X-CSRF-Token"


# ---------------------------------------------------------------------------
# CSRF middleware integration (simulated)
# ---------------------------------------------------------------------------


class TestCSRFMiddlewareIntegration:
    """Tests for the CSRF middleware behavior. Since CSRF is disabled in
    test mode (STATLAS_ENV=test), these test the token generation/verification
    logic that the middleware relies on."""

    def test_token_roundtrip(self) -> None:
        """Generate a token and verify it succeeds."""
        from app.csrf import generate_csrf_token, verify_csrf_token

        session_id = "test-session-abc123"
        token = generate_csrf_token(session_id)
        assert verify_csrf_token(token, session_id) is True

    def test_token_rejects_wrong_session(self) -> None:
        """Token for one session should fail for another."""
        from app.csrf import generate_csrf_token, verify_csrf_token

        token = generate_csrf_token("session-A")
        assert verify_csrf_token(token, "session-B") is False

    def test_token_rejects_tampered(self) -> None:
        """Tampered token should fail verification."""
        from app.csrf import generate_csrf_token, verify_csrf_token

        token = generate_csrf_token("session-A")
        ts, _sig = token.split(":")
        tampered = f"{ts}:00000000000000000000000000000000"
        assert verify_csrf_token(tampered, "session-A") is False

    def test_token_rejects_empty(self) -> None:
        from app.csrf import verify_csrf_token

        assert verify_csrf_token("", "session-A") is False
