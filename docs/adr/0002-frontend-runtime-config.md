# ADR 0002: Build-Once-Deploy-Many Runtime Configuration via Nginx Proxy

## Status
Accepted

## Context
Vite builds bundle application source code into static HTML, JavaScript, and CSS assets. Environment variables (`import.meta.env`) are evaluated and statically inlined at *build time*. If an absolute API URL (such as `http://localhost:8000` or a specific cluster ingress) is baked into the JavaScript bundle:
1. The container image becomes environment-specific.
2. The core container principle of **Build Once, Deploy Many** is destroyed.
3. Local development, staging, and production environments would require rebuilding the container image from scratch.

## Decision
We enforce a relative API routing strategy:
1. Frontend code exclusively issues API calls to relative paths (`/api/complaints`, `/api/stats`).
2. In production, the `nginx:1.27-alpine` container acts as a reverse proxy:
   ```nginx
   location /api/ {
       proxy_pass http://backend:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
   }
   ```
3. In local development, the Vite dev server mirrors this behavior via `server.proxy` targeting `http://backend:8000`.

## Consequences
- **True Image Portability:** A single frontend container image artifact can be deployed across Docker Compose, local k3d/kind, or remote production Kubernetes without rebuilding.
- **Elimination of CORS Preflight:** Because requests are dispatched to the same origin (`/api`), browsers omit CORS preflight `OPTIONS` requests, reducing HTTP round-trip latency.
- **Service Discovery:** Kubernetes CoreDNS and Docker bridge networks handle routing dynamically.
