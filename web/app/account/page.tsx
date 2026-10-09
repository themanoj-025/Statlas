import type { Metadata } from "next";
import { AccountClient } from "./AccountClient";

export const metadata: Metadata = {
  title: "Account",
  description: "Manage your Statlas subscription, assistant quota and API keys.",
  alternates: { canonical: "/account" },
};

export default function AccountPage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <p className="kicker">Account</p>
      <h1 className="page__title">Account</h1>
      <AccountClient />
    </div>
  );
}
