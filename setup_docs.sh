#!/usr/bin/env bash
set -euo pipefail

REPO_NAME="ClassHub"

mkdir -p docs .github/workflows

if [ ! -f "docs/index.md" ]; then
cat > "docs/index.md" <<'MD'
# ClassHub Docs

ClassHub is a self-hosted, classroom-first LMS designed for real programming:
fast student join → lesson → submission → teacher review, with a quarantined Homework Helper behind `/helper/*`.

## Quick links
- **Start Here:** START_HERE.md
- **Deploy:** DAY1_DEPLOY_CHECKLIST.md
- **Runbook:** RUNBOOK.md
- **Security Baseline:** SECURITY_BASELINE.md
- **Privacy Addendum:** PRIVACY-ADDENDUM.md
- **Disaster Recovery:** DISASTER_RECOVERY.md
MD
fi

cat > "requirements-docs.txt" <<'REQ'
mkdocs-material==9.6.9
REQ

cat > "mkdocs.yml" <<YML
site_name: ClassHub Docs
site_url: https://bseverns.github.io/${REPO_NAME}/
repo_url: https://github.com/bseverns/${REPO_NAME}
edit_uri: edit/main/docs/

theme:
  name: material
  features:
    - navigation.sections
    - navigation.expand
    - content.code.copy
    - search.suggest
    - search.highlight

markdown_extensions:
  - admonition
  - toc:
      permalink: true

nav:
  - Home: index.md
  - Start Here: START_HERE.md
  - Deploy:
      - Day 1 Checklist: DAY1_DEPLOY_CHECKLIST.md
      - Runbook: RUNBOOK.md
      - Troubleshooting: TROUBLESHOOTING.md
  - Security & Privacy:
      - Security Baseline: SECURITY_BASELINE.md
      - Security: SECURITY.md
      - Privacy Addendum: PRIVACY-ADDENDUM.md
      - Helper Policy: HELPER_POLICY.md
  - Recovery: DISASTER_RECOVERY.md
YML

cat > ".github/workflows/docs.yml" <<'YML'
name: Deploy docs

on:
  push:
    branches: [ main ]
    paths:
      - "docs/**"
      - "mkdocs.yml"
      - "requirements-docs.txt"
      - ".github/workflows/docs.yml"

permissions:
  contents: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements-docs.txt
      - run: mkdocs build --strict
      - run: mkdocs gh-deploy --force
YML

if [ -f ".gitignore" ] && ! grep -qE '(^|/)site/$' ".gitignore"; then
  echo "site/" >> ".gitignore"
fi

echo "Docs scaffold created."
