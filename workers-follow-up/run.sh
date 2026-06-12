#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
python workers-follow-up/server.py
