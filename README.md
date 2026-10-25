# Radiant Billing (Android)

Quotations, invoices and delivery notes for Radiant Lighting, Multan, as an Android app.
Everything is stored on the phone; nothing needs a server.

## Get the app
Every push to `main` builds a signed APK with GitHub Actions.
Open **Releases** → newest **Radiant Billing 1.0.N** → download the `.apk` on the phone → open it
(allow "Install unknown apps" for your browser/Files once). New builds install over the old one and keep your data.

## What's inside
- `src/app.src.html` — the app (same as the claude.ai web version)
- `src/platform.js` — phone layer: local database, photos, share sheet (WhatsApp), AI provider, backup/restore
- `src/localitems.js` — built-in order reader ("45 trail 4850") that works without AI
- `src/seed.json`, `src/img/` — products, customers, settings and documents from the web app (loaded on first launch)
- `tools/build_www.py` — builds `www/` from `src/`
- `android/` — Capacitor Android project
- `.github/workflows/android.yml` — APK build

## AI (optional)
Settings → AI for new items. Pick a provider (Groq, Gemini, OpenRouter, DeepSeek, OpenAI, Anthropic or any
OpenAI-compatible API) and paste a key. The key is stored only on the phone. Without a key, built-in matching is used.

## Build locally (optional)
```
npm ci
npm run sync            # builds www/ and copies it into android/
cd android && ./gradlew assembleRelease
```
Preview in a browser: `npm run serve` → http://localhost:8765

## Before a Play Store release
`android/app/radiant-test.keystore` is a test signing key committed so updates install cleanly.
Create a new private key, keep it out of the repo (GitHub secret), and update `android/app/build.gradle`.
The seed data includes your bank details; keep this repo private.
