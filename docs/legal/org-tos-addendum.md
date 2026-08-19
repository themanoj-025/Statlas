# Statlas — Organization Terms of Service Addendum

> ## ⚠️ DRAFT — REQUIRES LAWYER REVIEW BEFORE PUBLICATION
>
> This is a draft addendum to the Statlas Terms of Service covering organization/team features. It must be reviewed and signed off by a qualified lawyer before publication.
>
> Draft date: 2026-08-19 · Supplement to `terms-of-service-draft.md` v1.0.

---

## Overview

This addendum supplements the Statlas Terms of Service (`terms-of-service-draft.md`) for users and organizations that use Statlas's multi-tenant organization features. All general terms remain in effect; this addendum governs organization-specific rights, responsibilities, and data handling.

**By creating or joining an organization on Statlas, you agree to the terms in this addendum in addition to the main Terms of Service.**

---

## 1. Organization data ownership

### 1.1 Organization-owned data

Data created within an organization context (shared shortlists, reports, searches, watches, comments) is owned by the **organization**, not by individual members. This means:

- The organization owner controls the data lifecycle (retention, deletion, export).
- When a member is removed from an organization, resources they created with `org_members` or `restricted` visibility remain with the organization.
- The organization owner may access, modify, or delete any shared resource regardless of who created it.

### 1.2 Personal data remains personal

Individual users retain full ownership of their personal (non-org) data:

- Personal shortlists, reports, saved searches, and bookmarks remain private to the user.
- Personal data is never automatically converted to organization data.
- Users may voluntarily move personal resources into an organization context via the "Promote to org-shared" action.
- When a user leaves an organization, their personal account and all personal data are unaffected.

### 1.3 Data created on behalf of the organization

When a user creates a resource (shortlist, report, search) within an organization context:

- The resource's `owner_org_id` is set to the organization.
- The resource's `created_by_user_id` records who created it (audit trail).
- The organization retains the resource regardless of the creator's membership status.

---

## 2. Member responsibilities

### 2.1 Acceptable use within organizations

Organization members agree to:

- Use shared resources only for legitimate scouting, analytics, and recruitment purposes.
- Not share organization data with competitors or unauthorized third parties.
- Not attempt to access organization data they are not authorized to view (enforced by role-based access control).
- Respect the confidentiality of transfer intelligence, player valuations, and scouting assessments shared within the organization.

### 2.2 Role-based responsibilities

Each role carries specific responsibilities:

| Role | Responsibilities |
|------|-----------------|
| **Owner** | Accountable for all organization actions; manages billing; ensures compliance with these terms; may delete the organization. |
| **Manager** | Manages team composition (invite/remove/change roles); ensures shared resources are appropriate; monitors audit log. |
| **Scout** | Creates and edits scouting resources; comments on shared resources; contributes to team intelligence. |
| **Viewer** | Accesses shared resources read-only; may not create, edit, or comment. |

### 2.3 Prohibited conduct

Organization members must not:

- Share login credentials or allow non-members to access organization data.
- Use organization features to harass, defame, or target individuals.
- Attempt to access data from other organizations (cross-org data access is technically prevented and constitutes a security violation).
- Misuse the comment/mention system for spam or unauthorized communications.

---

## 3. Data deletion and cleanup

### 3.1 Member removal

When a member is removed from an organization:

- **Personal data**: Untouched. The removed member retains all personal shortlists, reports, bookmarks, and account data.
- **Resources with `personal` visibility**: Become inaccessible to the organization. The removed member retains access to these through their personal account.
- **Resources with `org_members` visibility**: Remain with the organization. The organization may reassign or delete these resources. The removed member loses access.
- **Resources with `restricted` visibility**: Governed by the `restricted_access` list. The removed member's ID is removed from the access list.
- **Comments**: The removed member's comments are preserved (audit trail) but attributed to their name/email. The organization may soft-delete comments if desired.

### 3.2 Organization deletion

When an organization owner deletes the organization:

1. **Soft-delete (30-day grace period)**: All organization data is retained but marked for deletion. Organization members are notified via email.
2. **Final deletion (after 30 days)**: All organization data, audit logs, comments, and associated metadata are permanently deleted. This action is irreversible.
3. **Personal accounts**: All organization members retain their personal Statlas accounts. Only org-affiliated data is deleted.

### 3.3 Data retention

Organization data retention is governed by the organization's `data_retention_days` setting (default: 90 days). This setting controls:

- How long soft-deleted organization data is retained before permanent purge.
- How long audit log entries are retained.
- How long removed members' contributions (comments, resource creation metadata) are retained.

The organization owner may adjust this setting (7–365 days) in organization settings.

---

## 4. Billing and seat limits

### 4.1 Organization billing

- Organizations on the **free tier** are limited to 5 members.
- **Pro organizations** support up to 25 members.
- **Enterprise organizations** support up to 100 members.
- Seat limits are enforced at invite time — invitations cannot exceed the current tier's seat limit.

### 4.2 Seat limit upgrades

- Organizations exceeding their seat limit must upgrade their tier before adding more members.
- Upgrading takes effect immediately and adjusts the seat limit.
- Downgrading requires removing excess members first.

### 4.3 Subscription responsibility

- The organization owner is responsible for the organization's subscription and billing.
- Members are not individually billed for organization membership.
- If the organization's subscription lapses, the organization is downgraded to the free tier (seat limits applied, features restricted accordingly).

---

## 5. Audit logging and compliance

### 5.1 Audit trail

When audit logging is enabled (default: on), the following events are recorded:

- Member added/removed
- Role changes
- Resource created/shared/deleted
- Comments added

Each audit entry includes: action type, performing user, target user (if applicable), resource reference, and timestamp.

### 5.2 Audit log access

- **Owners and managers** may view the organization's audit log.
- **Scouts and viewers** may not view the audit log.
- Audit log entries are append-only and cannot be modified or deleted (except on organization deletion).

### 5.3 Compliance

- Audit logging supports compliance with internal policies and external regulations that require activity trails.
- Organizations in regulated industries should enable audit logging and retain logs according to their compliance requirements.
- Audit log data is subject to the organization's data retention setting.

---

## 6. Comments and collaboration

### 6.1 Comment policy

- Comments on shared resources are visible to all organization members with access to the resource.
- Comments must comply with the acceptable use policy (§5 of the main ToS).
- Comments are attributed to the author and include timestamps.
- Soft-deleted comments preserve the audit trail but are hidden from normal views.

### 6.2 Mentions

- Users may mention teammates in comments using `@username` syntax.
- Mentions trigger in-app notifications for the mentioned user.
- Mentions are restricted to members of the same organization (cross-org mentions are not supported).

### 6.3 Intellectual property

- Comments and annotations are owned by the organization, not the individual author.
- The organization may retain, modify, or delete comments as needed.
- Individual authors may edit their own comments (the edit history is recorded).

---

## 7. Liability and indemnification

### 7.1 Organization liability

- The organization owner is responsible for the actions of organization members within the organization context.
- The organization owner ensures that members comply with these terms and the main Statlas Terms of Service.

### 7.2 Statlas liability

- Statlas provides organization features "as is" with the same disclaimers as the main service.
- Statlas is not responsible for disputes between organization members regarding data access, ownership, or usage.
- Statlas is not liable for any loss of data resulting from organization deletion or member removal.

### 7.3 Data security

- Statlas implements role-based access control to prevent cross-org data access.
- Organization data is isolated at the database level through query-layer enforcement.
- However, no system is perfectly secure — organization owners should ensure members use strong passwords and enable 2FA where required.

---

## 8. Changes to this addendum

- Changes to this addendum follow the same notice period as the main Terms of Service (14 days for material changes).
- Material changes to data ownership or deletion policies require explicit consent from the organization owner.
- Non-material clarifications may take effect immediately.

---

## 9. Governing law

This addendum is governed by the same laws and jurisdiction as the main Statlas Terms of Service.

---

## 10. Items for lawyer review

1. **Data ownership language** (§1): Confirm that "organization-owned data" is legally sound and compatible with the main ToS's IP provisions.
2. **Liability allocation** (§7): Confirm that holding the organization owner liable for member actions is appropriate in the target jurisdictions.
3. **Data deletion timelines** (§3.2): Confirm that 30-day grace periods comply with applicable data protection regulations.
4. **Cross-border considerations**: If organizations have members in different jurisdictions, confirm that data handling complies with all applicable laws.
5. **Audit log retention**: Confirm that audit log retention requirements align with compliance frameworks (SOC 2, ISO 27001, etc.) that target customers may require.
6. **Seat limit enforceability**: Confirm that billing-related seat limits are enforceable and do not create consumer-protection issues.

---

## Versioning

| Version | Date | Change |
|---------|------|--------|
| 1.0 (draft) | 2026-08-19 | Initial draft for Phase 16 organization features: data ownership, member responsibilities, data deletion, billing, audit logging, comments, liability. Requires lawyer review. |
