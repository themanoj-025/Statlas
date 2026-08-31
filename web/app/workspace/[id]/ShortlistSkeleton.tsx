/** Shortlist loading skeleton. */

'use client'

import React from 'react'

function ShortlistSkeleton() {
  return (
    <div role="status" aria-label="Loading this shortlist" style={{ display: "grid", gap: "var(--space-3)", marginTop: "var(--space-3)" }}>
      <span className="skeleton" style={{ display: "block", width: 180, height: 26 }} />
      <div className="table-wrap" aria-hidden="true">
        <table className="table">
          <tbody>
            {Array.from({ length: 4 }, (_, i) => (
              <tr key={i}>
                {Array.from({ length: 6 }, (_, j) => (
                  <td key={j}>
                    <span className="skeleton" style={{ display: "inline-block", width: j === 0 ? 140 : 70, height: 14 }} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
