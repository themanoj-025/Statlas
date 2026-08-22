import type { Metadata } from "next";
import Link from "next/link";
import { Mail, MessageSquare, Clock, ExternalLink } from "lucide-react";

export const metadata: Metadata = {
  title: "Contact & Support",
  description:
    "Get in touch with the Statlas team. Data-accuracy reports, support issues, partnerships, and general inquiries.",
  alternates: { canonical: "/contact" },
};

const SUPPORT_OPTIONS = [
  {
    icon: Mail,
    title: "Email",
    description: "data@statlas.com",
    detail: "Data-accuracy reports are read first. Response within 24 hours.",
    href: "mailto:data@statlas.com",
  },
  {
    icon: MessageSquare,
    title: "Support",
    description: "support@statlas.com",
    detail: "General support issues. Response within 24 hours.",
    href: "mailto:support@statlas.com",
  },
  {
    icon: Clock,
    title: "Hours",
    description: "Monday \u2013 Friday",
    detail: "9:00 \u2013 18:00 CET. Weekend inquiries answered on Monday.",
    href: undefined,
  },
];

const TOPICS = [
  { label: "General inquiry", value: "general" },
  { label: "Data accuracy report", value: "data" },
  { label: "Support issue", value: "support" },
  { label: "Partnership", value: "partnership" },
  { label: "Media / Press", value: "media" },
  { label: "Enterprise sales", value: "enterprise" },
];

export default function ContactPage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <p className="kicker">Contact</p>
      <h1 className="page__title">Get in touch</h1>
      <p className="page__lede">
        Found an error in the data? A mismatch between the methodology and a number on the
        site? Something that should work but does not? We want to hear about it.
      </p>

      {/* Support options */}
      <div className="grid" style={{ marginBottom: "var(--space-6)" }}>
        {SUPPORT_OPTIONS.map((opt) => {
          const Icon = opt.icon;
          const Wrapper = opt.href ? "a" : "div";
          const wrapperProps = opt.href ? { href: opt.href } : {};
          return (
            <Wrapper key={opt.title} className="card grid__span-4" style={{ padding: "var(--space-5)", textDecoration: "none", color: "var(--color-text-primary)", display: "block" }} {...wrapperProps}>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-2)" }}>
                <Icon size={18} color="var(--color-primary)" aria-hidden="true" />
                <h3 style={{ fontSize: "var(--text-base)", margin: 0 }}>{opt.title}</h3>
              </div>
              <p style={{ fontSize: "var(--text-sm)", fontWeight: 600, marginBottom: "var(--space-1)", marginTop: 0 }}>{opt.description}</p>
              <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", margin: 0 }}>{opt.detail}</p>
            </Wrapper>
          );
        })}
      </div>

      {/* Contact form */}
      <section className="card" style={{ padding: "var(--space-6)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>Send us a message</h2>
        <form style={{ display: "grid", gap: "var(--space-3)" }} action="#">
          <div className="field">
            <label className="field__label" htmlFor="contact-name">Name</label>
            <input className="input" id="contact-name" type="text" required placeholder="Your name" />
          </div>
          <div className="field">
            <label className="field__label" htmlFor="contact-email">Email</label>
            <input className="input" id="contact-email" type="email" required placeholder="your@email.com" />
          </div>
          <div className="field">
            <label className="field__label" htmlFor="contact-subject">Subject</label>
            <select className="select" id="contact-subject" required>
              <option value="">Select a topic</option>
              {TOPICS.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label className="field__label" htmlFor="contact-message">Message</label>
            <textarea
              className="input"
              id="contact-message"
              required
              rows={6}
              maxLength={5000}
              placeholder="Tell us what you need help with..."
              style={{ height: "auto", resize: "vertical" }}
            />
          </div>
          <button type="submit" className="button" style={{ justifySelf: "start" }}>
            Send message
          </button>
          <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", margin: 0 }}>
            We typically respond within 24 hours. Your data is handled according to our{" "}
            <Link href="/legal/privacy">privacy policy</Link>.
          </p>
        </form>
      </section>

      {/* FAQ */}
      <section style={{ marginTop: "var(--space-6)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>Common questions</h2>
        <div className="faq">
          <details>
            <summary>How do I report a data error?</summary>
            <p>
              Every player and team page has a "Report a data error" link. You can also email{" "}
              <a href="mailto:data@statlas.com">data@statlas.com</a> directly. Data-accuracy
              reports are read first.
            </p>
          </details>
          <details>
            <summary>I found a mismatch between the methodology and a number on the site</summary>
            <p>
              That is a bug. Report it at{" "}
              <a href="mailto:data@statlas.com">data@statlas.com</a> with the player name and
              the page URL. We will investigate and fix it.
            </p>
          </details>
          <details>
            <summary>Can I schedule a demo?</summary>
            <p>
              Enterprise demos are available. Email{" "}
              <a href="mailto:sales@statlas.com">sales@statlas.com</a> with your organisation
              name and requirements.
            </p>
          </details>
        </div>
      </section>

      {/* Links */}
      <section style={{ marginTop: "var(--space-6)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>Other resources</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          <Link href="/help" style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            Help & FAQ <ExternalLink size={14} aria-hidden="true" />
          </Link>
          <Link href="/docs" style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            Documentation <ExternalLink size={14} aria-hidden="true" />
          </Link>
          <Link href="/data-coverage" style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            Data coverage <ExternalLink size={14} aria-hidden="true" />
          </Link>
        </div>
      </section>
    </div>
  );
}
