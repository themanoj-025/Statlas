"use client";

import Link from "next/link";
import {
  Bookmark,
  FileText,
  List,
  Search,
  TrendingUp,
  UserPlus,
  X,
  Eye,
  Bell,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { api, ApiError } from "@/lib/api";
import type {
  DashboardActivityItem,
  DashboardRecommendedPlayer,
  DashboardSavedPlayer,
  DashboardSummary,
  DashboardTrendingPlayer,
  DashboardWorkspace,
} from "@/lib/types";

// ---------------------------------------------------------------------------
// Position group display names (matches the radar/leaderboard naming)
// ---------------------------------------------------------------------------

const POS_LABELS: Record<string, string> = {
  GK: "Goalkeeper",
  CB: "Centre-Back",
  FB: "Full-Back",
  DM: "Defensive Midfielder",
  CM: "Central Midfielder",
  AM: "Attacking Midfielder",
  W: "Winger",
  ST: "Striker",
};

function posLabel(code: string | null | undefined): string {
  if (!code) return "";
  return POS_LABELS[code] ?? code;
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function DashboardClient() {
  const { status } = useAuth();
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [dismissing, setDismissing] = useState<number | null>(null);
  const [unsaving, setUnsaving] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      setData(await api.dashboardSummary());
    } catch (err) {
      setLoadError(
        err instanceof ApiError ? err.message : "Could not load your dashboard.",
      );
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, attempt]);

  // --- Auth states ---

  if (status === "loading") {
    return <DashboardSkeleton />;
  }

  if (status === "signed-out") {
    return (
      <div className="state-block state-block--sunken" role="status">
        <p className="state-block__title">Your personal dashboard</p>
        <p className="state-block__body">
          Sign in to see recently viewed players, saved bookmarks, trending
          players, and personalised recommendations based on your scouting
          activity.
        </p>
        <div className="state-block__actions">
          <Link href="/login" className="button button--primary">
            Sign in
          </Link>
          <Link href="/register" className="button button--ghost">
            Create free account
          </Link>
        </div>
      </div>
    );
  }

  // --- Error state ---

  if (loadError && !data) {
    return (
      <div className="state-block state-block--error" role="alert">
        <p className="state-block__title">We couldn&rsquo;t load your dashboard.</p>
        <p className="state-block__body">{loadError}</p>
        <div className="state-block__actions">
          <button
            type="button"
            className="button button--primary"
            onClick={() => setAttempt((a) => a + 1)}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) return <DashboardSkeleton />;

  const { recent_activity, workspace, trending_players, recommended_players, saved_players, transfer_opportunities } =
    data;

  return (
    <div className="dashboard">
      <h1 className="dashboard__title">Dashboard</h1>

      {/* ---- Workspace shortcuts ---- */}
      <section className="dashboard__section" aria-label="Workspace shortcuts">
        <h2 className="dashboard__section-title">Your workspace</h2>
        <div className="dashboard__shortcuts">
          <ShortcutCard
            icon={<List size={20} />}
            label="Shortlists"
            count={workspace.shortlist_count}
            href="/workspace"
          />
          <ShortcutCard
            icon={<Search size={20} />}
            label="Saved searches"
            count={workspace.saved_search_count}
            href="/search"
          />
          <ShortcutCard
            icon={<FileText size={20} />}
            label="Reports"
            count={workspace.report_count}
            href="/reports"
          />
          <ShortcutCard
            icon={<Bell size={20} />}
            label="Watchlist"
            count={workspace.watch_count}
            href="/watchlist"
            badge={workspace.unread_alert_count > 0 ? workspace.unread_alert_count : undefined}
          />
        </div>
      </section>

      <div className="dashboard__columns">
        {/* ---- Left column: recent + trending ---- */}
        <div className="dashboard__main">
          {/* Recently viewed */}
          <section className="dashboard__section" aria-label="Recently viewed players">
            <h2 className="dashboard__section-title">Recently viewed</h2>
            {recent_activity.length === 0 ? (
              <EmptyState message="Recently viewed players will appear here as you explore player profiles." />
            ) : (
              <ul className="dashboard__player-list" role="list">
                {recent_activity.map((item) => (
                  <PlayerRow
                    key={`${item.entity_type}-${item.entity_id}`}
                    playerId={item.entity_id}
                    name={item.player_name ?? `Player #${item.entity_id}`}
                    team={item.team_name}
                    position={item.position_group}
                    meta={item.action_type === "viewed" ? "Viewed" : item.action_type}
                  />
                ))}
              </ul>
            )}
          </section>

          {/* Trending players */}
          <section className="dashboard__section" aria-label="Trending players">
            <h2 className="dashboard__section-title">
              <TrendingUp size={18} className="dashboard__icon" />
              Trending this week
            </h2>
            {trending_players.length === 0 ? (
              <EmptyState message="Trending players will appear here based on sustained percentile gains across the latest data refresh." />
            ) : (
              <ul className="dashboard__player-list" role="list">
                {trending_players.map((p) => (
                  <TrendingRow key={p.player_id} player={p} />
                ))}
              </ul>
            )}
          </section>
        </div>

        {/* ---- Right column: saved + recommended ---- */}
        <div className="dashboard__side">
          {/* Saved players */}
          <section className="dashboard__section" aria-label="Saved players">
            <h2 className="dashboard__section-title">
              <Bookmark size={18} className="dashboard__icon" />
              Saved players
            </h2>
            {saved_players.length === 0 ? (
              <EmptyState message="Bookmark players from their profile pages to see them here." />
            ) : (
              <ul className="dashboard__player-list" role="list">
                {saved_players.map((p) => (
                  <SavedRow
                    key={p.player_id}
                    player={p}
                    onUnsave={async () => {
                      setUnsaving(p.player_id);
                      try {
                        await api.unsavePlayer(p.player_id);
                        setAttempt((a) => a + 1);
                      } finally {
                        setUnsaving(null);
                      }
                    }}
                    unsaving={unsaving === p.player_id}
                  />
                ))}
              </ul>
            )}
          </section>

          {/* Recommended players */}
          <section className="dashboard__section" aria-label="Recommended for you">
            <h2 className="dashboard__section-title">
              <UserPlus size={18} className="dashboard__icon" />
              Recommended for you
            </h2>
            {recommended_players.length === 0 ? (
              <EmptyState message="Recommended players will appear based on your interests as you browse." />
            ) : (
              <ul className="dashboard__player-list" role="list">
                {recommended_players.map((p) => (
                  <RecommendedRow
                    key={p.player_id}
                    player={p}
                    onDismiss={async () => {
                      setDismissing(p.player_id);
                      try {
                        await api.dismissRecommendation(p.player_id);
                        setAttempt((a) => a + 1);
                      } finally {
                        setDismissing(null);
                      }
                    }}
                    dismissing={dismissing === p.player_id}
                  />
                ))}
              </ul>
            )}
          </section>

          {/* Transfer opportunities */}
          {transfer_opportunities.length > 0 && (
            <section className="dashboard__section" aria-label="Transfer opportunities">
              <h2 className="dashboard__section-title">
                <TrendingUp size={18} className="dashboard__icon" />
                Transfer opportunities
              </h2>
              <ul className="dashboard__player-list" role="list">
                {transfer_opportunities.map((opp) => (
                  <li key={opp.player_id} className="dashboard__player-row">
                    <Link href={`/players/${opp.player_id}`} className="dashboard__player-link">
                      <span className="dashboard__player-name">{opp.name}</span>
                      <span className="dashboard__player-meta">
                        {opp.position_group && (
                          <span className="dashboard__player-pos">{posLabel(opp.position_group)}</span>
                        )}
                        {opp.club && <span className="dashboard__player-team">{opp.club}</span>}
                        <span className="dashboard__recommendation-why">
                          {opp.opportunity_summary}
                        </span>
                      </span>
                    </Link>
                    {opp.upside_eur > 0 && (
                      <span className="dashboard__trending-gain" aria-label={`Upside €${(opp.upside_eur / 1e6).toFixed(1)}M`}>
                        +€{(opp.upside_eur / 1e6).toFixed(1)}M
                      </span>
                    )}
                  </li>
                ))}
              </ul>
              <Link href="/transfers/opportunities?type=hidden-gems" style={{ fontSize: "0.85rem" }}>
                View all opportunities →
              </Link>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ShortcutCard({
  icon,
  label,
  count,
  href,
  badge,
}: {
  icon: React.ReactNode;
  label: string;
  count: number;
  href: string;
  badge?: number;
}) {
  return (
    <Link href={href} className="dashboard__shortcut-card">
      <span className="dashboard__shortcut-icon">{icon}</span>
      <span className="dashboard__shortcut-label">{label}</span>
      <span className="dashboard__shortcut-count">
        {count}
        {badge !== undefined && (
          <span className="dashboard__shortcut-badge" aria-label={`${badge} unread`}>
            {badge}
          </span>
        )}
      </span>
    </Link>
  );
}

function PlayerRow({
  playerId,
  name,
  team,
  position,
  meta,
}: {
  playerId: number;
  name: string;
  team?: string | null;
  position?: string;
  meta: string;
}) {
  return (
    <li className="dashboard__player-row">
      <Link href={`/players/${encodeURIComponent(name.toLowerCase().replace(/\s+/g, "-"))}`} className="dashboard__player-link">
        <span className="dashboard__player-name">{name}</span>
        <span className="dashboard__player-meta">
          {position && <span className="dashboard__player-pos">{posLabel(position)}</span>}
          {team && <span className="dashboard__player-team">{team}</span>}
        </span>
      </Link>
      <span className="dashboard__player-action">{meta}</span>
    </li>
  );
}

function TrendingRow({ player }: { player: DashboardTrendingPlayer }) {
  return (
    <li className="dashboard__player-row">
      <Link href={`/players/${encodeURIComponent(player.player_name.toLowerCase().replace(/\s+/g, "-"))}`} className="dashboard__player-link">
        <span className="dashboard__player-name">{player.player_name}</span>
        <span className="dashboard__player-meta">
          {player.position_group && (
            <span className="dashboard__player-pos">{posLabel(player.position_group)}</span>
          )}
          {player.team_name && <span className="dashboard__player-team">{player.team_name}</span>}
        </span>
      </Link>
      <span className="dashboard__trending-gain" aria-label={`Average gain ${player.avg_gain} percentile points`}>
        +{player.avg_gain} pts
      </span>
    </li>
  );
}

function SavedRow({
  player,
  onUnsave,
  unsaving,
}: {
  player: DashboardSavedPlayer;
  onUnsave: () => void;
  unsaving: boolean;
}) {
  return (
    <li className="dashboard__player-row">
      <Link href={`/players/${encodeURIComponent(player.player_name.toLowerCase().replace(/\s+/g, "-"))}`} className="dashboard__player-link">
        <span className="dashboard__player-name">{player.player_name}</span>
        <span className="dashboard__player-meta">
          {player.position_group && (
            <span className="dashboard__player-pos">{posLabel(player.position_group)}</span>
          )}
          {player.team_name && <span className="dashboard__player-team">{player.team_name}</span>}
        </span>
      </Link>
      <button
        type="button"
        className="button button--sm button--ghost"
        aria-label={`Remove ${player.player_name} from saved`}
        onClick={onUnsave}
        disabled={unsaving}
      >
        <X size={14} />
      </button>
    </li>
  );
}

function RecommendedRow({
  player,
  onDismiss,
  dismissing,
}: {
  player: DashboardRecommendedPlayer;
  onDismiss: () => void;
  dismissing: boolean;
}) {
  return (
    <li className="dashboard__player-row dashboard__player-row--recommended">
      <Link href={`/players/${encodeURIComponent(player.player_name.toLowerCase().replace(/\s+/g, "-"))}`} className="dashboard__player-link">
        <span className="dashboard__player-name">{player.player_name}</span>
        <span className="dashboard__player-meta">
          {player.position_group && (
            <span className="dashboard__player-pos">{posLabel(player.position_group)}</span>
          )}
          {player.team_name && <span className="dashboard__player-team">{player.team_name}</span>}
        </span>
        <span className="dashboard__recommendation-why">{player.explanation}</span>
      </Link>
      <button
        type="button"
        className="button button--sm button--ghost"
        aria-label={`Dismiss recommendation for ${player.player_name}`}
        onClick={onDismiss}
        disabled={dismissing}
      >
        <X size={14} />
      </button>
    </li>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <p className="dashboard__empty">{message}</p>
  );
}

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

function DashboardSkeleton() {
  return (
    <div className="dashboard" aria-busy="true" aria-label="Loading dashboard">
      <div className="dashboard__title skeleton skeleton--text" />
      <div className="dashboard__shortcuts">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="dashboard__shortcut-card skeleton skeleton--block" />
        ))}
      </div>
      <div className="dashboard__columns">
        <div className="dashboard__main">
          <div className="dashboard__section">
            <div className="skeleton skeleton--text" style={{ width: 180, height: 20, marginBottom: 12 }} />
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="skeleton skeleton--text" style={{ height: 40, marginBottom: 8 }} />
            ))}
          </div>
        </div>
        <div className="dashboard__side">
          <div className="dashboard__section">
            <div className="skeleton skeleton--text" style={{ width: 160, height: 20, marginBottom: 12 }} />
            {Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="skeleton skeleton--text" style={{ height: 40, marginBottom: 8 }} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
