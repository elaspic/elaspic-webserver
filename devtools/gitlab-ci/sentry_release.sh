#!/bin/bash

set -ex

SENTRY_URL="https://sentry.io/api/hooks/release/builtin/129313/3284ec114189c6eac1528760d12a29ceda54ecf39ca9402ff0e2dcf831a5be95/"

curl "${SENTRY_URL}" \
  -X POST \
  -H 'Content-Type: application/json' \
  -d "{\"version\": \"$(git log -n 1 --pretty=format:%H)\"}"
