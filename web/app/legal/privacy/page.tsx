import type { Metadata } from "next";
import { LegalDoc, type LegalSection } from "@/components/LegalDoc";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description:
    "Statlas Privacy Policy: what we collect and deliberately do not, the GDPR position on player performance data, retention, and the operational data-subject request path.",
  alternates: { canonical: "/legal/privacy" },
};

const SECTIONS: LegalSection[] = [
  {
    title: "Who processes your data",
    paragraphs: [
      "Statlas (the operator of the football analytics platform; registered entity to be confirmed) is the data controller for the personal data described in this policy. Contact for all privacy matters: privacy@statlas.com (a monitored mailbox — operational, not a formality).",
    ],
  },
  {
    title: "What we collect (and what we deliberately do not)",
    paragraphs: [
      "Account data: email address (required), optional display name, and a password stored only as a salted, cryptographically hashed value. Payment data is processed by Stripe, which acts as our sub-processor: we do not collect or store your card number, CVC, or expiry date — Stripe returns only subscription status, last four digits, card brand, and billing country.",
      "We plan cookieless, privacy-friendly aggregate analytics (Plausible Analytics for MVP — IP-anonymized, no cross-site tracking, no advertising identifiers). Cookies are functional only: a session cookie for authentication and a local-storage theme preference. No advertising cookies, no tracking pixels, no third-party ad networks.",
      "We do not collect precise location, contacts, or device identifiers beyond what is needed to run the service. We do not sell personal data, and we do not use your personal data to train any AI model.",
    ],
  },
  {
    title: "Player performance data (footballers' statistics)",
    paragraphs: [
      "Statlas's core content is the performance statistics of football players. Under GDPR these statistics are personal data relating to identifiable individuals. There is no \"public figure\" exemption for commercial analytics tools, and we do not claim the journalistic exemption.",
      "Legal basis (Art. 6(1)(f) — legitimate interests): we process player performance statistics to provide the analytical service, to enable the historical-comparison and scouting functions of the product, and to pursue the public interest in statistical coverage of professional sport. We balance this against players' interests and rights in a legitimate-interests assessment (LIA) that must be reviewed and signed off before launch.",
      "What we publish: statistics as published by our sources (goals, per-90 metrics, percentiles, index scores) together with the player's name and club. We do not publish contact details, salaries, personal life information, or anything outside professional performance statistics and match participation.",
      "Retention: historical statistical snapshots are retained as statistical/archival records under a documented retention policy, not indefinitely \"just in case\"; the policy is reviewed every 24 months.",
      "Data-subject rights: players may exercise access, rectification, and erasure rights via the operational DSR process in section 9, handled in the same way as any data subject's request.",
    ],
  },
  {
    title: "How we use personal data",
    paragraphs: [
      "Account data is used to provide and operate the service (performance of contract, Art. 6(1)(b)). Payment status is used to process subscriptions and prevent fraud (contract + legitimate interests). Player statistics are published under the legitimate-interests basis above. Technical logs (IP, timestamps) support security and abuse prevention. Aggregate analytics contain no personal data.",
    ],
  },
  {
    title: "Who we share data with",
    paragraphs: [
      "We share personal data only with Stripe (sub-processor, payments), EU/EEA hosting and infrastructure providers bound by data-processing agreements, and public authorities where legally required. We do not sell personal data and do not share it with advertisers.",
    ],
  },
  {
    title: "Retention",
    paragraphs: [
      "Account data is retained while your account is active and for 30 days after deletion, then removed from active systems (backups up to 60 days more). Payment records are retained per tax law and Stripe's own retention. Statistical snapshots are retained as archival records for the life of the platform to keep historical comparisons truthful; the policy is formally reviewed every 24 months. Analytics aggregates are retained no longer than 26 months. Technical logs are retained 30 days.",
    ],
  },
  {
    title: "International transfers",
    paragraphs: [
      "Our database and servers are planned to be hosted in the EU/EEA. We do not currently transfer personal data outside the EEA except where required to process a payment (Stripe) or where an analytics processor is located there. Transfer safeguards (SCCs) will be confirmed with the final processor list.",
    ],
  },
  {
    title: "Security",
    paragraphs: [
      "We apply industry-standard measures: encrypted connections (TLS), hashed and salted passwords, role-restricted access to production data, scheduled and tested backups, dependency and secret scanning in CI, and rate limiting on public endpoints. We will notify affected users and the relevant supervisory authority within the timeframes required by law in the event of a personal-data breach.",
    ],
  },
  {
    title: "Your rights (data subject rights)",
    paragraphs: [
      "You have the right to access, rectify, erase, restrict, object (including to the player-statistics processing in section 3), and port your personal data, and to withdraw consent where consent is the basis (we do not currently rely on consent for any core processing).",
      "To exercise these rights, email privacy@statlas.com — an operational, monitored mailbox; requests are handled by a documented process, not a dead inbox. We respond within 30 days. Erasure and rectification of published aggregate statistics are limited where the data has been incorporated into published historical snapshots other users rely on and where processing remains lawful under our legitimate-interests basis; each request is assessed on its merits.",
      "If you are in the EEA/UK, you may also lodge a complaint with your local supervisory authority.",
    ],
  },
  {
    title: "Children",
    paragraphs: [
      "The service is not directed at children under 16 (EEA/UK), and paid subscriptions require users to be 18 or older. We do not knowingly collect data from children; if you believe a child has provided us personal data, contact us and we will delete it.",
    ],
  },
  {
    title: "Changes to this policy",
    paragraphs: [
      "Material changes will be announced by email (for account holders) and in-app with at least 14 days' notice. The date of last revision is shown at the top of the policy.",
    ],
  },
];

export default function PrivacyPage() {
  return (
    <LegalDoc
      title="Privacy Policy"
      intro="How Statlas handles personal data — including the GDPR position on player performance statistics. Draft date 2026-08-11; requires lawyer review before publication."
      sections={SECTIONS}
      version="Version 1.0 (draft) · 2026-08-11 · Items requiring lawyer review are tracked in founder-legal-checklist.md."
    />
  );
}
