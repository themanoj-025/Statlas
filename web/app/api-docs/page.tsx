import type { Metadata } from "next";
import Link from "next/link";
import { api } from "@/lib/api";

export const metadata: Metadata = {
  title: "API documentation",
  description:
    "The Statlas public API — versioned, key-authenticated, rate-limited. Generated from the live OpenAPI spec.",
  alternates: { canonical: "/api-docs" },
};

/**
 * API docs (Phase 4 — Part C2). The spec is generated from the actual
 * implementation (FastAPI /openapi.json) — never hand-written and drifting.
 * This page renders the endpoint list + links to the interactive docs.
 */
export default async function ApiDocsPage() {
  let spec: { paths?: Record<string, unknown>; info?: { version?: string } } = {};
  let specError = false;
  try {
    spec = await api.openapi();
  } catch {
    specError = true;
  }

  const paths = spec.paths ?? {};
  const endpoints = Object.entries(paths).filter(([path]) => path.startsWith("/api/v1/public"));

  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <p className="kicker">Developers</p>
      <h1 className="page__title">Public API</h1>
      <p className="page__lede">
        Versioned, key-authenticated, rate-limited read access to Statlas player data. The
        documentation below is generated from the live OpenAPI spec — it cannot drift from the
        implementation.
      </p>

      <section className="card" style={{ display: "grid", gap: "var(--space-3)" }}>
        <h2 className="card__title" style={{ margin: 0 }}>
          Getting started
        </h2>
        <ol style={{ margin: 0, paddingLeft: "var(--space-4)", display: "grid", gap: "var(--space-2)" }}>
          <li>
            Create an API key in your <Link href="/account">account dashboard</Link> (requires a
            signed-in account; the key is shown once and stored only as a hash).
          </li>
          <li>
            Authenticate with <code>Authorization: Bearer &lt;key&gt;</code>.
          </li>
          <li>
            Read the rate-limit headers on every response: <code>X-RateLimit-Limit</code>,{" "}
            <code>X-RateLimit-Remaining</code>, <code>X-RateLimit-Window</code>.
          </li>
        </ol>
        <pre className="assistant-tool-result" style={{ overflowX: "auto", margin: 0 }}>
          {`curl -H "Authorization: Bearer sl_xxx.yyy" \\\n  "https://api.statlas.com/api/v1/public/players/1/percentiles"`}
        </pre>
        <p className="field__hint" style={{ margin: 0 }}>
          The public API is included in the API Business tier. The interactive spec and the full
          OpenAPI document are served by the API itself at <code>/docs</code> and{" "}
          <code>/openapi.json</code>.
        </p>
      </section>

      {specError ? (
        <div className="state-block state-block--error" role="alert">
          <p className="state-block__body">
            Could not fetch the OpenAPI spec from the API — the API may be offline.
          </p>
        </div>
      ) : (
        <section className="card" aria-label="Public API endpoints" style={{ display: "grid", gap: "var(--space-2)" }}>
          <h2 className="card__title" style={{ margin: 0 }}>
            Endpoints (from the live spec)
          </h2>
          {endpoints.length === 0 ? (
            <p className="field__hint" style={{ margin: 0 }}>
              No public endpoints exposed on this deployment.
            </p>
          ) : (
            <table className="table" aria-label="Public API endpoints">
              <thead>
                <tr>
                  <th scope="col">Method</th>
                  <th scope="col">Path</th>
                </tr>
              </thead>
              <tbody>
                {endpoints.map(([path, methods]) =>
                  Object.keys(methods as Record<string, unknown>).map((method) => (
                    <tr key={`${method}-${path}`}>
                      <td>
                        <code>{method.toUpperCase()}</code>
                      </td>
                      <td>
                        <code>{path}</code>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </section>
      )}
    </div>
  );
}
