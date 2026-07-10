# Deploying the dashboard to Vercel

One-time setup (~3 minutes, requires your Vercel account):

1. Go to [vercel.com/new](https://vercel.com/new) and **Import** the GitHub repo
   `manavm-afk/Data-Center-Sustainability-Analysis` (authorize the Vercel GitHub
   app for this repo when prompted).
2. In the import screen:
   - **Framework preset:** Next.js (auto-detected)
   - **Root Directory:** `web`  ← required
   - Under *Build and Output Settings*, confirm
     **"Include source files outside of the Root Directory"** is **enabled**
     (default). The prebuild step copies `../web-data/` into `public/data/`,
     so the build needs the full repo checkout.
3. Deploy. Every push to `main` auto-deploys; PRs get preview URLs.

No environment variables are needed — the app is fully static against the
committed `web-data/` JSON layer. When the pipeline re-runs, commit the
regenerated `web-data/` and the next deploy picks it up.

> **Gotcha:** after changing **Root Directory**, don't use *Redeploy* on an old
> failed deployment — trigger a fresh build with a new push to `main` (any
> commit). Redeploys of a pre-fix deployment can keep failing with the Python
> entrypoint error.
