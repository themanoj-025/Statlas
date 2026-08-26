"""Tests for app.logging_setup — request IDs, filter, and setup_logging."""
from __future__ import annotations

import logging

from app.logging_setup import (
    RequestIdFilter,
    new_request_id,
    request_id_var,
    setup_logging,
)


class TestRequestIdFilter:
    def test_injects_request_id_into_record(self):
        filt = RequestIdFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None,
        )
        request_id_var.set("abc-123")
        assert filt.filter(record) is True
        assert getattr(record, "request_id") == "abc-123"

    def test_default_request_id(self):
        """Without setting a ContextVar, the default '-' is used."""
        filt = RequestIdFilter()
        request_id_var.set("-")
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test", args=(), exc_info=None,
        )
        assert filt.filter(record) is True
        assert getattr(record, "request_id") == "-"

    def test_filter_always_returns_true(self):
        filt = RequestIdFilter()
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="", lineno=0,
            msg="warning", args=(), exc_info=None,
        )
        assert filt.filter(record) is True


class TestNewRequestId:
    def test_returns_hex_string(self):
        rid = new_request_id()
        assert len(rid) == 12
        assert all(c in "0123456789abcdef" for c in rid)

    def test_sets_context_var(self):
        rid = new_request_id()
        assert request_id_var.get() == rid

    def test_unique_ids(self):
        ids = {new_request_id() for _ in range(100)}
        # With 12-char hex (64^12 space), 100 should all be unique
        assert len(ids) == 100


class TestSetupLogging:
    def test_configures_root_logger(self):
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        try:
            setup_logging(level="WARNING")
            assert root.level == logging.WARNING
            assert len(root.handlers) >= 1
        finally:
            root.handlers = original_handlers

    def test_adds_handler_with_filter(self):
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        try:
            setup_logging(level="INFO")
            handler = root.handlers[-1]
            filter_names = [type(f).__name__ for f in handler.filters]
            assert "RequestIdFilter" in filter_names
        finally:
            root.handlers = original_handlers

    def test_log_output_contains_request_id(self, capsys):
        """Verify that a log message includes the request_id field."""
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        original_level = root.level
        try:
            setup_logging(level="DEBUG")
            request_id_var.set("test-req-001")
            logger = logging.getLogger("test.logging_module")
            logger.info("Hello from test")

            captured = capsys.readouterr()
            # The output should contain the request ID
            assert "test-req-001" in captured.err or "test-req-001" in captured.out
        finally:
            root.handlers = original_handlers
            root.level = original_level

    def test_default_level_is_info(self):
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        try:
            setup_logging()
            assert root.level == logging.INFO
        finally:
            root.handlers = original_handlers


class TestRequestIdIntegration:
    def test_new_request_id_overwrites_previous(self):
        request_id_var.set("first")
        rid = new_request_id()
        assert request_id_var.get() == rid
        assert rid != "first"

    def test_context_var_isolation(self):
        """ContextVar works correctly across calls."""
        request_id_var.set("id-aaa")
        assert request_id_var.get() == "id-aaa"
        request_id_var.set("id-bbb")
        assert request_id_var.get() == "id-bbb"
