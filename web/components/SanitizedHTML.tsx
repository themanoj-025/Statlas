"use client";

import { useMemo } from "react";
import DOMPurify from "dompurify";

interface SanitizedHTMLProps {
  html: string;
  className?: string;
}

/**
 * Renders sanitized HTML using DOMPurify.
 *
 * Currently all blog/docs content is hardcoded, but this component future-proofs
 * against a CMS integration where content could be user-generated or externally
 * sourced. DOMPurify strips scripts, event handlers, and other XSS vectors.
 *
 * Must be a client component because DOMPurify requires the DOM API.
 */
export default function SanitizedHTML({ html, className }: SanitizedHTMLProps) {
  const safeHtml = useMemo(() => DOMPurify.sanitize(html), [html]);

  return (
    <div
      className={className}
      dangerouslySetInnerHTML={{ __html: safeHtml }}
    />
  );
}
