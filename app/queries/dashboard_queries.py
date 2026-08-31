"""Dashboard queries — activity, recommendations, and state management.

Implementation split across:
- dashboard_activity.py: recent activity and workspace summary
- dashboard_recommendations.py: trending players and recommendations
- dashboard_state.py: state management, save/unsave, saved players
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import DashboardState

# Re-export from split modules
from app.queries.dashboard_activity import (  # noqa: F401, E402
    get_recent_activity,
    get_workspace_summary,
)
from app.queries.dashboard_recommendations import (  # noqa: F401, E402
    get_trending_players,
    get_recommended_players,
)
from app.queries.dashboard_state import (  # noqa: F401, E402
    get_or_create_dashboard_state,
    dismiss_recommendation,
    get_top_viewed_positions,
    save_player,
    unsave_player,
    get_saved_players,
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
