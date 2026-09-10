"""Workspace queries — shortlists and entry management.

Implementation split across:
- workspace_helpers.py: validation, status transitions, helper functions
  (canonical home for exceptions and shared helpers)
- workspace_shortlists.py: shortlist CRUD operations
- workspace_entries.py: entry add/update/notes/tags/detail operations

This module is a facade: import from here, never from the split modules
directly.
"""

from __future__ import annotations

from app.queries.workspace_entries import (
    add_entry_note,
    add_entry_tag,
    add_player_to_shortlist,
    get_shortlist_detail,
    get_shortlist_memberships,
    get_user_tag_suggestions,
    remove_entry,
    remove_entry_by_id,
    remove_entry_tag,
    set_entry_priority,
    update_entry_status,
)

# Canonical helpers/exceptions MUST be re-exported before the split modules
# below: they import these names back from this facade at import time.
from app.queries.workspace_helpers import (
    ALL_STATUSES,
    DEFAULT_SHORTLIST_DESCRIPTION,
    DEFAULT_SHORTLIST_NAME,
    PIPELINE_ORDER,
    PRIORITIES,
    TERMINAL_STATUSES,
    DuplicateEntry,
    InvalidStatusTransition,
    PlayerNotFound,
    ShortlistNotFound,
    WorkspaceLimitExceeded,
    _bump_shortlist,
    _entry_counts,
    _now,
    _owned_entry,
    _owned_shortlist,
    validate_transition,
)
from app.queries.workspace_shortlists import (
    create_shortlist,
    delete_shortlist,
    ensure_default_shortlist,
    list_shortlists,
)

__all__ = [
    "ALL_STATUSES",
    "DEFAULT_SHORTLIST_DESCRIPTION",
    "DEFAULT_SHORTLIST_NAME",
    "PIPELINE_ORDER",
    "PRIORITIES",
    "TERMINAL_STATUSES",
    "DuplicateEntry",
    "InvalidStatusTransition",
    "PlayerNotFound",
    "ShortlistNotFound",
    "WorkspaceLimitExceeded",
    "add_entry_note",
    "add_entry_tag",
    "add_player_to_shortlist",
    "create_shortlist",
    "delete_shortlist",
    "ensure_default_shortlist",
    "get_shortlist_detail",
    "get_shortlist_memberships",
    "get_user_tag_suggestions",
    "list_shortlists",
    "remove_entry",
    "remove_entry_by_id",
    "remove_entry_tag",
    "set_entry_priority",
    "update_entry_status",
    "validate_transition",
]
