#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
env_file="@data/srbbot.env"
pid_file="@data/srbbot.pid"
log_file="@data/logs/srbbot.log"

if [[ ! -r "$env_file" ]]; then
  echo "Missing protected runtime configuration: $env_file" >&2
  exit 1
fi
if [[ -f "$pid_file" ]]; then
  existing_pid="$(<"$pid_file")"
  if [[ "$existing_pid" =~ ^[0-9]+$ ]] && kill -0 "$existing_pid" 2>/dev/null; then
    echo "SRBbot is already running with PID $existing_pid" >&2
    exit 1
  fi
  rm -f -- "$pid_file"
fi

mkdir -p "$(dirname "$log_file")"
set -a
source "$env_file"
set +a
nohup .venv/bin/srbbot serve --poll-seconds 120 >>"$log_file" 2>&1 </dev/null &
pid=$!
printf '%s\n' "$pid" >"$pid_file"
sleep 1
if ! kill -0 "$pid" 2>/dev/null; then
  echo "SRBbot exited during startup; inspect $log_file" >&2
  exit 1
fi
echo "SRBbot started with PID $pid"
