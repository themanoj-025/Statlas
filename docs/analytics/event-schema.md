# Phase 18 — Event Schema

Every tracked event has: name, trigger, required properties, and a rationale
explaining why it's tracked. This is the single source of truth for what
Statlas observes about user behavior.

---

## Authentication Events

### `user_login`
- **Trigger:** User successfully authenticates (email/password, OAuth)
- **Properties:** `user_id`, `user_tier`, `signup_date`, `session_id`
- **Why tracked:** Daily active users and tier breakdown

### `user_signup`
- **Trigger:** New user account created
- **Properties:** `user_id`, `signup_source` (organic/campaign/email), `tier`
- **Why tracked:** Acquisition funnel and source attribution

### `user_logout`
- **Trigger:** User explicitly logs out
- **Properties:** `user_id`, `session_id`
- **Why tracked:** Session end marker, session duration calculation

---

## Feature Usage Events

### `feature_viewed`
- **Trigger:** User navigates to a major feature page
- **Properties:** `user_id`, `feature_name`, `time_on_page_seconds`
- **Why tracked:** Feature discovery and engagement depth

### `feature_created`
- **Trigger:** User creates a new resource (shortlist, report, saved search, watch)
- **Properties:** `user_id`, `feature_name`, `is_org_shared`
- **Why tracked:** Active creation vs passive consumption ratio

### `feature_shared`
- **Trigger:** User shares a resource with org or makes it public
- **Properties:** `user_id`, `feature_name`, `shared_with_org_size`
- **Why tracked:** Collaboration and virality signals

### `feature_deleted`
- **Trigger:** User deletes a resource they created
- **Properties:** `user_id`, `feature_name`, `resource_age_days`
- **Why tracked:** Feature satisfaction inverse signal

---

## Search Events

### `search_executed`
- **Trigger:** User runs a Phase 8 multi-condition search
- **Properties:** `user_id`, `num_conditions`, `result_count`, `template_name`
- **Why tracked:** Search feature usage, complexity, and effectiveness

### `search_saved`
- **Trigger:** User saves a search for reuse
- **Properties:** `user_id`, `num_conditions`, `is_org_shared`
- **Why tracked:** Power user signal, search-to-workflow conversion

---

## Transfer Intelligence Events

### `valuation_compared`
- **Trigger:** User views valuation comparison for a player
- **Properties:** `user_id`, `player_id`, `gap_direction` (undervalued/overvalued)
- **Why tracked:** Transfer intelligence feature engagement

### `transfer_candidate_viewed`
- **Trigger:** User views a transfer candidate result
- **Properties:** `user_id`, `template_name`, `result_count`
- **Why tracked:** Transfer candidate discovery usage

### `opportunity_viewed`
- **Trigger:** User views a hidden-gem or age-opportunity card
- **Properties:** `user_id`, `opportunity_type`, `player_id`
- **Why tracked:** Opportunity finder feature adoption

---

## Subscription Events

### `subscription_created`
- **Trigger:** User subscribes to Pro tier
- **Properties:** `user_id`, `subscription_tier`, `source`, `mrr_contribution`
- **Why tracked:** Conversion funnel and revenue attribution

### `subscription_canceled`
- **Trigger:** User cancels subscription
- **Properties:** `user_id`, `subscription_duration_days`, `reason`
- **Why tracked:** Churn analysis and retention issues

### `subscription_renewed`
- **Trigger:** Subscription auto-renews
- **Properties:** `user_id`, `subscription_tier`, `duration_months`
- **Why tracked:** Retention and LTV calculation

### `upgrade_attempted`
- **Trigger:** User clicks upgrade / hits paywall
- **Properties:** `user_id`, `triggering_feature`, `current_tier`
- **Why tracked:** Upgrade funnel — where users discover they need Pro

### `upgrade_completed`
- **Trigger:** Payment succeeds, tier upgraded
- **Properties:** `user_id`, `subscription_tier`, `amount_eur`
- **Why tracked:** Conversion completion

---

## Organization Events

### `org_created`
- **Trigger:** User creates a new organization
- **Properties:** `user_id`, `org_name`, `org_tier`
- **Why tracked:** Team adoption and growth

### `org_member_invited`
- **Trigger:** Org owner/manager invites a new member
- **Properties:** `user_id`, `org_id`, `role_invited`, `seat_utilization`
- **Why tracked:** Collaboration activation

### `org_member_joined`
- **Trigger:** Invited user accepts and joins
- **Properties:** `user_id`, `org_id`, `role`, `invitation_age_days`
- **Why tracked:** Invite-to-join conversion

---

## Error Events

### `error_occurred`
- **Trigger:** Backend error or user-facing error message
- **Properties:** `error_type`, `error_message`, `user_id`, `feature_context`, `endpoint`
- **Why tracked:** Broken features prioritization

---

## Tactical Analysis Events

### `tactical_analysis_viewed`
- **Trigger:** User views passing network, pressure map, or formation analysis
- **Properties:** `user_id`, `analysis_type`, `match_id`, `team_id`
- **Why tracked:** Tactical intelligence feature adoption

---

## Dashboard Events

### `dashboard_viewed`
- **Trigger:** User loads the personal dashboard
- **Properties:** `user_id`, `session_id`, `widgets_rendered`
- **Why tracked:** Dashboard engagement and widget popularity

### `widget_interacted`
- **Trigger:** User clicks/expands a dashboard widget
- **Properties:** `user_id`, `widget_name`, `action` (view/dismiss/click)
- **Why tracked:** Widget relevance and satisfaction

---

## Report Events

### `report_generated`
- **Trigger:** User generates an AI scouting report
- **Properties:** `user_id`, `player_id`, `report_type`, `generation_time_ms`
- **Why tracked:** AI feature usage and performance

### `report_exported`
- **Trigger:** User exports report (PDF/JSON/CSV)
- **Properties:** `user_id`, `report_id`, `export_format`
- **Why tracked:** Report utility and sharing behavior

---

## Watchlist Events

### `alert_triggered`
- **Trigger:** A watchlist alert fires
- **Properties:** `user_id`, `watch_id`, `alert_type`, `player_id`
- **Why tracked:** Alert system effectiveness

### `alert_dismissed`
- **Trigger:** User dismisses/clears an alert
- **Properties:** `user_id`, `alert_id`, `time_to_dismiss_seconds`
- **Why tracked:** Alert relevance and urgency
