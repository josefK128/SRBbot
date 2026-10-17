#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
pid_file="@data/srbbot.pid"
if [[ ! -f "$pid_file" ]]; then
  echo "SRBbot is not running"
  exit 0
fi
pid="$(<"$pid_file")"
if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
  kill "$pid"
  for _ in {1..20}; do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.25
  done
fi
rm -f -- "$pid_file"
echo "SRBbot stopped"
