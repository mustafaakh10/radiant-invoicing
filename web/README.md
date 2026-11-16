# Radiant Billing: web app (Django)

Quotations, invoices, delivery notes and purchase orders for Radiant Lighting, as a normal website
you sign in to from any phone or computer. It is the same app as the Android build and the claude.ai
version: one source (`src/app.src.html`), three builds.

```
radiant-invoicing/
  src/app.src.html        the app (screens, PDF, quick entry), shared by every build
  src/platform_web.js     web layer: talks to this Django server
  src/platform.js         Android layer: stores everything on the phone
  tools/build_www.py      builds the app: `--web` for this server, no flag for Android
  web/                    this Django project
    billing/              data API, photo uploads, AI proxy, backup/import
    billing/static/app/   the built app (generated, don't edit by hand)
```

## Run it on your laptop

```bash
cd web
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser          # your login
python manage.py runserver
```

Open http://localhost:8000 and sign in. Without `RL_SECRET_KEY` set, it runs in debug mode.

After changing anything in `src/`, rebuild the app:

```bash
python tools/build_www.py --web           # from the repo root
```

## Bring your data over

Any Radiant Billing backup file works: one downloaded from this site, the Android app's
"Share backup file", or an export of the claude.ai version. Photos come along and are re-linked.

```bash
python manage.py import_backup path/to/backup.json      # replaces everything
python manage.py import_backup path/to/backup.json --keep   # merges instead
```

Or use **Settings → Backup & restore → Restore from file** in the app.

## AI (optional)

Settings → **AI assistant**. Pick a provider (Groq and Gemini have free tiers; OpenAI, Claude,
DeepSeek, OpenRouter or any OpenAI-compatible API also work), paste the key, **Save & test**.

- The key is stored in the server database and never sent to the browser.
- The built-in matcher places most lines without AI. Only lines it can't place are sent.
- Each call sends only the products that share words with the text (one short line each, up to 12)
  instead of the whole catalogue: about 220 tokens instead of about 5,500 with 63 products.
- Replies are capped and use short JSON keys.
- The same entry twice is answered from the server's memory (cache) at no cost.
- Optional monthly token limit; usage this month is shown in Settings and in the admin panel.

## Put it online (later)

Environment variables for the server:

| Variable | Example |
|---|---|
| `RL_SECRET_KEY` | a long random string |
| `RL_ALLOWED_HOSTS` | `billing.radiantlighting.pk,yourname.pythonanywhere.com` |
| `RL_CSRF_ORIGINS` | `https://billing.radiantlighting.pk` |

Then `python manage.py migrate`, `python manage.py collectstatic`, create your login and point
the host's WSGI file at `radiant_web.wsgi`. Photos are saved in `web/media/` and served only to
signed-in users. Back up `db.sqlite3` and `media/` (or use the in-app backup).

Note: free PythonAnywhere accounts can only call an allow-list of outside sites, so check the
AI provider you pick is reachable from there (Settings → AI assistant → Save & test tells you).

## Tests

```bash
cd web && python manage.py test billing
```
