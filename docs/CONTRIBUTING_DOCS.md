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
- Publishes with the GitHub Pages Actions flow (`configure-pages` + `upload-pages-artifact` + `deploy-pages`).
- Repo Settings > Pages should use `GitHub Actions` as the source.
- Registry-backed docs drift guard: `python3 scripts/check_docs_truth.py`
- Registry note: [DOCS_TRUTH_MECHANISM.md](DOCS_TRUTH_MECHANISM.md)

## Mermaid bundle maintenance

Docs Mermaid rendering is pinned to a repo-local asset:
- `docs/javascripts/vendor/mermaid.min.js`
- referenced by `mkdocs.yml` via `javascripts/vendor/mermaid.min.js?v=10.9.4`

Current pinned bundle:
- version: `10.9.4`
- source: `https://unpkg.com/mermaid@10.9.4/dist/mermaid.min.js`
- sha256: `1360dfc1fbdbf83466b8c49c778c17a23bbb15718c176356a7f4d2c95c54da07`

Update procedure:

```bash
curl -fL https://unpkg.com/mermaid@<version>/dist/mermaid.min.js -o docs/javascripts/vendor/mermaid.min.js
shasum -a 256 docs/javascripts/vendor/mermaid.min.js
```

After download:
1. Update the version query string in `mkdocs.yml`.
2. Update version/source/hash in this doc.
3. Run `mkdocs build --strict`.
