# Deploying ControlBench

The app has two parts, deployed separately and for free:

* **Backend** (FastAPI + ML models) -> **Render**
* **Frontend** (React build) -> **Vercel**, which proxies `/api` to the backend.

Deploy the backend first (you need its URL for the frontend).

---

## 1. Backend on Render

1. Push everything to GitHub (see the commit block your assistant provided).
2. Go to <https://render.com> and sign in with GitHub.
3. **New +** -> **Blueprint** -> select the `ControlBench` repo.
   Render reads `render.yaml` and configures the service automatically.
   *(Or **New + -> Web Service** and set: Runtime `Python`, Build
   `pip install -r requirements.txt`, Start
   `uvicorn api.main:app --host 0.0.0.0 --port $PORT`, Plan `Free`, and env var
   `PYTHON_VERSION = 3.12.7`.)*
4. Click **Apply / Create** and wait for the first build (~3-5 min).
5. Copy the service URL, e.g. `https://controlbench-api.onrender.com`.
6. Verify it works: open `<that URL>/docs` (the Swagger UI) or `/api/health`.

> **Free-tier note:** the service sleeps after ~15 minutes of inactivity, so the
> first request after idle takes ~30-50s to wake. Subsequent requests are fast.

---

## 2. Frontend on Vercel

The frontend is a **pure static site** that calls the backend directly using the
`VITE_API_BASE` environment variable. No proxy/rewrite is needed.

1. Go to <https://vercel.com>, **Add New -> Project**, import the `ControlBench` repo.
2. **Root Directory = `frontend`** (important — this is the React app). Vercel
   auto-detects Vite (Build `npm run build`, Output `dist`).
3. **Environment Variables** -> add:
   - Name: `VITE_API_BASE`
   - Value: your Render URL from step 1.5, e.g. `https://controlbench-api.onrender.com`
     (no trailing slash, no `/api`).
4. **Do NOT add any "Rewrite" that sends `/` or `/(.*)` to the backend** — that
   would replace the React app with the API. Only the env var above is needed.
5. Click **Deploy**. You get a URL like `https://control-bench.vercel.app`.
6. Open it — the React UI loads and calls the Render backend directly (CORS is open
   on the backend by default).

> **Already deployed and seeing `{"detail":"Not Found"}`?** That means every path is
> being proxied to the backend. Fix it by: Project **Settings -> Rewrites/Redirects**,
> delete any catch-all to the backend; confirm **Root Directory = `frontend`**; add the
> `VITE_API_BASE` env var above; then **Redeploy**. (Re-creating the Vercel project from
> scratch with these settings is the most reliable reset.)

---

## 3. Share it

Your public link is the **Vercel URL**. Put it in the README and your resume.

If the very first load is slow, that's the Render backend waking up — reload once
it's warm. To avoid cold starts entirely, upgrade the Render plan or switch to a
single-container host (ask the assistant to generate a `Dockerfile`).
