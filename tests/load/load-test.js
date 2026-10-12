// Canonical k6 smoke test — synced verbatim into every portfolio repo
// (see shared/tools/sync_load_test.py). Per-repo tailoring happens through
// environment variables, NOT through editing local copies — local edits
// create the variant drift this canonical exists to prevent.
//
// Tailoring env vars (set in the repo's load-test workflow `env:` block):
//   K6_BASE_URL     target base URL            (default http://localhost:8000)
//   K6_HEALTH_PATH  health endpoint path       (default /health;
//                   Streamlit apps use /_stcore/health, Match-Mind /api/health)
//   K6_TARGET       peak virtual users         (default 10; Streamlit trio: 5)
//   K6_P95_MS       p(95) latency budget in ms (default 500; Streamlit trio: 1000)
//
// Example (Streamlit repo):
//   env: |
//     K6_BASE_URL=http://127.0.0.1:8501
//     K6_HEALTH_PATH=/_stcore/health
//     K6_TARGET=5
//     K6_P95_MS=1000

import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.K6_BASE_URL || 'http://localhost:8000';
const HEALTH_PATH = __ENV.K6_HEALTH_PATH || '/health';
const TARGET = Number(__ENV.K6_TARGET || 10);
const P95_MS = Number(__ENV.K6_P95_MS || 500);

export const options = {
  stages: [
    { duration: '30s', target: TARGET },  // ramp up
    { duration: '1m', target: TARGET },   // sustain
    { duration: '30s', target: 0 },       // ramp down
  ],
  thresholds: {
    http_req_duration: [`p(95)<${P95_MS}`],
    http_req_failed: ['rate<0.1'],
  },
};

export default function () {
  const res = http.get(`${BASE_URL}${HEALTH_PATH}`);
  check(res, {
    'status is 200': (r) => r.status === 200,
    [`response time < ${P95_MS}ms`]: (r) => r.timings.duration < P95_MS,
  });
  sleep(1);
}
