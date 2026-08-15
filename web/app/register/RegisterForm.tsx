"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { ApiError } from "@/lib/api";

export function RegisterForm() {
  const { register } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      setError("Passwords must be at least 8 characters.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await register(email, password);
      router.push("/account");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create the account — try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="card" style={{ padding: "var(--space-4)", marginTop: "var(--space-4)" }}>
      <div className="field">
        <label className="field__label" htmlFor="reg-email">
          Email
        </label>
        <input
          id="reg-email"
          className="input"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>
      <div className="field">
        <label className="field__label" htmlFor="reg-password">
          Password
        </label>
        <input
          id="reg-password"
          className="input"
          type="password"
          autoComplete="new-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <p className="field__hint">At least 8 characters. Stored as a salted hash — never plaintext.</p>
      </div>

      {error && (
        <div className="state-block state-block--error" role="alert" style={{ marginBottom: "var(--space-3)" }}>
          <p className="state-block__body">{error}</p>
        </div>
      )}

      <button type="submit" className="button" disabled={submitting} style={{ width: "100%" }}>
        {submitting ? "Creating account…" : "Create account"}
      </button>
      <p className="field__hint" style={{ marginTop: "var(--space-3)" }}>
        Already have an account? <Link href="/login">Sign in</Link>
      </p>
    </form>
  );
}
