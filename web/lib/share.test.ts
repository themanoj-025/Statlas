/**
 * Permalink + embed tests (Phase 3 — Part C quality gates).
 * Runs under `node --test` (Node 22.6+ type-stripping; no bundler needed).
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  MAX_RADAR_PLAYERS,
  MAX_TREND_PLAYERS,
  buildEmbedCode,
  decodeRadarQuery,
  decodeTrendQuery,
  embedPageUrl,
  encodeRadarQuery,
  encodeTrendQuery,
  ogImageUrl,
  sharePageUrl,
  socialShareUrls,
} from "./share.ts";

test("radar permalink round-trips the exact configuration", () => {
  const query = encodeRadarQuery({ players: ["erling-haaland", "mohamed-salah"], mode: "raw" });
  const decoded = decodeRadarQuery(query);
  assert.deepEqual(decoded, {
    kind: "radar",
    players: ["erling-haaland", "mohamed-salah"],
    mode: "raw",
  });
});

test("trend permalink round-trips players, metrics, window and mode", () => {
  const query = encodeTrendQuery({
    players: ["erling-haaland", "mohamed-salah"],
    metrics: ["si_prgp_p90", "si_prgc_p90"],
    window: 10,
    mode: "pct",
  });
  const decoded = decodeTrendQuery(query);
  assert.deepEqual(decoded, {
    kind: "trend",
    players: ["erling-haaland", "mohamed-salah"],
    metrics: ["si_prgp_p90", "si_prgc_p90"],
    window: 10,
    mode: "pct",
  });
});

test("decode clamps to safe defaults and limits — never invalid state", () => {
  // Garbage mode -> pct; bad window -> 5; over-limit players -> sliced.
  const radar = decodeRadarQuery("v=1&players=a,b,c,d,e,f&mode=weird");
  assert.equal(radar.mode, "pct");
  assert.equal(radar.players.length, MAX_RADAR_PLAYERS);

  const trend = decodeTrendQuery("players=a,b,c,d&metrics=&window=99&mode=raw");
  assert.equal(trend.players.length, MAX_TREND_PLAYERS);
  assert.equal(trend.window, 5);
  assert.equal(trend.mode, "raw");
  assert.deepEqual(trend.metrics, []); // empty metrics stay empty (caller applies defaults)

  // Duplicates collapse.
  const dedup = decodeRadarQuery("players=a,a,b");
  assert.deepEqual(dedup.players, ["a", "b"]);
});

test("share URLs target the locked routes", () => {
  const query = encodeRadarQuery({ players: ["a"], mode: "pct" });
  assert.equal(sharePageUrl("radar", query), `/compare?${query}`);
  assert.equal(sharePageUrl("trend", query), `/trend?${query}`);
  assert.equal(ogImageUrl("radar", query), `/compare/og-image?${query}`);
  assert.equal(ogImageUrl("trend", query), `/trend/og-image?${query}`);
  assert.equal(embedPageUrl("radar", query), `/embed/radar?${query}`);
});

test("embed code is a real, lazy-loaded, attributed iframe snippet", () => {
  const query = encodeRadarQuery({ players: ["erling-haaland"], mode: "pct" });
  const code = buildEmbedCode("radar", query, { title: "Haaland radar" });
  assert.match(code, /<iframe /);
  assert.match(code, /src="\/embed\/radar\?/);
  assert.match(code, /title="Haaland radar"/);
  assert.match(code, /loading="lazy"/);
  assert.match(code, /Statlas/); // attribution + backlink
});

test("embed code uses absolute URLs when an origin is given (third-party pages)", () => {
  const query = encodeRadarQuery({ players: ["erling-haaland"], mode: "pct" });
  const code = buildEmbedCode("radar", query, { origin: "https://statlas.com" });
  // A relative src/href would resolve against the EMBEDDING page's origin.
  assert.match(code, /src="https:\/\/statlas\.com\/embed\/radar\?/);
  assert.match(code, /href="https:\/\/statlas\.com\/compare"/);
  assert.ok(!code.includes('src="/embed'));
});

test("social share intents carry the URL and title", () => {
  const urls = socialShareUrls("https://statlas.com/compare?players=a", "Player comparison");
  assert.match(urls.x, /^https:\/\/twitter\.com\/intent\/tweet\?/);
  assert.match(urls.x, /url=https%3A%2F%2Fstatlas\.com/);
  assert.match(urls.linkedin, /^https:\/\/www\.linkedin\.com\/sharing\/share-offsite\/\?url=/);
});
