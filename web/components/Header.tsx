"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Menu, X } from "lucide-react";
import { useAuth } from "./AuthProvider";
import { NotificationBell } from "./NotificationBell";
import { SearchCombobox } from "./SearchCombobox";
import { ThemeToggle } from "./ThemeToggle";

const NAV_ITEMS = [
  { href: "/positions", label: "Leaderboards" },
  { href: "/archetypes", label: "Archetypes" },
  { href: "/leagues", label: "Leagues" },
  { href: "/search", label: "Search" },
  { href: "/compare", label: "Compare" },
  { href: "/trend", label: "Trend" },
  { href: "/methodology", label: "Methodology" },
  { href: "/pricing", label: "Pricing" },
  { href: "/data-coverage", label: "Data coverage" },
];

export function Header() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const { status, user } = useAuth();

  // Embed pages are bare iframe targets (Phase 3 C3): no site chrome.
  if (pathname.startsWith("/embed/")) return null;

  return (
    <header className="site-header no-print">
      <div className="container container--xl site-header__inner">
        <Link href="/" className="brand" aria-label="Statlas — home">
          <span className="brand__mark" aria-hidden="true" />
          <span>
            Stat<span className="brand__name">las</span>
          </span>
        </Link>

        <nav className="site-nav" aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              aria-current={pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href)) ? "page" : undefined}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="site-header__actions">
          {status === "signed-in" ? (
            <>
              <Link href="/dashboard" className="header-account">
                Dashboard
              </Link>
              <Link href="/workspace" className="header-account">
                Workspace
              </Link>
              <Link href="/watchlist" className="header-account">
                Watchlist
              </Link>
              <Link href="/reports" className="header-account">
                Reports
              </Link>
              <Link href="/account" className="header-account" aria-label={`Account — ${user?.email ?? ""}`}>
                Account
              </Link>
              <NotificationBell />
            </>
          ) : status === "signed-out" ? (
            <Link href="/login" className="header-account">
              Sign in
            </Link>
          ) : null}
          <SearchCombobox />
          <ThemeToggle />
          <button
            type="button"
            className="nav-toggle"
            aria-expanded={menuOpen}
            aria-controls="mobile-menu"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? <X size={20} aria-hidden="true" /> : <Menu size={20} aria-hidden="true" />}
          </button>
        </div>
      </div>

      <div id="mobile-menu" className={`mobile-menu ${menuOpen ? "mobile-menu--open" : ""}`}>
        {NAV_ITEMS.map((item) => (
          <Link key={item.href} href={item.href} onClick={() => setMenuOpen(false)}>
            {item.label}
          </Link>
        ))}
        {status === "signed-in" && (
          <>
            <Link href="/workspace" onClick={() => setMenuOpen(false)}>
              Workspace
            </Link>
            <Link href="/watchlist" onClick={() => setMenuOpen(false)}>
              Watchlist
            </Link>
            <Link href="/reports" onClick={() => setMenuOpen(false)}>
              Reports
            </Link>
          </>
        )}
        <Link href={status === "signed-in" ? "/account" : "/login"} onClick={() => setMenuOpen(false)}>
          {status === "signed-in" ? "Account" : "Sign in"}
        </Link>
      </div>
    </header>
  );
}
