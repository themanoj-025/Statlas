import type { Axis, PlayerPayload } from "./types";
import { playerColor } from "./colors";
import type { RadarPlayer } from "@/components/RadarChart";

/**
 * Build RadarPlayer lines from player payloads (canonical axis union, ordered
 * by the first player). Shared by the compare tool's RadarCard and the
 * embeddable widget so both render the exact same chart from the same data.
 */
export function buildRadarPlayers(payloads: PlayerPayload[]): RadarPlayer[] {
  const canonicalAxes: Axis[] = [];
  const seen = new Set<string>();
  for (const payload of payloads) {
    for (const axis of payload.axes) {
      if (!seen.has(axis.id)) {
        seen.add(axis.id);
        canonicalAxes.push(axis);
      }
    }
  }
  return payloads.map((payload, index) => {
    const byId = new Map(payload.axes.map((a) => [a.id, a]));
    const axes: Axis[] = canonicalAxes.map((canon) => {
      const own = byId.get(canon.id);
      return own ?? { ...canon, raw: null, pct: null, status: "no_data" as const };
    });
    return {
      id: payload.player.player_id,
      name: payload.player.name,
      color: playerColor(index),
      axes,
      index: payload.percentiles.index,
    };
  });
}
