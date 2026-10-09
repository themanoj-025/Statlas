"""Dashboard queries — activity, recommendations, and state management.

Implementation split across:
- dashboard_activity.py: recent activity and workspace summary
- dashboard_recommendations.py: trending players and recommendations
- dashboard_state.py: state management, save/unsave, saved players
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import DashboardState

# Re-exports from the split modules (backward compatibility for
# ``from app.queries.dashboard_queries import X`` consumers, live and tests).
from app.queries.dashboard_activity import (
    get_recent_activity,
    get_workspace_summary,
)
from app.queries.dashboard_recommendations import (
    get_recommended_players,
    get_trending_players,
)
from app.queries.dashboard_state import (
    dismiss_recommendation,
    get_or_create_dashboard_state,
    get_saved_players,
    save_player,
    unsave_player,
)


def get_or_create_dashboard_state_local(db: Session, user_id: int) -> DashboardState:
    """Get or create dashboard state for a user."""
    state = db.query(DashboardState).filter(DashboardState.user_id == user_id).first()
    if state is None:
        state = DashboardState(user_id=user_id)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state
