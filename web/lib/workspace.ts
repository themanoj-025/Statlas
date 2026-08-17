// Phase 7 — scouting workspace display constants.
// Status/priority labels are the product's single naming source (the backend
// stores the enum codes; every display name lives here, never duplicated).

import type { EntryPriority, EntryStatus } from "./types";

// Pipeline order for display (docs/product/scouting-pipeline.md §1).
export const STATUS_ORDER: EntryStatus[] = [
  "discovered",
  "monitoring",
  "scouted",
  "shortlisted",
  "reviewed",
  "rejected",
  "signed",
];

export const STATUS_LABELS: Record<EntryStatus, string> = {
  discovered: "Discovered",
  monitoring: "Monitoring",
  scouted: "Scouted",
  shortlisted: "Shortlisted",
  reviewed: "Reviewed",
  rejected: "Rejected",
  signed: "Signed",
};

export const PRIORITY_LABELS: Record<Exclude<EntryPriority, null>, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
};

// Semantic chip class per status — always paired with the text label
// (never color alone, Constitution §2 accessibility).
export const STATUS_CHIP_CLASS: Record<EntryStatus, string> = {
  discovered: "chip",
  monitoring: "chip chip--info",
  scouted: "chip chip--accent",
  shortlisted: "chip chip--primary",
  reviewed: "chip chip--purple",
  rejected: "chip chip--danger",
  signed: "chip chip--success",
};

export const PRIORITY_CHIP_CLASS: Record<Exclude<EntryPriority, null>, string> = {
  low: "chip",
  medium: "chip chip--warning",
  high: "chip chip--danger",
};
