#!/usr/bin/env bash

source compose/.env
export SMOKE_BASE_URL="http://localhost"
bash scripts/golden_path_smoke.sh --skip-up
