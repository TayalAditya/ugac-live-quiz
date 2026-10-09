#!/usr/bin/env bash
set -Eeuo pipefail

REPOSITORY_URL="${REPOSITORY_URL:-https://github.com/TayalAditya/ugac-live-quiz.git}"
BRANCH="${BRANCH:-deploy/ugac}"
APP_DIR="${APP_DIR:-$HOME/live-quiz}"
UGAC_DOCKER_NETWORK="${UGAC_DOCKER_NETWORK:-ugac-internal}"

require_command() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "Required command is missing: $1" >&2
        exit 1
    }
}

compose_up() {
    if docker compose version >/dev/null 2>&1; then
        docker compose "$@"
    else
        docker-compose "$@"
    fi
}

require_command git
require_command docker
if ! docker compose version >/dev/null 2>&1 && ! command -v docker-compose >/dev/null 2>&1; then
    echo "Docker Compose is not installed." >&2
    exit 1
fi

if [[ -d "$APP_DIR/.git" ]]; then
    git -C "$APP_DIR" fetch origin "$BRANCH"
    git -C "$APP_DIR" checkout "$BRANCH"
    git -C "$APP_DIR" pull --ff-only origin "$BRANCH"
else
    git clone --branch "$BRANCH" --single-branch "$REPOSITORY_URL" "$APP_DIR"
fi

cd "$APP_DIR"

if [[ ! -f .env ]]; then
    cp .env.example .env
    echo
    echo "Created $APP_DIR/.env."
    echo "Set SECRET_KEY, ADMIN_PASSWORD, and DATABASE_URL before running this script again."
    exit 2
fi

if grep -q 'replace-with-' .env || grep -q 'USER:PASSWORD@' .env; then
    echo "Update the placeholder values in $APP_DIR/.env, then run this script again." >&2
    exit 2
fi

if ! docker network inspect "$UGAC_DOCKER_NETWORK" >/dev/null 2>&1; then
    echo "Expected UGAC Docker network was not found: $UGAC_DOCKER_NETWORK" >&2
    exit 1
fi

compose_up -f docker-compose.yml -f docker-compose.ugac.yml up -d --build
compose_up -f docker-compose.yml -f docker-compose.ugac.yml ps
curl --fail --silent --show-error http://127.0.0.1:5010/healthz
echo
echo "Quiz container is healthy on 127.0.0.1:5010."
echo "Caddy still needs the /quiz/ reverse-proxy block from deploy/caddy-quiz.caddy."
