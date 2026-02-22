# Docs Development

## Summary
Use this page for local MkDocs setup and verification before pushing docs changes.

## What to do now
1. Create a Python virtual environment.
2. Install docs dependencies.
3. Run local serve/build checks.

## Verification signal
`mkdocs build --strict` exits with code `0`.

## Local setup

```bash
cd /path/to/ClassHub
python -m venv .venv_docs
source .venv_docs/bin/activate
pip install -r requirements-docs.txt
```

## Run docs locally

```bash
mkdocs serve
```

Open the local URL shown in terminal (usually `http://127.0.0.1:8000`).

## Strict build check

```bash
mkdocs build --strict
```

## CI workflow

- Docs deploy workflow: `.github/workflows/docs.yml`
- Triggered when docs files, `mkdocs.yml`, or `requirements-docs.txt` change.
