# Deploying Legal-Eye

Two pieces, two hosts. This is not a workaround, it is the correct shape for
this stack.

| Piece | What it is | Where it goes |
|---|---|---|
| `site/` | Static HTML: landing page, terms, privacy notice, `llms.txt`, `robots.txt`, `sitemap.xml` | Vercel |
| `frontend/streamlit_app.py` plus `backend/` | The Streamlit app | Streamlit Community Cloud, Render, Railway or a VM |

## Why the app cannot go on Vercel

Vercel runs short-lived serverless functions. Streamlit is a long-running server
that holds a WebSocket open for every user and keeps session state in memory
between interactions. There is no entrypoint setting, `vercel.json` change or
Python runtime option that reconciles those two models. The
`No python entrypoint found` error is Vercel detecting `requirements.txt` at the
repository root and trying to build a Python serverless function. Even if that
error is silenced, the app will not run.

## 1. Vercel, for the static site

In the Vercel project settings, set:

- **Root Directory:** `site`
- **Framework Preset:** Other
- **Build Command:** leave empty
- **Output Directory:** leave empty

Setting the root directory to `site` is what actually fixes the build error.
Vercel then never sees `requirements.txt`, stops detecting a Python project, and
serves the folder as static files. `site/vercel.json` supplies clean URLs,
security headers and the `/app` redirect.

## 2. Streamlit Community Cloud, for the app

Free, and it is the path of least resistance for a Streamlit app.

1. Sign in at share.streamlit.io with the GitHub account that owns the repo.
2. New app, pick `LizaliseSiveNzo/legal-eye`, branch `main`.
3. Main file path: `frontend/streamlit_app.py`
4. Under Advanced settings, add the secrets. These are the same names as
   `.env`, and they must never be committed:

   ```toml
   DEEPSEEK_API_KEY = "..."
   PAYMENT_PROVIDER = "dev"
   PAYMENTS_ALLOW_DEV = "false"
   EMAIL_PROVIDER = "console"
   REPORT_PRICE_CENTS = "9900"
   ```

5. Deploy, then copy the resulting URL.

Alternatives if you outgrow it: Render or Railway both run a long-lived process
and take a start command of
`streamlit run frontend/streamlit_app.py --server.port $PORT --server.address 0.0.0.0`.

### One caveat on Community Cloud

Tesseract is not installed there, so scanned PDFs will report that OCR is
unavailable. Add a `packages.txt` at the repository root containing
`tesseract-ocr` to have it installed. Render and Railway need it in the
Dockerfile or build command instead.

## 3. Join the two together

Edit `site/vercel.json` and replace `REPLACE-ME.streamlit.app` in both redirects
with the URL from step 2. Redeploy Vercel. `legal-eye.co.za/app` then sends
visitors to the app, and every other path is served statically.

A redirect is used rather than a proxy rewrite deliberately. Proxying Streamlit
through Vercel breaks its WebSocket connection, and the app fails in ways that
are tedious to debug. The visible URL changes, which is a fair trade.

## 4. Before you point the domain at it

- Fill the highlighted placeholders in `terms.html` and `privacy.html`.
- Add DNS records for the domain in Vercel.
- Add SPF, DKIM and DMARC records for the email sending domain, or delivered
  reviews will land in spam.
- Confirm `PAYMENTS_ALLOW_DEV` is `false` in production. With it true, reviews
  are delivered without taking payment.
