# Quicbo Deployment Guide

This guide explains how to deploy Quicbo with maximum performance.

## Recommended Hosting: Split Deployment
To keep the **Persistent Browser** speed (~10s searches), we recommend hosting the Frontend and Backend separately.

### 1. Backend (Persistent)
We recommend **Railway**, **Render**, or **DigitalOcean**.
- **Source**: `quicbo/backend`
- **Command**: `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Dependencies**: Ensure Playwright browsers are installed (usually via a `nixpacks.toml` or `render.yaml`).
- **Optimization**: This keeps the browsers "warm" in the background.

### 2. Frontend (Fast)
Host on **Vercel**.
- **Root Directory**: `frontend`
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Environment Variables**:
    - `VITE_API_URL`: Set this to your Backend URL (e.g., `https://quicbo-backend.up.railway.app`)

---

## Alternative: All-on-Vercel (NOT RECOMMENDED)
If you must use Vercel for everything:
1. Connect the root of the repository to Vercel.
2. Vercel will use `vercel.json` to route `/api/*` requests to the Python functions.
3. **Warning**: Every search will be slow (~40s) because Vercel starts/stops the browser on every request.

## Local Development
1. **Frontend**: `npm run dev` in `/frontend`
2. **Backend**: `uvicorn main:app --reload` in `/backend`
