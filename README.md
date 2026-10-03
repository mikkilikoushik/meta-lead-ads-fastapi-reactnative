# Meta Lead Ads → FastAPI → WebSocket → React Native (PoC)

```
Meta Lead Ads Testing Tool
   → Meta Webhook (POST /webhook, signed)
   → FastAPI  → Graph API (GET /{leadgen_id})
   → SQLite   → WebSocket (/ws)
   → React Native (Expo) list updates instantly
```

## Structure

```
meta-leads-poc/
├── .gitignore
├── README.md
├── backend/
│   ├── main.py          # routes: /leads, /webhook (GET+POST), /ws
│   ├── meta.py          # signature check, Graph API fetch, field parsing
│   ├── db.py            # SQLite (dedupes by Meta lead id)
│   ├── ws_manager.py    # WebSocket broadcast
│   ├── config.py        # loads .env, fails fast if missing
│   ├── requirements.txt
│   └── .env.example
└── mobile/
    ├── App.tsx          # leads screen
    ├── index.ts
    ├── src/{config,api,types,useLeads}.ts
    ├── package.json, app.json, tsconfig.json
    └── .env.example
```

## 1. Meta setup

You need: a Facebook **Page** you admin, and a Meta developer account.

1. https://developers.facebook.com → **Create App** → use case *Other* → type *Business*.
2. In the app: **Add product → Webhooks**.
3. Copy **App secret** (App settings → Basic) → `META_APP_SECRET`.
4. Create a **Lead form** on your Page (Meta Business Suite / Ads Manager → Instant Forms). Include full name, email, phone.
5. Get a **Page access token** with `leads_retrieval`, `pages_show_list`, `pages_read_engagement`, `pages_manage_metadata`:
   - Open https://developers.facebook.com/tools/explorer, pick your app, choose *User Token*, add those permissions, **Generate Access Token**.
   - Exchange for a long-lived user token:
     ```
     curl "https://graph.facebook.com/v23.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_USER_TOKEN"
     ```
   - List pages with the long-lived token — each page comes with its own (non-expiring) token:
     ```
     curl "https://graph.facebook.com/v23.0/me/accounts?access_token=LONG_LIVED_USER_TOKEN"
     ```
   - Put the page's `access_token` in `META_PAGE_ACCESS_TOKEN`, and note its `id` (PAGE_ID).
6. Subscribe the Page to your app's `leadgen` events:
   ```
   curl -X POST "https://graph.facebook.com/v23.0/PAGE_ID/subscribed_apps" \
     -d "subscribed_fields=leadgen" -d "access_token=PAGE_ACCESS_TOKEN"
   ```
   (Do this after the webhook in step 3 below is verified, or any time — it is independent.)

While the app is in **Development mode**, Page admins/testers can use everything above without App Review.

## 2. Backend + ngrok

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # fill in the three META_* values
uvicorn main:app --host 0.0.0.0 --port 8000
```

In another terminal:

```bash
ngrok http 8000
```

Copy the `https://xxxx.ngrok-free.app` URL. **It changes each ngrok restart** (free tier), so re-enter it in Meta and in `mobile/.env` when it does.

## 3. Register the webhook in Meta

App Dashboard → **Webhooks** → object **Page** → *Subscribe to this object*:

- Callback URL: `https://xxxx.ngrok-free.app/webhook`
- Verify token: the value of `META_VERIFY_TOKEN`

Click **Verify and save** (FastAPI must be running). Then, in the Page fields list, **subscribe to `leadgen`**.

## 4. Mobile app

```bash
cd mobile
cp .env.example .env     # set EXPO_PUBLIC_API_URL to the same ngrok https URL
npm install
npx expo start           # scan the QR code with Expo Go
```

Using the ngrok URL for the app means the phone works on any network (no LAN IP needed).

> If Expo Go says the project SDK is incompatible, scaffold a fresh project with
> `npx create-expo-app@latest tmp --template blank-typescript`, then copy only `App.tsx`, `src/`
> and `.env` into it. The app uses no extra npm packages.

## 5. Test end-to-end

1. Keep the app open on the phone (status dot should be green / "live").
2. Open https://developers.facebook.com/tools/lead-ads-testing → select Page + form → **Create lead**.
3. The lead appears in the app within a second or two, with no refresh or touch.
   The tool's *Track status* shows whether Meta delivered the webhook.

## Behaviour notes

- **No polling.** Leads arrive over WebSocket only. On (re)connect the app does a single `GET /leads`
  to catch anything missed while offline; reconnects use exponential backoff.
- Webhook POSTs are rejected unless the `X-Hub-Signature-256` HMAC matches `META_APP_SECRET`.
- Meta retries webhooks, so leads are de-duplicated on `meta_lead_id`.
- Lead Testing Tool leads contain Meta's dummy values (e.g. `<test lead: dummy data for email>`); that is
  what the Graph API returns, and it is stored as-is.
- Limits of a PoC: updates arrive only while the app is foregrounded (a backgrounded OS kills sockets;
  push notifications are the production answer), broadcast is in-process (single server instance), and
  `/leads` and `/ws` are unauthenticated.

## Troubleshooting

| Symptom | Check |
|---|---|
| "Verify and save" fails | FastAPI running? ngrok URL current? Verify token identical? |
| Webhook hits but no lead stored | Backend log: Graph API error → token missing `leads_retrieval`, or wrong page token |
| 403 Invalid signature | `META_APP_SECRET` is for a different app |
| Test tool creates lead, nothing arrives | Page not subscribed (step 1.6) or `leadgen` field not subscribed (step 3) |
| App stuck on "offline" | `EXPO_PUBLIC_API_URL` wrong; restart Expo after editing `.env` (`npx expo start -c`) |
