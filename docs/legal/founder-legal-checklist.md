# Statlas — Founder Legal Checklist

*Phase 0 deliverable B4. This is a **to-do list for the human founder**, not legal advice and not execution. Each item has an action, a reason, and the outcome to confirm. Items marked `[DO BEFORE LAUNCH]` are blockers for public launch; the rest can proceed in parallel with development.*

*Companion documents: `terms-of-service-draft.md` and `privacy-policy-draft.md` (both flagged REQUIRES LAWYER REVIEW), `data-compliance-notes.md` (source-term re-verifications).*

---

## A. Business entity — research, then register

- [ ] **Determine your jurisdiction.** Statlas's registration country determines the ToS governing-law clause, tax obligations, and GDPR/Supervisory-Authority position. Pick the jurisdiction where the founder is based (or where the entity will have its real economic center). *Outcome: a one-line statement "Statlas is registered in <jurisdiction>."*
- [ ] **Research entity types for that jurisdiction** and choose one. Examples to research, depending on jurisdiction: US (LLC vs. S-Corp), UK (Ltd), Netherlands (BV), Germany (GmbH / UG), France (SAS / SARL), Spain (SL), Portugal (Lda). Consider liability protection, tax treatment, and cost. *Outcome: entity type chosen.*
- [ ] **Register the entity** and obtain its registration number. *Outcome: certificate/registration number.*
- [ ] **Obtain tax identifiers:** US: EIN (free from the IRS); UK: company number + UTR; EU: national registration number and, if selling digital services cross-border, a **VAT OSS registration** for EU digital-services VAT. *Outcome: tax IDs filed.*
- [ ] **Open a business bank account** under the entity name. Needed for Stripe payouts and legitimacy. *Outcome: account opened.*
- [ ] **Set up basic bookkeeping** (tool + process) from day one — legal costs, Stripe fees, revenue. *Outcome: ledger exists.*

`[DO BEFORE LAUNCH]` The entity must exist before the ToS/privacy policy name a controller, before Stripe is configured in production, and before any revenue is collected.

## B. Domain registration

- [ ] **Register the primary domain:** **statlas.com**. This is the recommended primary.
- [ ] **Register close variants** to protect against typosquatting and future expansion (budget permitting): `statlas.co`, `statlas.football`, `getstatlas.com`, `statlas.app`, `statlas.io`, and common misspellings such as `statlass.com`. *Outcome: variants registered or consciously declined with a note.*
- [ ] **Check availability across TLDs** before committing brand collateral. *Outcome: availability table.*
- [ ] **Enable WHOIS privacy** on the registrations (or use a privacy-forward registrar). *Outcome: personal details not public.*
- [ ] **Add the domains to the repo's `.env.example`** as canonical URL configuration (no secrets, just the canonical hostnames). *Outcome: one canonical domain for the product; others 301-redirect.*

## C. Business email

- [ ] **Set up business email at the primary domain** (Google Workspace or Zoho Mail — cheap, professional, and gives you the operational mailboxes below).
- [ ] **Create and monitor these mailboxes (they are referenced by the legal drafts and must be real):**
  - `hello@statlas.com` — general contact.
  - `privacy@statlas.com` — data-subject requests (DSR). The privacy policy promises a documented, monitored process; a dead mailbox is a compliance failure.
  - `legal@statlas.com` — lawyer/legal correspondence and source-permission requests (e.g., the FBref written-permission request).
  - `data@statlas.com` — the descriptive User-Agent contact address used by the scrapers (see `data-compliance-notes.md`).
- [ ] **Set a service-level commitment** for monitoring these mailboxes (e.g., daily check). *Outcome: mailboxes configured and monitored.*

## D. Trademark search for "Statlas"

- [ ] **Run a trademark search for "STATLAS"** before scaled commercial use. Start with free searches: USPTO TESS (US), EUIPO (EU), UKIPO (UK), WIPO Global Brand Database (international), plus a general web search for existing "Statlas" products or companies.
- [ ] **Check the relevant Nice classes** for a football analytics/data platform: **Class 9** (software), **Class 35** (business data services), **Class 41** (sporting/entertainment data services), **Class 42** (SaaS), **Class 45** (online services) — file or at least search across these.
- [ ] **Check for identical or confusingly similar marks in football/data contexts** specifically (including word marks of football clubs or agencies).
- [ ] **Decide on filing strategy** with the search results in hand: (a) proceed and file, (b) proceed unregistered (common-law/using-rights), or (c) rename. The constitution's naming is not set in stone until this search is done. *Outcome: a documented go/no-go decision.*
- [ ] **If proceeding, consider a filing** in the home jurisdiction first (cheapest), then EUIPO/Madrid as budget allows. *Outcome: filing decision recorded.*
- [ ] **Re-check the domain squatting situation** for the chosen name in parallel (see §B).

`[DO BEFORE LAUNCH]` At minimum, complete the *search* before paying for scaled marketing or launching a public brand; filing can follow but should be scheduled before competitors file.

## E. Legal reviews and source-term re-verifications

- [ ] **Send the FBref/Sports Reference written-permission request** (`data@statlas.com` outbound) as planned in `data-compliance-notes.md`. *Outcome: written response filed, whatever it is.*
- [ ] **Re-verify the StatsBomb LICENSE.pdf** (repo: github.com/hudl/open-data) before any Phase 1 wiring and again before any monetized feature touches StatsBomb data.
- [ ] **Re-verify API-Football free-tier limits and caching/redistribution terms** at account creation.
- [ ] **Have the ToS draft and Privacy Policy draft reviewed and signed off** by a lawyer in the founder's jurisdiction, using the enumerated review items in each document (§13 of the ToS, §12 of the Privacy Policy).
- [ ] **Get the GDPR legitimate-interests assessment (LIA) for player performance statistics signed off** (see `privacy-policy-draft.md` §3).
- [ ] **Confirm the EU/EEA hosting plan** for the database so the privacy policy's transfer statements hold true at launch.

## F. Payments and commercial readiness

- [ ] **Create the Stripe account under the legal entity**, with the business bank account attached.
- [ ] **Set up the subscription products** matching the Pro pricing (€7/month, €60/year) and test the checkout in Stripe test mode.
- [ ] **Register for EU VAT OSS** if selling to EU consumers (replaces per-country VAT registration for digital services).
- [ ] **Write the pricing page copy** that the ToS references (current prices always shown).

## G. Ongoing operational obligations

- [ ] **Maintain the dated changelog** (Constitution §5) — started during development, not backfilled.
- [ ] **Review the data retention policy every 24 months** (per `privacy-policy-draft.md` §6).
- [ ] **Re-run the trademark watch** annually (or use a watch service) after filing.
- [ ] **Review source compliance notes annually** and whenever a source changes terms.

---

## Summary of launch blockers

1. Entity registered and tax IDs obtained (§A).
2. Primary domain registered; canonical URL decided (§B).
3. Business + privacy mailboxes live and monitored (§C).
4. Trademark search completed with a recorded go/no-go (§D).
5. ToS + Privacy Policy reviewed and signed off by a lawyer (§E).
6. LIA for player statistics signed off (§E).
7. Stripe configured under the entity (§F).
8. Source terms re-verified (FBref permission outcome, StatsBomb LICENSE.pdf, API-Football terms) (§E).

---

## Versioning

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-08-11 | Initial founder checklist: entity, domain, email, trademark, legal reviews, payments, operations. |
