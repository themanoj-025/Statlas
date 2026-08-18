"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { ApiError } from "@/lib/api";

export function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email, password);
      router.push("/account");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not sign in — try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="card" style={{ padding: "var(--space-4)", marginTop: "var(--space-4)" }}>
      <div className="field">
        <label className="field__label" htmlFor="login-email">
          Email
        </label>
        <input
          id="login-email"
          className="input"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>
      <div className="field">
        <label className="field__label" htmlFor="login-password">
          Password
        </label>
        <input
          id="login-password"
          className="input"
          type="password"
          autoComplete="current-password"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>

      {error && (
        <div className="state-block state-block--error" role="alert" style={{ marginBottom: "var(--space-3)" }}>
          <p className="state-block__body">{error}</p>
        </div>
      )}

      <button type="submit" className="button" disabled={submitting} style={{ width: "100%" }}>
        {submitting ? "Signing in…" : "Sign in"}
      </button>
      <p className="field__hint" style={{ marginTop: "var(--space-3)" }}>
        <Link href="/reset-password">Forgot password?</Link>
      </p>
      <p className="field__hint">
        No account yet? <Link href="/register">Create one</Link> — it takes a few seconds and the
        free tier needs nothing else.
      </p>
    </form>
  );
}
