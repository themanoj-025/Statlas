import type { Metadata } from "next";
import { Suspense } from "react";
import { ResetPasswordClient } from "./ResetPasswordClient";

export const metadata: Metadata = {
  title: "Reset password",
  description: "Reset your Statlas password.",
  alternates: { canonical: "/reset-password" },
};

export default function ResetPasswordPage() {
  return (
    <div className="container page" style={{ maxWidth: 480 }}>
      <p className="kicker">Account</p>
      <h1 className="page__title">Reset password</h1>
      <p className="page__lede">
        Enter your email to receive a password reset link.
      </p>
      <Suspense>
        <ResetPasswordClient />
      </Suspense>
    </div>
  );
}
