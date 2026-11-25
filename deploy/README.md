# Deploying on a shared server

The public instance runs at **https://scamshield.42studio.fit** on an EC2 host that already serves another project through Caddy on ports 80/443. ScamShield never publishes a port of its own:

```
Internet ── :443 ── Caddy (the host's existing web container)
                      ├─ scamshield.42studio.fit /api/*, /artifacts/*, /docs ──> scamshield-api:8000
                      └─ scamshield.42studio.fit (everything else) ────────────> scamshield-web:3000 (Next.js)
scamshield-api, -worker, -radar ── internal network ── scamshield-db (Postgres)
```

`scamshield-api` and `scamshield-web` also join the Caddy container's Docker network (`EDGE_NETWORK`). Every container, volume and network name starts with `scamshield`, so nothing clashes with the other project.

## Steps

1. DNS: an `A` record `scamshield` → the server's IP.
2. Copy the repository to `~/scamshield` and create `~/scamshield/.env`:

   ```bash
   PUBLIC_URL=https://scamshield.42studio.fit
   EDGE_NETWORK=studio42_default          # docker inspect <caddy container> → its network
   SCAMSHIELD_MODE=live
   SCAMSHIELD_SEED_DEMO=1
   SCAMSHIELD_REQUIRE_LOGIN=1             # case data and scans need an account; checker, extension and blocklist stay public
   SCAMSHIELD_CORS=https://scamshield.42studio.fit
   SCAMSHIELD_JWT_SECRET=<openssl rand -hex 32>
   SCAMSHIELD_ADMIN_PASSWORD=<strong>
   SCAMSHIELD_ANALYST_PASSWORD=<strong>
   SERPAPI_KEY=...                        # optional: Search and Maps radars
   ANTHROPIC_API_KEY=...                  # optional: AI review
   ```

3. Start it: `docker compose -f docker-compose.server.yml up -d --build`.
4. Append [Caddyfile.scamshield](Caddyfile.scamshield) to the host Caddy's config and reload it (`caddy validate`, then `caddy reload`). Caddy gets the certificate once DNS points at the server.

Update later: copy the new code, then `docker compose -f docker-compose.server.yml up -d --build`. `down` keeps the database; never add `-v`.
