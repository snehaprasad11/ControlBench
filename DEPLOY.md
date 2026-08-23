# Deploying LockBench

LockBench deploys as **one service** (the FastAPI backend serves the built React app),
so you get **one URL** for the whole thing — no separate frontend host, no CORS setup,
no environment variables to wire up.

## Deploy on Render (free)

1. Push the repo to GitHub (already done).
2. Go to <https://render.com> and sign in with GitHub.
3. Click **New +** → **Web Service**.
4. Connect and select the **ControlBench** repo.
5. Render detects the `Dockerfile` and fills everything in automatically.
   Leave the defaults, set **Instance Type = Free**, click **Create Web Service**.
6. Wait for the first build (~5–8 min — it builds the React app and the Python image).
7. When it says **Live**, copy the URL, e.g. `https://lockbench.onrender.com`.
   **That URL is the whole app** — open it and the UI loads and talks to its own API.

> You can also use **New + → Blueprint** instead of step 3–5; Render reads `render.yaml`
> and configures the same service. Either way works.

### Verify it

- `https://<your-url>/` → the app UI.
- `https://<your-url>/api/health` → `{"status":"ok","ml_model_loaded":true}`.

### Free-tier note (important)

The free instance **sleeps after ~15 min idle**, so the *first* visit after it's been
idle takes ~30–50 s to wake up. LockBench shows a "Waking the backend…" message during
that time (by design), then loads normally. Every visit after that is fast.

To avoid cold starts entirely, upgrade to a paid Render instance, or host the same
Dockerfile on another platform (Fly.io, Railway) — the container is portable.

## Share it

Your public link is the Render URL. Put it in the README header (top of the file) and on
your resume/transcript.
