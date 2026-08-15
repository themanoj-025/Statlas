# Statlas — Terms of Service (First Draft)

> ## ⚠️ DRAFT — REQUIRES LAWYER REVIEW BEFORE PUBLICATION
>
> This is a first-draft framework written by an AI assistant for Statlas's specific product and data practices. It is not legal advice and must be reviewed, corrected, and signed off by a qualified lawyer in the founder's jurisdiction **before** it is published or any user relies on it. Items requiring a lawyer's decision are enumerated in §13 and marked `[LAWYER]` in the text.
>
> Draft date: 2026-08-11 · Applies to Statlas (the football data platform).

---

## 1. Who we are

Statlas ("Statlas", "we", "us", "our") operates a football (soccer) data visualization and scouting analytics platform at **statlas.com** (the recommended primary domain; registration is a pending founder task per `founder-legal-checklist.md` §B), including the website, the mobile-responsive web application, and any API or embed services we offer.

## 2. The service and what to expect from the data

Statlas provides derived football statistics and analysis: per-90 statistics, percentile rankings, the Statlas Index composite score, player profiles, league leaderboards, radar charts, shot and pass maps where coverage exists, and scouting-oriented tools.

You should understand, before using the service, that:

- **The data is derived from third-party sources** (including FBref/Sports Reference, Understat, StatsBomb Open Data, and API-Football) which we do not own and which are refreshed on the cadence stated on each page ("Data as of YYYY-MM-DD").
- **Data is provided "as-is" with no guarantee of accuracy or completeness.** Errors occur in source data and in our pipeline. Recency labels, coverage labels, and the data coverage page tell you what data exists and when it was collected; they do not guarantee correctness.
- **The service is not real-time.** Batch-updated data is labeled with its snapshot date. The word "live" on Statlas applies only to the fixtures and live-score layer. Do not rely on Statlas for real-time match or betting-critical information.
- **The Statlas Index and percentiles are computed per a published methodology** (`/methodology`), which is part of these terms: the methodology is the definitive description of how derived metrics are calculated and it may change with notice as described in §11.

**Accuracy limitation clause.** Because our metrics are derived from third-party sources on a stated cadence and provided as-is, Statlas does not warrant that any statistic, percentile, or index value is accurate, complete, current, or fit for any particular purpose. You use the data at your own risk.

## 3. Accounts and eligibility

- You must be **at least 16 years old** to use the service (in the EEA/UK; where a higher age applies locally, the local age applies).
- **Paid subscriptions require you to be 18 or older** or to have parental consent.
- You are responsible for keeping your account credentials confidential and for all activity under your account. Notify us promptly at privacy@statlas.com if you believe your account has been compromised.
- One person, one account. Accounts may not be shared across organizations except under the Pro or API tiers where explicitly permitted.

## 4. Free tier and Pro subscription

### Free tier
The free tier includes: full player profiles, the Statlas Index and percentiles for all qualified players, league leaderboards (limited to the top 50 rows per leaderboard), **3 player comparisons per day**, and the data coverage and methodology pages. Feature limits are shown on the pricing page and may be adjusted with notice.

### Pro subscription
Pro is billed **monthly at €7 (or annual at €60, billed yearly)** and includes, as of the drafting date: unlimited leaderboard rows, CSV exports, PDF scout-report export, embed widgets (up to 10 active embeds), and priority support. **We may change prices or feature scopes; current prices are always shown on the pricing page before you subscribe.**

### Billing, renewal, and cancellation
- Payments are processed by **Stripe** as our payment processor. We do not store your card number (see the Privacy Policy).
- Subscriptions **auto-renew** until cancelled.
- **You can cancel at any time** from your account settings. Cancellation takes effect at the end of the current billing period; you keep Pro access until then. **We do not provide partial refunds for unused portions of a billing period**, except where required by law.
- If payment fails, we will retry per Stripe's dunning schedule and may downgrade your account to the free tier after the grace period.

### B2B/API tier
A commercial API tier is planned but not yet offered. When offered, its terms will be a separate agreement; nothing in these terms grants API access or the right to resell data outside that future agreement.

## 5. Acceptable use

You agree **not** to:

- **Scrape, crawl, or otherwise access Statlas itself by automated means**, or attempt to circumvent rate limits, access controls, or the "pending qualification"/data-pending states to obtain data we have not published.
- **Resell, redistribute, or sublicense** Statlas-derived metrics, leaderboard data, or API access outside the terms of the tier you are on. (This clause covers Statlas's own derived output; it does not affect the underlying third-party facts, see §6.)
- Use the service to build a competing database or product that is a material substitute for Statlas.
- Use Statlas data to train, fine-tune, or prompt AI models (we mirror our sources' restrictions: no model training on our derived output without written permission).
- Use the service to harass, defame, or misidentify any individual, or to publish fabricated statistics attributed to the service.
- Use the service in violation of any applicable law, or to make decisions that violate the rights of any data subject under the GDPR or equivalent law.

We may suspend or terminate accounts that violate this section, with notice where feasible.

## 6. Intellectual property and data ownership

- **Statlas's derived metrics are proprietary to Statlas.** This includes the Statlas Index formula and scores, percentile calculations, the weighting system, radar/visualization designs, and site copy. You receive a limited, non-exclusive, non-transferable license to use the service and its output for your own analysis, subject to these terms.
- **The underlying factual statistics are sourced from third parties and are not exclusively owned by Statlas.** FBref data is owned/licensed by Sports Reference and its data providers; xG models by Understat and FBref respectively; event data by StatsBomb (see our data compliance notes). Where required, pages carrying third-party data display the required attribution (e.g., StatsBomb logo and source statement).
- **Copyright in the pages' presentation and the derived metrics is Statlas's.** Copyright in the underlying facts is not ours to grant.

## 7. Third-party content and attribution

Certain features display third-party data subject to separate attribution obligations (notably StatsBomb open data and API-Football). Statlas complies with those attribution requirements in the UI; you may not remove, obscure, or alter third-party logos, source statements, or recency labels that appear on the service.

## 8. Disclaimers of warranties

**The service is provided "as is" and "as available", without warranties of any kind, express or implied**, including accuracy, merchantability, fitness for a particular purpose, and non-infringement — except as required by law. We do not warrant that the service will be uninterrupted or error-free.

**Not professional or betting advice.** Nothing on Statlas constitutes professional scouting, investment, gambling, or betting advice. The Statlas Index is a descriptive composite metric, not a prediction. Decisions you make based on the service are your own.

## 9. Limitation of liability

To the maximum extent permitted by law, **Statlas's total liability for any claim arising out of or related to these terms or the service is limited to the greater of (a) the amounts you paid us in the twelve (12) months preceding the claim, or (b) €50.** We are not liable for indirect, incidental, consequential, special, or punitive damages, or for lost profits or data. Where liability cannot be excluded by law, it is limited to the maximum extent permitted. `[LAWYER]` — jurisdiction-specific caps must be reviewed.

## 10. Termination

You may stop using the service at any time and delete your account. We may suspend or terminate your access for material breach of these terms (including §5) or where required by law. On termination, your right to use the service ends; our retention of data is described in the Privacy Policy.

## 11. Changes to these terms and to the methodology

- **Methodology changes** (formula, weights, threshold, grouping) take effect on the date the updated methodology page and changelog entry are published. Because the index is a published formula, users can audit any change.
- **These terms may be updated** with at least 14 days' notice by email or in-app notice for material changes; continued use after the effective date constitutes acceptance. Non-material changes may take effect immediately.
- Material price changes to your active subscription require your consent and never apply retroactively.

## 12. Governing law and disputes `[LAWYER]`

These terms are governed by the laws of **the jurisdiction where Statlas is registered (to be determined by the founder — see the legal checklist)**. Any dispute will first be subject to good-faith negotiation; if unresolved, it will be submitted to the courts of that jurisdiction, or to binding arbitration if we determine arbitration is required by local law. The governing law and forum clauses must be reviewed and set by counsel.

## 13. Items for lawyer review (summary)

1. Governing law and dispute forum (§12).
2. Liability cap and exclusion wording for the applicable jurisdiction (§9).
3. The GDPR-compliant treatment of players' performance data in this ToS and the Privacy Policy (player statistics are personal data — no "public figure" exemption).
4. Whether the "material substitute"/competing-database restrictions adequately protect Statlas from its own sources and vice versa (§5–6).
5. Consumer-protection and cancellation/refund language for the countries where users reside (EU consumer rights, UK, US states).
6. Final pricing, free-tier limits, and feature scopes before the pricing page ships.
7. The API tier terms before any API is offered.

---

## 14. Versioning

| Version | Date | Change |
|---|---|---|
| 1.0 (draft) | 2026-08-11 | First draft for Statlas-specific product: derived-data accuracy limits, free/Pro tiers, Stripe billing and cancellation, acceptable use, IP statement, methodology-change notice. Requires lawyer review. |
