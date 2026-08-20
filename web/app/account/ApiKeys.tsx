"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";

type KeyRow = {
  id: number;
  name: string;
  prefix: string;
  created_at: string | null;
  last_used_at: string | null;
  revoked: boolean;
};

type KeysPayload = { keys: KeyRow[] };
type CreatePayload = { key: string; prefix: string; name: string };

const API_URL =
  typeof window === "undefined"
    ? (process.env.STATLAS_API_URL ?? "http://127.0.0.1:8000")
    : (process.env.NEXT_PUBLIC_STATLAS_API_URL ?? "http://127.0.0.1:8000");

function parseError(res: { status: number }, body: Record<string, unknown>): string {
  if (typeof body.detail === "string") return body.detail;
  const err = body.error;
  if (err && typeof err === "object" && typeof (err as Record<string, unknown>).message === "string") {
    return (err as Record<string, string>).message;
  }
  return `API ${res.status}`;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { credentials: "include", cache: "no-store" });
  if (!res.ok) {
    let detail = `API ${res.status}`;
    try {
      detail = parseError(res, await res.json());
    } catch {
      /* non-JSON */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    credentials: "include",
    cache: "no-store",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = `API ${res.status}`;
    try {
      detail = parseError(res, await res.json());
    } catch {
      /* non-JSON */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { method: "DELETE", credentials: "include", cache: "no-store" });
  if (!res.ok) {
    let detail = `API ${res.status}`;
    try {
      detail = parseError(res, await res.json());
    } catch {
      /* non-JSON */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return {} as T;
  return res.json() as Promise<T>;
}

export function ApiKeys() {
  const [keys, setKeys] = useState<KeyRow[]>([]);
  const [name, setName] = useState("");
  const [revealed, setRevealed] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    get<KeysPayload>("/api/v1/keys")
      .then((p) => setKeys(p.keys))
      .catch(() => setKeys([]));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const create = async () => {
    setBusy(true);
    setError(null);
    try {
      const created = await post<CreatePayload>("/api/v1/keys", { name: name.trim() || "default" });
      setRevealed(created.key); // one-time reveal
      setName("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create the key.");
    } finally {
      setBusy(false);
    }
  };

  const revoke = async (id: number) => {
    setBusy(true);
    setError(null);
    try {
      await del(`/api/v1/keys/${id}`);
      setRevealed(null);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not revoke the key.");
    } finally {
      setBusy(false);
    }
  };

  const rotate = async (id: number) => {
    setBusy(true);
    setError(null);
    try {
      const created = await post<CreatePayload>(`/api/v1/keys/${id}/rotate`, {});
      setRevealed(created.key);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not rotate the key.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card" aria-label="API keys" style={{ display: "grid", gap: "var(--space-3)" }}>
      <div className="section-head" style={{ marginTop: 0 }}>
        <h2 className="card__title" style={{ margin: 0 }}>
          API keys
        </h2>
        <span className="chip">Public API · v1</span>
      </div>

      <p className="field__hint" style={{ margin: 0 }}>
        Keys authenticate requests to <code>/api/v1/public/…</code>. Send them as{" "}
        <code>Authorization: Bearer &lt;key&gt;</code>. The full key is shown <strong>once</strong>{" "}
        at creation — after that only its prefix is stored (hashed), so treat it like a password.
      </p>

      {revealed && (
        <div className="state-block state-block--sunken" role="status">
          <p className="state-block__title">Your new key — shown once</p>
          <p className="state-block__body">
            <code style={{ userSelect: "all", wordBreak: "break-all" }}>{revealed}</code>
          </p>
          <p className="field__hint" style={{ margin: 0 }}>
            Copy it now. Statlas stores only a hash of this key and cannot show it again.
          </p>
        </div>
      )}

      {error && (
        <div className="state-block state-block--error" role="alert">
          <p className="state-block__body">{error}</p>
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void create();
        }}
        style={{ display: "flex", gap: "var(--space-2)" }}
      >
        <label htmlFor="key-name" className="visually-hidden">
          Key name
        </label>
        <input
          id="key-name"
          className="input"
          placeholder="e.g. scouting-pipeline"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={busy}
          style={{ flex: 1 }}
        />
        <button type="submit" className="button" disabled={busy}>
          Create key
        </button>
      </form>

      {keys.length === 0 ? (
        <p className="field__hint" style={{ margin: 0 }}>
          No keys yet — create one to start calling the public API.
        </p>
      ) : (
        <div className="table-wrap">
          <table className="table" aria-label="Your API keys">
            <thead>
              <tr>
                <th scope="col">Name</th>
                <th scope="col">Prefix</th>
                <th scope="col">Created</th>
                <th scope="col">Last used</th>
                <th scope="col">Status</th>
                <th scope="col">
                  <span className="visually-hidden">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {keys.map((k) => (
                <tr key={k.id}>
                  <td>{k.name}</td>
                  <td>
                    <code>{k.prefix}…</code>
                  </td>
                  <td>{k.created_at ? new Date(k.created_at).toLocaleDateString() : "—"}</td>
                  <td>{k.last_used_at ? new Date(k.last_used_at).toLocaleString() : "never"}</td>
                  <td>{k.revoked ? "revoked" : "active"}</td>
                  <td>
                    {!k.revoked && (
                      <>
                        <button type="button" className="button button--sm button--secondary" onClick={() => void rotate(k.id)} disabled={busy}>
                          Rotate
                        </button>{" "}
                        <button type="button" className="button button--sm button--secondary" onClick={() => void revoke(k.id)} disabled={busy}>
                          Revoke
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
