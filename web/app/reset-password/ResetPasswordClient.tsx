"use client";

import { useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";

export function ResetPasswordClient() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  // If token is present, show the confirm form; otherwise show the request form.
  if (token) {
    return <ConfirmForm token={token} />;
  }
  return <RequestForm />;
}

function RequestForm() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setMsg(null);
    setError(null);
    try {
      const res = await api.requestPasswordReset(email);
      setMsg(res.detail);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not send reset link.");
    }
    setSubmitting(false);
  };

  return (
    <form onSubmit={submit} className="card" style={{ padding: "var(--space-4)", marginTop: "var(--space-4)" }}>
      <div className="field">
        <label className="field__label" htmlFor="reset-email">
          Email address
        </label>
        <input
          id="reset-email"
          className="input"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>

      {msg && (
        <div className="state-block state-block--sunken" role="status" style={{ marginBottom: "var(--space-3)" }}>
          <p className="state-block__body">{msg}</p>
        </div>
      )}

      {error && (
        <div className="state-block state-block--error" role="alert" style={{ marginBottom: "var(--space-3)" }}>
          <p className="state-block__body">{error}</p>
        </div>
      )}

      <button type="submit" className="button" disabled={submitting} style={{ width: "100%" }}>
        {submitting ? "Sending…" : "Send reset link"}
      </button>

      <p className="field__hint" style={{ marginTop: "var(--space-3)" }}>
        Remember your password? <Link href="/login">Sign in</Link>.
      </p>
    </form>
  );
}

function ConfirmForm({ token }: { token: string }) {
  const [newPassword, setNewPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setMsg(null);
    setError(null);
    try {
      const res = await api.confirmPasswordReset(token, newPassword);
      setMsg(res.detail);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reset password.");
    }
    setSubmitting(false);
  };

  if (msg) {
    return (
      <div className="card" style={{ padding: "var(--space-4)", marginTop: "var(--space-4)" }}>
        <div className="state-block state-block--sunken" role="status">
          <p className="state-block__body">{msg}</p>
        </div>
        <p className="field__hint" style={{ marginTop: "var(--space-3)" }}>
          <Link href="/login">Sign in with your new password</Link>.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="card" style={{ padding: "var(--space-4)", marginTop: "var(--space-4)" }}>
      <div className="field">
        <label className="field__label" htmlFor="new-password">
          New password (min 8 chars, upper + lower + digit)
        </label>
        <input
          id="new-password"
          className="input"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
        />
      </div>

      {error && (
        <div className="state-block state-block--error" role="alert" style={{ marginBottom: "var(--space-3)" }}>
          <p className="state-block__body">{error}</p>
        </div>
      )}

      <button type="submit" className="button" disabled={submitting || newPassword.length < 8} style={{ width: "100%" }}>
        {submitting ? "Resetting…" : "Reset password"}
      </button>
    </form>
  );
}
