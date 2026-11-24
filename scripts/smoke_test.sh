#!/usr/bin/env bash
# End-to-end check of the running Docker stack:
# API -> PostgreSQL -> Redis -> Celery worker -> Mailpit.
#
# Usage:
#   docker compose up -d --build
#   scripts/smoke_test.sh
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
MAILPIT_URL="${MAILPIT_URL:-http://localhost:8025}"
PYTHON="${PYTHON:-python3}"
EMAIL="ana.petrovic@example.com"
PASSWORD="password123"

step() { echo "==> $*"; }
fail() { echo "FAIL: $*" >&2; exit 1; }
# Evaluate a Python expression on the JSON read from stdin (`d` is the data).
json() { "$PYTHON" -c "import json, sys; d = json.load(sys.stdin); print($1)" | tr -d '\r'; }

step "Waiting for the API"
for _ in $(seq 1 60); do
  curl -fs "$API_URL/health" >/dev/null && break
  sleep 1
done
health=$(curl -fs "$API_URL/health") || fail "API did not start"
echo "    $health"
[ "$(echo "$health" | json 'd["database"]')" = ok ] || fail "database is not ok"
[ "$(echo "$health" | json 'd["redis"]')" = ok ] || fail "redis is not ok"

step "Migrations match the models (PostgreSQL)"
docker compose exec -T api alembic check || fail "alembic check found differences"

step "Seeding demo data"
docker compose exec -T api python -m app.seed

step "Requests without a token are rejected"
code=$(curl -s -o /dev/null -w '%{http_code}' "$API_URL/books")
[ "$code" = 401 ] || fail "expected 401, got $code"

step "Logging in as $EMAIL"
token=$(curl -fs -X POST "$API_URL/auth/login" \
  --data-urlencode "username=$EMAIL" --data-urlencode "password=$PASSWORD" \
  | json 'd["access_token"]') || fail "login failed"
auth="Authorization: Bearer $token"

step "Listing books"
count=$(curl -fs -H "$auth" "$API_URL/books" | json 'len(d)')
[ "$count" -gt 0 ] || fail "no books returned"
echo "    $count books"

step "Placing an order"
order_id=$(curl -fs -X POST "$API_URL/orders" -H "$auth" \
  -H "Content-Type: application/json" \
  -d '{"items": [{"book_id": 1, "quantity": 1}, {"book_id": 5, "quantity": 1}]}' \
  | json 'd["id"]') || fail "order was not created"
echo "    order #$order_id"

step "Waiting for the confirmation email in Mailpit"
subject="Order #$order_id confirmed"
for _ in $(seq 1 30); do
  found=$(curl -fs "$MAILPIT_URL/api/v1/messages" \
    | json "any(m['Subject'] == '$subject' for m in d['messages'])")
  if [ "$found" = True ]; then
    echo "Smoke test passed: '$subject' was delivered by the worker"
    exit 0
  fi
  sleep 1
done
fail "email '$subject' did not arrive"
