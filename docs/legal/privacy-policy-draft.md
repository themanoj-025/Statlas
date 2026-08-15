# Statlas — Privacy Policy (First Draft)

> ## ⚠️ DRAFT — REQUIRES LAWYER REVIEW BEFORE PUBLICATION
>
> This is a first-draft framework written by an AI assistant for Statlas's actual planned data collection. It must be reviewed and signed off by a qualified lawyer in the founder's jurisdiction **before** publication. It deliberately contains **no boilerplate about data types Statlas does not collect**. Items requiring a lawyer's decision are enumerated in §12 and marked `[LAWYER]` in the text.
>
> Draft date: 2026-08-11 · Governing law and data-protection basis: GDPR (EU/EEA), UK GDPR (UK) — with the legal basis assessments summarized below.

---

## 1. Who processes your data

Statlas (the operator of the football analytics platform; registered entity and address to be confirmed in `founder-legal-checklist.md`) is the data controller for the personal data described in this policy. Contact for all privacy matters: **privacy@statlas.com** (a monitored mailbox — this is an operational requirement, not a formality; the domain and mailbox are founder tasks in `founder-legal-checklist.md` §B–§C).

## 2. What we collect (and what we deliberately do not)

### 2.1 Account data
When you create an account we collect:

- **Email address** (required; used for login and account communication).
- **Display name** (optional).
- **Password** — stored only as a salted, cryptographically hashed value. We never see or store your password in plaintext. If we later add OAuth sign-in (e.g., Google), we will collect the identity provider's identifier and your email from that provider instead of a password.

### 2.2 Payment data (Stripe)
When you subscribe to Pro, payment is processed by **Stripe**, which acts as our sub-processor. We **do not collect or store your card number, CVC, or expiry date**. Stripe receives the payment details directly, processes them on its PCI-DSS-compliant infrastructure, and returns us only: the subscription status, the last four digits of the card, the card brand, and the billing country. Stripe's own privacy policy applies to its processing.

### 2.3 Usage analytics
We plan to run **cookieless, privacy-friendly aggregate analytics** (we have selected Plausible Analytics for MVP: cookieless, IP-anonymized, no cross-site tracking, no advertising identifiers). This collects aggregate page-view and referral counts — it does not collect your personal data and cannot identify you.

### 2.4 Cookies and local storage
- **Functional cookies only:** a session cookie for authentication and a preference stored in local storage for your chosen theme (light/dark) and league defaults.
- **No advertising cookies, no tracking pixels, no third-party ad networks.**
- You can delete cookies/local storage at any time; doing so may log you out.

### 2.5 What we do NOT collect
We do not collect precise location, contacts/address book, device identifiers beyond those needed to run the service, or any data from third-party advertising networks. We do not sell personal data, and we do not use your personal data to train any AI model.

## 3. Player performance data (footballers' statistics)

**Statlas's core content is the performance statistics of football players. Under GDPR these statistics are personal data relating to identifiable (or identifiable-in-principle) individuals.** There is no "public figure" exemption for commercial analytics tools, and we do not claim the journalistic exemption.

We therefore document our position explicitly:

- **Legal basis (Art. 6(1)(f) — legitimate interests):** Statlas processes player performance statistics to provide the analytical service you use, to enable the historical-comparison and scouting functions of the product, and to pursue the public interest in statistical and analytical coverage of professional sport. We balance this against players' interests and rights, and we have prepared a **legitimate-interests assessment (LIA)** that records this analysis. `[LAWYER]` — the LIA must be reviewed and signed off before launch; it lives with the legal records of the project.
- **What we publish:** statistics as published by our sources (goals, per-90 metrics, percentiles, index scores) together with the player's name and club. We do not publish contact details, salaries, personal life information, or anything outside professional performance statistics and match participation.
- **Retention:** historical statistical snapshots are retained as **statistical/archival records** under a documented retention policy (§6), not indefinitely "just in case." The policy is reviewed every 24 months.
- **Data-subject rights:** players may exercise access, rectification, and erasure rights via the operational DSR process in §9. We will handle requests relating to an individual player's data in the same way we handle any data subject's request, subject to the limits in §9.

## 4. How we use personal data

| Purpose | Data | Legal basis |
|---|---|---|
| Provide and operate the service (accounts, profiles, comparisons) | Account data | Performance of contract (Art. 6(1)(b)) |
| Process subscriptions and prevent fraud | Payment status, billing email | Performance of contract; legitimate interests (6(1)(f)) |
| Publish football performance statistics | Player stats + names | Legitimate interests (6(1)(f)) — see §3 |
| Security, abuse prevention, server logs | Technical logs (IP, timestamps) | Legitimate interests (6(1)(f)) |
| Aggregate, anonymized analytics | None (aggregate only) | Legitimate interests (6(1)(f)) |

## 5. Who we share data with

We share personal data only with:

- **Stripe** (sub-processor — payments; §2.2).
- **Hosting and infrastructure providers** (EU/EEA region for our database and servers — selected at Phase 2; contractually bound by data-processing agreements).
- **Plausible Analytics** (aggregate analytics; no personal data involved).
- **Public authorities** where legally required.

We do not sell personal data. We do not share personal data with advertisers.

## 6. Retention

- **Account data:** retained while your account is active, and for 30 days after you delete your account (to allow recovery and complete processing), then deleted from active systems. Backups may retain data for up to 60 days more.
- **Payment records:** billing history is retained in accordance with tax law and Stripe's own retention; card data is never stored by us.
- **Statistical snapshots:** player performance snapshots are retained as archival/statistical records for the life of the platform to keep historical comparisons truthful (immutability is a product requirement — see the methodology). The retention policy is formally reviewed every 24 months, and any disposal is documented. `[LAWYER]` — confirm the archival justification and 24-month review cycle against applicable law.
- **Analytics aggregates:** retained no longer than 26 months, then deleted or fully anonymized.
- **Logs:** technical logs retained 30 days.

## 7. International transfers

Our database and servers are planned to be hosted in the **EU/EEA**. We do not currently transfer personal data outside the EEA except where required to process a payment (Stripe) or where an analytics processor is located there. `[LAWYER]` — confirm the final processor list and add the applicable transfer safeguards (SCCs) if any processor is outside the EEA.

## 8. Security

We apply industry-standard measures: encrypted connections (TLS), hashed and salted passwords, role-restricted access to production data, scheduled and **tested** backups (a broken backup is a failed backup), dependency and secret scanning in CI, and rate limiting on public endpoints. We will notify affected users and the relevant supervisory authority within the timeframes required by law in the event of a personal-data breach.

## 9. Your rights (data subject rights, DSR)

You have the right to:

- **Access** a copy of your personal data;
- **Rectify** inaccurate data;
- **Erase** your data ("right to be forgotten");
- **Restrict** processing;
- **Object** to processing based on legitimate interests (including the player-statistics processing in §3);
- **Data portability** where technically feasible;
- **Withdraw consent** where consent is the basis (we do not currently rely on consent for any core processing).

**How to exercise these rights:** email **privacy@statlas.com** — this is an operational, monitored mailbox, and requests are handled by a documented process, not a dead inbox. We respond within 30 days. **Limits:** erasure and rectification of *published aggregate statistics* are limited where the data has been incorporated into published historical snapshots that other users rely on and where the processing remains lawful under our legitimate-interests basis; we will always assess each request on its merits. Players are free to exercise these rights for their own performance data in the same way.

If you are in the EEA/UK, you may also lodge a complaint with your local supervisory authority.

## 10. Children

The service is not directed at children under 16 (EEA/UK), and paid subscriptions require users to be 18 or older. We do not knowingly collect data from children; if you believe a child has provided us personal data, contact us and we will delete it.

## 11. Changes to this policy

Material changes will be announced by email (for account holders) and in-app with at least 14 days' notice. The date of last revision is shown at the top of the policy.

## 12. Items for lawyer review (summary)

1. Governing law and the entity/address to be named as controller.
2. The legitimate-interests assessment for player performance statistics (Art. 6(1)(f)) and the archival retention justification.
3. International transfers (Stripe, analytics, hosting) and the applicable safeguards.
4. DSR erasure limits for published aggregates.
5. Final analytics/processor selection and DPAs.
6. Local requirements for the countries where users reside (e.g., state privacy laws in the US, ePrivacy for cookies).

---

## 13. Versioning

| Version | Date | Change |
|---|---|---|
| 1.0 (draft) | 2026-08-11 | First draft matching Statlas's actual collection: account/email auth, Stripe sub-processor payments, cookieless analytics, functional cookies only, GDPR position on player performance data with LIA and retention policy, operational DSR path. Requires lawyer review. |
