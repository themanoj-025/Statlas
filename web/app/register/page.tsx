import type { Metadata } from "next";
import { RegisterForm } from "./RegisterForm";

export const metadata: Metadata = {
  title: "Create account",
  description: "Create a free Statlas account to manage your subscription, assistant quota and API keys.",
  alternates: { canonical: "/register" },
};

export default function RegisterPage() {
  return (
    <div className="container page" style={{ maxWidth: 480 }}>
      <p className="kicker">Account</p>
      <h1 className="page__title">Create account</h1>
      <p className="page__lede">
        A free account unlocks the assistant quota, saved comparisons and — when you upgrade —
        Pro features. Your data is yours; see the privacy policy for what we store.
      </p>
      <RegisterForm />
    </div>
  );
}
