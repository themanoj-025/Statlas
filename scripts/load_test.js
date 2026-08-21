/**
 * Statlas Load Testing Script (k6)
 *
 * Tests key API endpoints under concurrent load to establish
 * performance baselines and identify bottlenecks.
 *
 * Usage:
 *   k6 run scripts/load_test.js
 *   k6 run --vus 50 --duration 30s scripts/load_test.js
 *
 * Constitution §4 (Performance): server-rendered pages must hit
 * LCP < 2.5s; API endpoints should respond within 500ms at p95.
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// Custom metrics
const errorRate = new Rate("errors");
const apiLatency = new Trend("api_latency");

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8000";

export const options = {
  stages: [
    { duration: "10s", target: 10 }, // ramp up
    { duration: "30s", target: 50 }, // sustained load
    { duration: "10s", target: 100 }, // peak load
    { duration: "10s", target: 0 }, // ramp down
  ],
  thresholds: {
    http_req_duration: ["p(95)<500", "p(99)<1000"], // 95% < 500ms, 99% < 1s
    errors: ["rate<0.05"], // < 5% error rate
  },
};

export default function () {
  const group = Math.random();

  if (group < 0.3) {
    // 30% — Meta / health checks (lightweight)
    testMeta();
  } else if (group < 0.5) {
    // 20% — Player search
    testPlayerSearch();
  } else if (group < 0.7) {
    // 20% — Leaderboard
    testLeaderboard();
  } else if (group < 0.85) {
    // 15% — Leagues
    testLeagues();
  } else {
    // 15% — Positions
    testPositions();
  }

  sleep(0.5); // think time between requests
}

function testMeta() {
  const res = http.get(`${BASE_URL}/api/v1/meta`);
  const success = check(res, {
    "meta status 200": (r) => r.status === 200,
    "meta has metrics": (r) => {
      try {
        return JSON.parse(r.body).metrics !== undefined;
      } catch {
        return false;
      }
    },
  });
  errorRate.add(!success);
  apiLatency.add(res.timings.duration);
}

function testPlayerSearch() {
  const queries = ["haaland", "salah", "mbappe", "bellingham", "kroos"];
  const q = queries[Math.floor(Math.random() * queries.length)];
  const res = http.get(`${BASE_URL}/api/v1/players/search?q=${q}&limit=8`);
  const success = check(res, {
    "search status 200": (r) => r.status === 200,
    "search returns array": (r) => {
      try {
        return Array.isArray(JSON.parse(r.body));
      } catch {
        return false;
      }
    },
  });
  errorRate.add(!success);
  apiLatency.add(res.timings.duration);
}

function testLeaderboard() {
  const positions = ["ST", "CM", "CB", "AM", "W"];
  const position = positions[Math.floor(Math.random() * positions.length)];
  const res = http.get(
    `${BASE_URL}/api/v1/leaderboard?metric=si_index&position=${position}&limit=25`
  );
  const success = check(res, {
    "leaderboard status 200": (r) => r.status === 200,
    "leaderboard has entries": (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.entries !== undefined;
      } catch {
        return false;
      }
    },
  });
  errorRate.add(!success);
  apiLatency.add(res.timings.duration);
}

function testLeagues() {
  const res = http.get(`${BASE_URL}/api/v1/leagues`);
  const success = check(res, {
    "leagues status 200": (r) => r.status === 200,
    "leagues is array": (r) => {
      try {
        return Array.isArray(JSON.parse(r.body));
      } catch {
        return false;
      }
    },
  });
  errorRate.add(!success);
  apiLatency.add(res.timings.duration);
}

function testPositions() {
  const res = http.get(`${BASE_URL}/api/v1/positions`);
  const success = check(res, {
    "positions status 200": (r) => r.status === 200,
    "positions has data": (r) => {
      try {
        return JSON.parse(r.body).length > 0;
      } catch {
        return false;
      }
    },
  });
  errorRate.add(!success);
  apiLatency.add(res.timings.duration);
}
