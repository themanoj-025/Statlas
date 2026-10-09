import type { Metadata } from "next";
import { LoginForm } from "./LoginForm";

export const metadata: Metadata = {
  title: "Sign in",
  description: "Sign in to Statlas to manage your subscription, assistant quota and API keys.",
  alternates: { canonical: "/login" },
};

export default function LoginPage() {
  return (
    <div className="container page" style={{ maxWidth: 480 }}>
      <p className="kicker">Account</p>
      <h1 className="page__title">Sign in</h1>
      <p className="page__lede">
        Sign in to manage your Pro subscription, assistant quota and API keys.
      </p>
      <LoginForm />
    </div>
  );
}
