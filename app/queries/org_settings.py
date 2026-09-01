# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------


def _log_audit(
    db: Session,
    org_id: int,
    performed_by_user_id: int,
    action: str,
    *,
    target_user_id: int | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    detail: dict | None = None,
) -> None:
    """Append an audit log entry. Never raises — audit failures are logged."""
    try:
        log_entry = AuditLog(
            org_id=org_id,
            action=action,
            performed_by_user_id=performed_by_user_id,
            target_user_id=target_user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail or {},
        )
        db.add(log_entry)
    except (SQLAlchemyError, ValueError) as exc:
        logger.warning("Audit log write failed for %s/%s: %s", resource_type, resource_id, exc)


def get_audit_log(
    db: Session,
    org_id: int,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]] -> None:
    """Get audit log entries for an organization. Owner/manager only."""
    entries = (
        db.query(AuditLog, User)
        .join(User, AuditLog.performed_by_user_id == User.id)
        .filter(AuditLog.org_id == org_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [
        {
            "id": log.id,
            "action": log.action,
            "performed_by": user.display_name or user.email,
            "performed_by_user_id": log.performed_by_user_id,
            "target_user_id": log.target_user_id,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "detail": log.detail,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log, user in entries
    ]


# ---------------------------------------------------------------------------
# Org settings
# ---------------------------------------------------------------------------


def get_org_settings(db: Session, org_id: int) -> dict[str, Any] | None:
    """Get organization settings."""
    settings = db.query(OrgSettings).filter(OrgSettings.org_id == org_id).first()
    if settings is None:
        return None
    return {
        "org_id": settings.org_id,
        "data_retention_days": settings.data_retention_days,
        "workspace_name": settings.workspace_name,
        "enable_audit_logging": settings.enable_audit_logging,
        "allow_public_reporting": settings.allow_public_reporting,
        "require_2fa": settings.require_2fa,
    }


def update_org_settings(
    db: Session,
    org_id: int,
    user_id: int,
    **kwargs: Any,
) -> dict[str, Any] -> None:
    """Update organization settings. Owner/manager only."""
    if not user_has_permission(db, user_id, org_id, "org_settings_edit"):
        raise PermissionError("You do not have permission to edit org settings")

    settings = db.query(OrgSettings).filter(OrgSettings.org_id == org_id).first()
    if settings is None:
        # Create if missing
        settings = OrgSettings(org_id=org_id)
        db.add(settings)
        db.flush()

    for key, value in kwargs.items():
        if hasattr(settings, key) and value is not None:
            setattr(settings, key, value)

    db.commit()
    return get_org_settings(db, org_id)


# ---------------------------------------------------------------------------
# Resource access helpers (Part C2)
# ---------------------------------------------------------------------------


def get_user_shortlists(
    db: Session,
    user_id: int,
    *,
    org_id: int | None = None,
) -> list[dict[str, Any]] -> None:
    """Get shortlists accessible to the user, including personal + org-shared.

    If org_id is provided, returns shortlists in that org context.
    If org_id is None, returns all accessible shortlists across all contexts.
    """
    from app.models import ShortlistEntry

    # Personal shortlists (always visible to the owner)
    personal = (
        db.query(Shortlist)
        .filter(
            Shortlist.user_id == user_id,
            Shortlist.deleted_at.is_(None),
            Shortlist.owner_org_id.is_(None),
        )
        .all()
    )

    results = []
    for sl in personal:
        entry_count = (
            db.query(ShortlistEntry)
            .filter(
                ShortlistEntry.shortlist_id == sl.id,
                ShortlistEntry.removed_at.is_(None),
            )
            .count()
        )
        results.append(
            {
                "shortlist_id": sl.id,
                "name": sl.name,
                "description": sl.description,
                "entry_count": entry_count,
                "visibility": getattr(sl, "visibility", "personal"),
                "owner_type": "personal",
                "created_at": sl.created_at.isoformat() if sl.created_at else None,
            }
        )

    # Org-shared shortlists
    user_org_ids = get_user_org_ids(db, user_id)
    if org_id is not None:
        user_org_ids = [oid for oid in user_org_ids if oid == org_id]

    if user_org_ids:
        org_shortlists = (
            db.query(Shortlist)
            .filter(
                Shortlist.owner_org_id.in_(user_org_ids),
                Shortlist.deleted_at.is_(None),
            )
            .all()
        )
        for sl in org_shortlists:
            # Check visibility access
            vis = getattr(sl, "visibility", "org_members")
            if vis == "personal" and sl.user_id != user_id:
                continue  # Other users' personal shortlists in org are hidden
            if vis == "restricted":
                restricted_access = getattr(sl, "restricted_access", None) or []
                if user_id not in restricted_access:
                    user_role = get_user_org_role(db, user_id, sl.owner_org_id)
                    if user_role not in ("owner", "manager"):
                        continue

            entry_count = (
                db.query(ShortlistEntry)
                .filter(
                    ShortlistEntry.shortlist_id == sl.id,
                    ShortlistEntry.removed_at.is_(None),
                )
                .count()
            )
            creator = db.get(User, sl.user_id)
            results.append(
                {
                    "shortlist_id": sl.id,
                    "name": sl.name,
                    "description": sl.description,
                    "entry_count": entry_count,
                    "visibility": vis,
                    "owner_type": "org",
                    "org_id": sl.owner_org_id,
                    "created_by": (
                        creator.display_name or creator.email if creator else None
                    ),
                    "created_at": sl.created_at.isoformat() if sl.created_at else None,
                }
            )

    return results
