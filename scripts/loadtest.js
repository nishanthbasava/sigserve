// k6 load test for the submit/poll API path.
//
// The sampler itself is deliberately out of scope (worker throughput is one
// MCMC per worker); this measures the API layer. Run the worker with
// SAMPLER_ENGINE=stub so queued jobs drain instantly instead of piling up:
//
//   SAMPLER_ENGINE=stub docker compose up -d worker
//   KEY=$(docker compose exec -T api python -m sigserve.cli create-key --name k6 | tail -1)
//   docker run --rm -i --add-host=host.docker.internal:host-gateway \
//     -e API_URL=http://host.docker.internal:8000 -e API_KEY=$KEY \
//     grafana/k6 run - < scripts/loadtest.js
//
// Requests per second is the `http_reqs` rate in the summary.

import http from "k6/http";
import { check, sleep } from "k6";

const BASE = __ENV.API_URL || "http://localhost:8000";
const KEY = __ENV.API_KEY;

export const options = {
  scenarios: {
    submit_and_poll: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "15s", target: 20 },
        { duration: "60s", target: 20 },
        { duration: "15s", target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<500"],
  },
};

// 20 mutation types x 8 samples, same shape the e2e test uses.
const MATRIX = Array.from({ length: 20 }, (_, i) =>
  Array.from({ length: 8 }, (_, j) => ((i * 7 + j * 3) % 10) + 1)
);

const PAYLOAD = JSON.stringify({ matrix: MATRIX, params: { rank: 2, max_iters: 100 } });

export default function () {
  const headers = { "Content-Type": "application/json", "X-API-Key": KEY };

  const submit = http.post(`${BASE}/jobs`, PAYLOAD, { headers });
  check(submit, { "submit returns 202": (r) => r.status === 202 });

  const poll = http.get(`${BASE}/jobs/${submit.json("id")}`, { headers });
  check(poll, { "poll returns 200": (r) => r.status === 200 });

  sleep(0.1);
}
