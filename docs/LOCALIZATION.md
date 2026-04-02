# Localization (i18n)

ClassHub supports multiple UI languages through Django's built-in i18n framework. This document explains how to add or update translations.

## Quick reference

| Task | Command |
|---|---|
| Extract new strings | `python manage.py makemessages -l <code>` |
| Compile translations | `python manage.py compilemessages` |
| Check Spanish/Somali parity | `python3 scripts/check_i18n_spanish_somali_parity.py` |
| Optional fallback budget gate | `CLASSHUB_I18N_SO_MAX_IDENTICAL=80 python3 scripts/check_i18n_spanish_somali_parity.py` |
| Add a new language | See [Adding a Language](#adding-a-language) below |

## How it works

1. **Template strings** are wrapped in `{% trans "..." %}` or `{% blocktrans %}...{% endblocktrans %}` tags.
2. **Python strings** (views, forms, validation messages) use `gettext()` or `gettext_lazy()`.
3. Django's `makemessages` command scans for these markers and produces `.po` files.
4. Translators edit the `.po` files to provide translations.
5. `compilemessages` compiles `.po` → `.mo` (binary) for runtime use.

## Where strings live

| Location | What to mark | Tag/function |
|---|---|---|
| `templates/*.html` | Labels, headings, help text | `{% trans %}`, `{% blocktrans %}` |
| `hub/views/*.py` | Error messages, validation text | `from django.utils.translation import gettext as _` |
| `hub/services/*.py` | User-facing validation messages | `gettext_lazy()` for module-level strings |

## Current coverage

Translations are provided for:
- student join page (`/`)
- teacher login page (`/teach/login`)
- student class page chrome and activity labels (`/student`)
- student data controls page (`/student/my-data`)
- student portfolio pages (`/student/portfolio`, export shell copy)
- student gallery page (`/student/gallery`)
- teacher day-of-class portal headings and digest/closeout labels (`/teach?portal_mode=day`)

Languages currently shipped:
- English (default)
- Spanish (`es`)
- Somali (`so`)
- S'gaw Karen (`ksw`)

Coverage outside those paths is still partial and should be treated as in-progress.

Karen-language implementation note:
- The repo now uses S'gaw Karen (`ksw`) as the concrete "Karen" locale code.
- `ksw` ships with full locale wiring plus a first translated helper-widget tranche (chrome + quick prompts), so Django language selection, cookies, helper routing, and widget locale payloads work end-to-end.
- Wider `ksw` UI coverage is still partial; untranslated strings continue to fall back to English until native-speaker-reviewed Karen copy is added.

Somali parity policy:
- Somali should include every `msgid` that exists in Spanish.
- New strings should not land in Spanish without a non-empty Somali entry.
- Where a reviewed Somali translation is not ready yet, keep a non-empty fallback entry and follow up with language review.

## Family-visible first tranche

Localization completion is intentionally bounded to a family-visible tranche so progress is enforceable:

- Student class experience: `/student`
- Teacher day-of-class workflow shell: `/teach?portal_mode=day`

Contract guard:

```bash
python3 scripts/check_i18n_family_visible_contract.py
```

The guard fails if any of the following drift:
- tranche definition markers in this doc
- required i18n tests in `hub.tests.test_i18n`
- required `{% trans %}`/`{% blocktrans %}` coverage in the route templates
- required non-empty tranche translations in:
  - `locale/es/LC_MESSAGES/django.po`
  - `locale/so/LC_MESSAGES/django.po`

Parity guard:

```bash
python3 scripts/check_i18n_spanish_somali_parity.py
```

This guard fails if Somali is missing any Spanish `msgid`, or if a Somali entry is empty.
It also prints a non-blocking LANTERN metric showing how many Somali entries are still identical to English fallback copy.

Optional stricter mode:
- Set `CLASSHUB_I18N_SO_MAX_IDENTICAL` to enforce a maximum fallback count.
- Example: `CLASSHUB_I18N_SO_MAX_IDENTICAL=80 python3 scripts/check_i18n_spanish_somali_parity.py`

Human review packet (trust-critical strings):
- [LOCALIZATION_SO_REVIEW_PACKET.md](LOCALIZATION_SO_REVIEW_PACKET.md)

## Adding a language

1. **Register the language** in `config/settings.py`:
   ```python
   LANGUAGES = [
       ("en", "English"),
       ("es", "Español"),
       ("fr", "Français"),  # ← add here
   ]
   ```

2. **Create the locale directory and extract strings**:
   ```bash
   python manage.py makemessages -l fr
   ```
   This creates `locale/fr/LC_MESSAGES/django.po`.

3. **Translate** — edit the `.po` file. Each entry has a `msgid` (English source) and `msgstr` (translation). Fill in the `msgstr` values.

4. **Compile**:
   ```bash
   python manage.py compilemessages --locale=fr
   ```

5. **Test** — visit the join page and switch languages using the chooser, or set `Accept-Language: fr` in your browser.

## Language chooser

A lightweight `<form>` that POSTs to Django's `/i18n/setlang/` view. It appears on:
- Student join page (`/`)
- Teacher login page (`/teach/login`)

The chooser uses no inline JS and respects CSP. Language choice is persisted via Django's session/cookie mechanism.

## Testing translations

```bash
# Run all i18n tests
python manage.py test hub.tests.test_i18n --verbosity=2

# Manual: visit the join page with a Spanish browser
curl -H "Accept-Language: es" http://localhost:8000/
```

## Accessibility notes

- The `<html lang>` attribute is set dynamically to match the active language.
- The language chooser label uses `sr-only` for screen readers.
- **RTL support**: not currently implemented. If a future language requires RTL (e.g., Arabic), additional CSS work will be needed. The scaffold does not block this.

## CI/build reminder

If you modify translatable strings, remember to:
1. Run `makemessages` to update `.po` files
2. Update translations in the `.po` files
3. Run `compilemessages` to regenerate `.mo` files
4. Commit both `.po` and `.mo` files
