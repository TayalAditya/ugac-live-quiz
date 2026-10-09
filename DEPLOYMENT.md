# UGAC Server Deployment

The quiz is served at https://ugac.iitmandi.ac.in/quiz/. It is a single
Flask-SocketIO process behind the UGAC server's existing Caddy HTTPS proxy.

The deployment branch is deploy/ugac in
https://github.com/TayalAditya/ugac-live-quiz.

## Before Deployment

1. Create a Neon database and copy its pooled PostgreSQL connection string.
2. On the server, create a checkout directory separate from the UGAC website
   files, for example /home/ugcouncil_user/live-quiz.
3. Copy .env.example to .env. Set APP_ENV=production, the Neon URL, and
   unique values for SECRET_KEY and ADMIN_PASSWORD.
4. Ensure .env is readable only by the deployment account and is never
   committed or copied into the public website directory.

## Container

From the quiz checkout on the UGAC server:

    docker compose -f docker-compose.yml -f docker-compose.ugac.yml up -d --build
    docker compose -f docker-compose.yml -f docker-compose.ugac.yml ps
    curl http://127.0.0.1:5010/healthz

The container is deliberately bound only to 127.0.0.1:5010. It cannot be
reached directly from the internet.

## Caddy Route

Add the block from deploy/caddy-quiz.caddy above the final SPA `handle` block
in the existing Caddyfile for ugac.iitmandi.ac.in, then validate and reload:

    docker exec ugac-frontend caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
    docker exec ugac-frontend caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile

The Caddy proxy forwards WebSocket upgrades automatically and sends
X-Forwarded-Prefix: /quiz, letting Flask generate links,
redirects, QR codes, form actions, and socket paths beneath /quiz/.

The existing site container and quiz container share the external
`ugac-internal` network; it is never necessary to expose the quiz directly to the
internet.

## Jump Host

From a machine that cannot reach the UGAC private address directly, run:

```powershell
.\deploy\deploy-to-ugac.ps1 `
  -HostName "172.22.100.12" -Port 2256 -UserName "ugcouncil_user" `
  -JumpHost "172.16.5.185" -JumpUser "tayalji"
```

## Smoke Test

Visit these public URLs:

    https://ugac.iitmandi.ac.in/quiz/
    https://ugac.iitmandi.ac.in/quiz/admin
    https://ugac.iitmandi.ac.in/quiz/healthz

Create a two-question quiz, scan its QR code from a phone, open and close both
questions, then export the XLSX. The browser developer console should show a
Socket.IO connection to /quiz/socket.io/.

## Updating

    git pull --ff-only
    docker compose -f docker-compose.yml -f docker-compose.ugac.yml up -d --build
    docker image prune -f

Use one Gunicorn worker. The live leaderboard cache is held in process memory;
multiple workers would require a shared Redis message queue and cache.
