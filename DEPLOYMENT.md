# VoxDesk — Production Deployment Guide

Three pieces, in this order:

1. **Dashboard** → Vercel
2. **Backend** (API + Postgres + Redis + Qdrant + worker) → a VPS with Docker Compose
3. **Dograh** (voice engine) → its own VPS via the official remote script

You'll need: a GitHub account, a Vercel account, one small VPS (2GB RAM is
enough for the backend), one larger VPS for Dograh (8GB RAM / 4 vCPU minimum),
and optionally a domain name.

---

## Step 0 — Push the code to GitHub

```bash
cd voxdesk
git init && git add -A && git commit -m "VoxDesk initial release"
gh repo create voxdesk --private --source . --push
# (or create the repo on github.com and: git remote add origin <url> && git push -u origin main)
```

---

## Step 1 — Dashboard on Vercel

1. Go to <https://vercel.com/new> → **Import** the `voxdesk` repo.
2. **Root Directory**: set to `apps/web`.
3. Under *Root Directory* settings, make sure **"Include source files outside
   of the Root Directory"** is enabled (default) — the dashboard imports
   `packages/shared` from outside `apps/web`.
4. **Environment variable**: `NEXT_PUBLIC_API_URL` = `https://api.yourdomain.com`
   (your backend URL from Step 2 — you can deploy now with a placeholder and
   update it after Step 2; env changes require a redeploy).
5. Click **Deploy** → you get `https://voxdesk-<something>.vercel.app`.
6. Optional: *Settings → Domains* to attach `app.yourdomain.com`.

---

## Step 2 — Backend on a VPS (Docker Compose)

Any Ubuntu 22.04+ VPS works (Hetzner CX22, DigitalOcean 2GB, Lightsail…).

1. **DNS**: add an A record `api.yourdomain.com → <server IP>`.
   (No domain? Use `<ip-with-dashes>.sslip.io` as API_DOMAIN — resolves automatically.)

2. **Install Docker** on the server:
   ```bash
   curl -fsSL https://get.docker.com | sudo sh
   ```

3. **Clone and configure**:
   ```bash
   git clone https://github.com/<you>/voxdesk && cd voxdesk
   cp .env.example .env
   nano .env
   ```
   Change in `.env`:
   - `JWT_SECRET` → output of `openssl rand -base64 48`
   - `CORS_ORIGINS` → your Vercel URL, e.g. `https://voxdesk.vercel.app`
     (comma-add your custom domain later)
   - `API_DOMAIN` → `api.yourdomain.com`
   - Postgres password: pick a strong one, set it in **both**
     `docker-compose.yml` (`POSTGRES_PASSWORD`) and `DATABASE_URL`.

4. **Start everything** (Caddy terminates HTTPS automatically via Let's Encrypt):
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
   ```
   Migrations run automatically before the API starts.

5. **Verify**:
   ```bash
   curl https://api.yourdomain.com/health
   # {"status":"ok","service":"voxdesk-api"}
   ```

6. **Firewall** (recommended): allow only 22, 80, 443:
   ```bash
   sudo ufw allow 22 && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw enable
   ```

7. Go back to Vercel, set `NEXT_PUBLIC_API_URL=https://api.yourdomain.com`,
   redeploy. Open the dashboard, register your first organization — done.
   Everything now runs live on mock voice providers; Steps 3–4 make real
   phone calls work.

---

## Step 3 — Dograh on its own VPS

Dograh bundles its own nginx (ports 80/443), Postgres, Redis, MinIO and a
TURN server — give it a **separate** server: 8GB RAM / 4 vCPU minimum,
open ports TCP 80, 443, 3478, 5349 and UDP 3478, 5349, 49152-49200.

1. On the Dograh server (as root):
   ```bash
   curl -o setup_remote.sh https://raw.githubusercontent.com/dograh-hq/dograh/main/scripts/setup_remote.sh
   chmod +x setup_remote.sh && sudo ./setup_remote.sh
   ```
   The script asks for the server's public IP, an optional TURN password,
   deployment mode (choose **prebuilt**) and worker count (default 4).

2. Start it:
   ```bash
   cd dograh && ./remote_up.sh
   ```

3. Access the Dograh UI at `https://<ip-with-dashes>.sslip.io`
   (trusted Let's Encrypt certificate, no DNS needed). First boot pulls
   images for 2–3 minutes.

4. In the Dograh UI, create your voice workflow/agent and configure its
   webhook to point at your backend:
   `https://api.yourdomain.com/webhooks/dograh`.

5. On the **backend** server, edit `.env`:
   ```
   VOICE_ENGINE=dograh
   DOGRAH_URL=https://<your-dograh-host>
   DOGRAH_API_KEY=<key from the Dograh UI>
   ```
   then `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`.

Alternative if you don't want to manage a second VPS: Railway has a
one-click Dograh template (railway.com/deploy/dograh), and Hostinger offers
a one-click Dograh VPS image.

---

## Step 4 — Telnyx (real phone numbers)

1. Sign up at telnyx.com → **Numbers → Buy a number** (US/Canada local).
2. Create an API key (*Account → API Keys*).
3. Connect the number to Dograh's Telnyx integration (Dograh UI → telephony
   settings) so inbound audio streams to Dograh, **and/or** point the
   number's webhook at `https://api.yourdomain.com/webhooks/telnyx` for call
   lifecycle events.
4. Backend `.env`:
   ```
   TELEPHONY_PROVIDER=telnyx
   TELNYX_API_KEY=<key>
   TELNYX_PUBLIC_KEY=<public key, for webhook signature verification>
   ```
   restart compose. Register the number in the dashboard
   (*Agents → Phone numbers*) and assign it to an agent.

---

## Post-deploy checklist

- [ ] `https://api.yourdomain.com/health` returns ok
- [ ] Dashboard loads on Vercel, register + login works (CORS is right)
- [ ] Upload a knowledge doc → status `ready`
- [ ] Simulate a call → transcript, summary, recording play in the dashboard
- [ ] Dograh UI reachable, webhook pointed at `/webhooks/dograh`
- [ ] Test call to your Telnyx number reaches the agent
- [ ] `JWT_SECRET` and Postgres password are not the defaults
- [ ] Firewall on: only 22/80/443 open on the backend box

## Updating

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```
Vercel redeploys automatically on every push to `main`.
