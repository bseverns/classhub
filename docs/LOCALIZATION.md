# Localization (i18n)

ClassHub supports multiple UI languages through Django's built-in i18n framework. This document explains how to add or update translations.

## Quick reference

| Task | Command |
|---|---|
| Extract new strings | `python manage.py makemessages -l <code>` |
| Compile translations | `python manage.py compilemessages` |
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

Translations are provided for the **student join page** and **teacher login page**:
- English (default)
- Spanish (`es`)

Other pages render in English. The scaffold is ready to expand.

## Adding a language

1. **Register the language** in `config/settings.py`:
   ```python
   LANGUAGES = [
       ("en", "English"),
       ("es", "Español"),
       ("so", "Soomaali"),  # ← add here
   ]
   ```

2. **Create the locale directory and extract strings**:
   ```bash
   python manage.py makemessages -l so
   ```
   This creates `locale/so/LC_MESSAGES/django.po`.

3. **Translate** — edit the `.po` file. Each entry has a `msgid` (English source) and `msgstr` (translation). Fill in the `msgstr` values.

4. **Compile**:
   ```bash
   python manage.py compilemessages --locale=so
   ```

5. **Test** — visit the join page and switch languages using the chooser, or set `Accept-Language: so` in your browser.

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
