# UGAC Server Deployment

The quiz is served at https://ugac.iitmandi.ac.in/quiz/. It is a single
Flask-SocketIO process behind the UGAC server's existing HTTPS reverse proxy.

The deployment branch is deploy/ugac in
https://github.com/TayalAditya/ugac-live-quiz.

## Before Deployment

1. Create a Neon database and copy its pooled PostgreSQL connection string.
2. On the server, create a checkout directory separate from the UGAC website
   files, for example /opt/ugac-live-quiz.
3. Copy .env.example to .env. Set APP_ENV=production, the Neon URL, and
   unique values for SECRET_KEY and ADMIN_PASSWORD.
4. Ensure .env is readable only by the deployment account and is never
   committed or copied into the public website directory.

## Container

From the quiz checkout on the UGAC server:

    docker compose up -d --build
    docker compose ps
    curl http://127.0.0.1:5010/healthz

The container is deliberately bound only to 127.0.0.1:5010. It cannot be
reached directly from the internet.

## Reverse Proxy

Add the two location blocks from deploy/nginx-quiz.conf to the existing HTTPS
server block for ugac.iitmandi.ac.in, then validate before reloading:

    sudo nginx -t
    sudo systemctl reload nginx

The Socket.IO route is separate because it needs WebSocket upgrade headers.
The proxy also sends X-Forwarded-Prefix: /quiz, letting Flask generate links,
redirects, QR codes, form actions, and socket paths beneath /quiz/.

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
    docker compose up -d --build
    docker image prune -f

Use one Gunicorn worker. The live leaderboard cache is held in process memory;
multiple workers would require a shared Redis message queue and cache.
