import type { Metadata } from "next";
import { LegalDoc, type LegalSection } from "@/components/LegalDoc";

export const metadata: Metadata = {
  title: "Terms of Service",
  description:
    "Statlas Terms of Service: derived-data accuracy limits, free and Pro tiers, acceptable use, intellectual property, and the published methodology as part of the terms.",
  alternates: { canonical: "/legal/terms" },
};

const SECTIONS: LegalSection[] = [
  {
    title: "Who we are",
    paragraphs: [
      'Statlas operates a football data visualization and scouting analytics platform (statlas.com — registration pending), including the website, the mobile-responsive web application, and any API or embed services we offer.',
    ],
  },
  {
    title: "The service and what to expect from the data",
    paragraphs: [
      'Statlas provides derived football statistics and analysis: per-90 statistics, percentile rankings, the Statlas Index composite score, player profiles, league leaderboards, radar charts, and shot and pass maps where coverage exists.',
      'The data is derived from third-party sources (including FBref/Sports Reference, Understat, StatsBomb Open Data, and API-Football) which we do not own and which are refreshed on the cadence stated on each page ("Data as of YYYY-MM-DD").',
      'Data is provided "as-is" with no guarantee of accuracy or completeness. The service is not real-time: batch-updated data is labeled with its snapshot date, and the word "live" applies only to the fixtures and live-score layer.',
      'The Statlas Index and percentiles are computed per a published methodology (/methodology), which is part of these terms: the methodology is the definitive description of how derived metrics are calculated and it may change with notice as described in section 11.',
      'Because our metrics are derived from third-party sources on a stated cadence and provided as-is, Statlas does not warrant that any statistic, percentile, or index value is accurate, complete, current, or fit for any particular purpose. You use the data at your own risk.',
    ],
  },
  {
    title: "Accounts and eligibility",
    paragraphs: [
      "You must be at least 16 years old to use the service (in the EEA/UK; where a higher age applies locally, the local age applies). Paid subscriptions require you to be 18 or older or to have parental consent.",
      "You are responsible for keeping your account credentials confidential and for all activity under your account. Notify us promptly at privacy@statlas.com if you believe your account has been compromised. One person, one account.",
    ],
  },
  {
    title: "Free tier and Pro subscription",
    paragraphs: [
      "The free tier includes: full player profiles, the Statlas Index and percentiles for all qualified players, league leaderboards (limited to the top 50 rows per leaderboard), 3 player comparisons per day, and the data coverage and methodology pages.",
      "Pro is billed monthly at €7 (or annual at €60, billed yearly) and includes, as of the drafting date: unlimited leaderboard rows, CSV exports, PDF scout-report export, embed widgets (up to 10 active embeds), and priority support. Prices and feature scopes may change; current prices are always shown on the pricing page before you subscribe.",
      "Payments are processed by Stripe; we do not store your card number. Subscriptions auto-renew until cancelled. You can cancel at any time; cancellation takes effect at the end of the current billing period, and we do not provide partial refunds for unused portions of a billing period except where required by law.",
      "A commercial API tier is planned but not yet offered. When offered, its terms will be a separate agreement; nothing in these terms grants API access or the right to resell data outside that future agreement.",
    ],
  },
  {
    title: "Acceptable use",
    paragraphs: [
      "You agree not to: scrape or access Statlas itself by automated means or attempt to circumvent rate limits or access controls; resell, redistribute, or sublicense Statlas-derived metrics or API access outside the terms of the tier you are on; use the service to build a competing database that is a material substitute for Statlas; use Statlas data to train, fine-tune, or prompt AI models (we mirror our sources' restrictions); use the service to harass, defame, or misidentify any individual, or to publish fabricated statistics attributed to the service; or use the service in violation of any applicable law.",
      "We may suspend or terminate accounts that violate this section, with notice where feasible.",
    ],
  },
  {
    title: "Intellectual property and data ownership",
    paragraphs: [
      "Statlas's derived metrics are proprietary to Statlas: the Statlas Index formula and scores, percentile calculations, the weighting system, radar/visualization designs, and site copy. You receive a limited, non-exclusive, non-transferable license to use the service and its output for your own analysis, subject to these terms.",
      "The underlying factual statistics are sourced from third parties and are not exclusively owned by Statlas. Where required, pages carrying third-party data display the required attribution (e.g., the StatsBomb logo and source statement).",
    ],
  },
  {
    title: "Third-party content and attribution",
    paragraphs: [
      "Certain features display third-party data subject to separate attribution obligations (notably StatsBomb open data and API-Football). Statlas complies with those attribution requirements in the UI; you may not remove, obscure, or alter third-party logos, source statements, or recency labels that appear on the service.",
    ],
  },
  {
    title: "Disclaimers of warranties",
    paragraphs: [
      "The service is provided \"as is\" and \"as available\", without warranties of any kind, express or implied — including accuracy, merchantability, fitness for a particular purpose, and non-infringement — except as required by law.",
      "Nothing on Statlas constitutes professional scouting, investment, gambling, or betting advice. The Statlas Index is a descriptive composite metric, not a prediction. Decisions you make based on the service are your own.",
    ],
  },
  {
    title: "Limitation of liability",
    paragraphs: [
      "To the maximum extent permitted by law, Statlas's total liability for any claim arising out of or related to these terms or the service is limited to the greater of (a) the amounts you paid us in the twelve months preceding the claim, or (b) €50. We are not liable for indirect, incidental, consequential, special, or punitive damages, or for lost profits or data.",
    ],
  },
  {
    title: "Termination",
    paragraphs: [
      "You may stop using the service at any time and delete your account. We may suspend or terminate your access for material breach of these terms or where required by law. On termination, your right to use the service ends; our retention of data is described in the Privacy Policy.",
    ],
  },
  {
    title: "Changes to these terms and to the methodology",
    paragraphs: [
      "Methodology changes (formula, weights, threshold, grouping) take effect on the date the updated methodology page and changelog entry are published. These terms may be updated with at least 14 days' notice by email or in-app notice for material changes; continued use after the effective date constitutes acceptance. Material price changes to your active subscription require your consent and never apply retroactively.",
    ],
  },
  {
    title: "Governing law and disputes",
    paragraphs: [
      "These terms are governed by the laws of the jurisdiction where Statlas is registered (to be determined — see the legal checklist). Any dispute will first be subject to good-faith negotiation; if unresolved, it will be submitted to the courts of that jurisdiction, or to binding arbitration if we determine arbitration is required by local law. The governing law and forum clauses must be reviewed and set by counsel.",
    ],
  },
];

export default function TermsPage() {
  return (
    <LegalDoc
      title="Terms of Service"
      intro="The terms that govern use of the Statlas platform. Draft date 2026-08-11; requires lawyer review before publication."
      sections={SECTIONS}
      version="Version 1.0 (draft) · 2026-08-11 · Items requiring lawyer review are tracked in founder-legal-checklist.md."
    />
  );
}
