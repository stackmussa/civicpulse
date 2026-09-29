import http from 'k6/http';
import { check, sleep } from 'k6';

// Multi-stage load ramp to demonstrate HPA scale-out and scale-in lag
export const options = {
  stages: [
    { duration: '30s', target: 10 },  // baseline warmup
    { duration: '1m', target: 50 },   // ramp up load to trigger HPA scaling
    { duration: '1m', target: 50 },   // sustained peak load
    { duration: '30s', target: 0 },   // cool down to test stabilization window
  ],
  thresholds: {
    http_req_duration: ['p(95)<1500'], // 95% of requests under 1.5s
    http_req_failed: ['rate<0.01'],    // less than 1% failure rate
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8000';

const SAMPLE_COMPLAINTS = [
  { text: "Water pipe leaking heavily on Main Double Road near market", location: "Sector F-7, Islamabad" },
  { text: "Street lights dark for three consecutive days on street 12", location: "Sector G-10/2, Islamabad" },
  { text: "Garbage dump overflow blocking pedestrian footpath", location: "Commercial Market, Rawalpindi" },
  { text: "Dangerous electric spark on transformer pole during rain", location: "Sector I-9/4, Islamabad" },
  { text: "Deep pothole causing vehicular damage near overhead bridge", location: "Murree Road, Rawalpindi" },
];

export default function () {
  const rand = Math.random();

  if (rand < 0.4) {
    // 40% traffic: cached /api/stats endpoint
    const res = http.get(`${BASE_URL}/api/stats`);
    check(res, {
      'stats status 200': (r) => r.status === 200,
    });
  } else if (rand < 0.7) {
    // 30% traffic: paginated complaints list
    const res = http.get(`${BASE_URL}/api/complaints?page=1&page_size=10`);
    check(res, {
      'list status 200': (r) => r.status === 200,
    });
  } else {
    // 30% traffic: create complaint (exercises triage CPU + DB + cache invalidation)
    const payload = SAMPLE_COMPLAINTS[Math.floor(Math.random() * SAMPLE_COMPLAINTS.length)];
    const params = { headers: { 'Content-Type': 'application/json' } };
    const res = http.post(`${BASE_URL}/api/complaints`, JSON.stringify(payload), params);
    check(res, {
      'create status 201 or 429': (r) => r.status === 201 || r.status === 429,
    });
  }

  sleep(0.5);
}
