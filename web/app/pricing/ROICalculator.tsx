"use client";

import { useState } from "react";

export function ROICalculator() {
  const [teamSize, setTeamSize] = useState(5);
  const timeSavedPerWeek = teamSize * 2; // 2 hours per scout per week
  const annualHours = timeSavedPerWeek * 52;
  const costPerHour = 50; // Average scout hour cost
  const annualSavings = annualHours * costPerHour;

  return (
    <div
      className="card"
      style={{
        padding: "var(--space-6)",
        background: "var(--color-surface-raised)",
        border: "1px solid var(--color-border)",
      }}
    >
      <h3 style={{ fontSize: "var(--text-lg)", marginBottom: "var(--space-4)" }}>
        Calculate your savings
      </h3>

      <div style={{ marginBottom: "var(--space-4)" }}>
        <label
          style={{
            display: "block",
            fontSize: "var(--text-sm)",
            fontWeight: 500,
            marginBottom: "var(--space-2)",
          }}
          htmlFor="team-size"
        >
          Team size:{" "}
          <span className="num" style={{ fontWeight: 700, color: "var(--color-primary)" }}>
            {teamSize}
          </span>{" "}
          {teamSize === 1 ? "scout" : "scouts"}
        </label>
        <input
          id="team-size"
          type="range"
          min="1"
          max="50"
          value={teamSize}
          onChange={(e) => setTeamSize(parseInt(e.target.value))}
          style={{ width: "100%" }}
          aria-label="Team size"
        />
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: "var(--text-xs)",
            color: "var(--color-text-muted)",
          }}
        >
          <span>1</span>
          <span>50</span>
        </div>
      </div>

      <div
        className="grid"
        style={{
          marginBottom: "var(--space-4)",
          gridTemplateColumns: "repeat(3, 1fr)",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div
            className="num"
            style={{
              fontSize: "var(--text-2xl)",
              fontWeight: 700,
              color: "var(--color-primary)",
            }}
          >
            {timeSavedPerWeek}
          </div>
          <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", margin: 0 }}>
            hours saved/week
          </p>
        </div>
        <div style={{ textAlign: "center" }}>
          <div
            className="num"
            style={{
              fontSize: "var(--text-2xl)",
              fontWeight: 700,
              color: "var(--color-primary)",
            }}
          >
            {annualHours.toLocaleString()}
          </div>
          <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", margin: 0 }}>
            hours saved/year
          </p>
        </div>
        <div style={{ textAlign: "center" }}>
          <div
            className="num"
            style={{
              fontSize: "var(--text-2xl)",
              fontWeight: 700,
              color: "var(--color-primary)",
            }}
          >
            &euro;{annualSavings.toLocaleString()}
          </div>
          <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", margin: 0 }}>
            annual savings
          </p>
        </div>
      </div>

      <p
        style={{
          fontSize: "var(--text-xs)",
          color: "var(--color-text-muted)",
          textAlign: "center",
          margin: 0,
        }}
      >
        Based on {teamSize} {teamSize === 1 ? "scout" : "scouts"} saving ~2 hours/week with
        Statlas. Actual savings depend on usage patterns.
      </p>
    </div>
  );
}
