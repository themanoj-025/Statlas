import type { Metadata } from "next";

export type LegalSection = {
  title: string;
  paragraphs: string[];
};

export const legalMetadata: Metadata = {
  robots: { index: true, follow: true },
};

export function LegalDoc({
  title,
  intro,
  sections,
  version,
}: {
  title: string;
  intro: string;
  sections: LegalSection[];
  version: string;
}) {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <p className="kicker">Legal</p>
      <h1 className="page__title">{title}</h1>

      <div className="notice" role="note">
        <strong>Draft — requires lawyer review before publication.</strong> This is a first-draft
        framework written for Statlas&rsquo;s actual product and data practices. It is not legal
        advice and must be reviewed and signed off by a qualified lawyer in the founder&rsquo;s
        jurisdiction before it is published or any user relies on it.
      </div>

      <p className="page__lede">{intro}</p>

      <div className="prose">
        {sections.map((section, index) => (
          <section key={section.title}>
            <h2>
              {index + 1}. {section.title}
            </h2>
            {section.paragraphs.map((paragraph) => (
              <p key={paragraph.slice(0, 40)}>{paragraph}</p>
            ))}
          </section>
        ))}
      </div>

      <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginTop: "var(--space-6)" }}>
        {version}
      </p>
    </div>
  );
}
