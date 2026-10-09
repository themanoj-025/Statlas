import type { Metadata } from "next";
import { WatchlistClient } from "./WatchlistClient";

export const metadata: Metadata = {
  title: "Watchlist",
  description:
    "Your watchlist — follow players and teams and get alerted on meaningful changes: percentile jumps, club moves, new season data, and data-coverage changes.",
  alternates: { canonical: "/watchlist" },
};

export default function WatchlistPage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-lg)" }}>
      <p className="kicker">Watchlist</p>
      <h1 className="page__title">Watchlist &amp; alerts</h1>
      <p className="page__lede">
        Follow players and teams and Statlas will tell you when something actually changes —
        a percentile jump past a meaningful threshold, a club move, new season data, or a
        change in data coverage. No noise from every weekly refresh.
      </p>
      <WatchlistClient />
    </div>
  );
}
