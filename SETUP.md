# Setup Guide

Step-by-step instructions for getting the sermon translator running end-to-end.

---

## Prerequisites

- Python 3.11+, Node.js 20+, `uv` installed
- NVIDIA GPU with CUDA (for ML inference) — CPU fallback works but latency will be high
- A free [Cloudflare account](https://dash.cloudflare.com/sign-up) + a domain (or use a free `trycloudflare.com` tunnel for testing)
- Free [API.Bible key](https://scripture.api.bible/) for multi-translation Bible lookup

---

## 1. Environment Variables

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and fill in:

| Variable | How to get it |
|---|---|
| `SECRET_KEY` | Run `openssl rand -hex 32` — paste the output |
| `BIBLE_API_KEY` | Register at [scripture.api.bible](https://scripture.api.bible/), create an app, copy the API key |
| `FRONTEND_ORIGIN` | Your frontend URL — `http://localhost:3000` for local dev, or your Cloudflare Pages URL for production |
| `WHISPER_DEVICE` | `cuda` if GPU is available, `cpu` otherwise |
| `NLLB_DEVICE` | Same as above |

All other settings have sensible defaults.

---

## 2. Backend: Core Dependencies

```bash
cd backend
uv sync
```

This installs FastAPI, SQLAlchemy, auth libraries — everything except the ML stack.

---

## 3. ML Models (requires GPU)

Install the ML extras (torch, faster-whisper, NLLB, aiortc):

```bash
uv sync --extra ml
```

> Skip this step if you're only testing auth/sessions/WebSocket without live audio. The server starts without ML deps — STT and translation will simply fail at runtime.

### Download faster-whisper model

On first STT request, faster-whisper auto-downloads the model to `~/.cache/huggingface/hub/`. To pre-download:

```bash
# From the backend virtualenv
uv run python -c "
from faster_whisper import WhisperModel
WhisperModel('medium', device='cuda', compute_type='float16')
print('Whisper ready')
"
```

Swap `medium` for `large-v3` if your GPU has ≥10 GB VRAM for better accuracy.

> Update `WHISPER_MODEL=large-v3` in `.env` after downloading if you change the size.

### Download NLLB translation model

```bash
uv run python -c "
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
AutoTokenizer.from_pretrained('facebook/nllb-200-distilled-600M')
AutoModelForSeq2SeqLM.from_pretrained('facebook/nllb-200-distilled-600M')
print('NLLB ready')
"
```

Models are cached in `~/.cache/huggingface/hub/`. Combined download ~2.5 GB.

**License note:** NLLB-200 is CC-BY-NC 4.0 (non-commercial only). Fine for free church use. If this project is ever monetized, swap to MADLAD-400 (Apache 2.0) — the `Translator` protocol in `backend/app/pipeline/translate.py` makes this a one-file change.

---

## 4. Frontend

```bash
cd frontend
npm install
```

---

## 5. Running Locally

Two terminals:

```bash
# Terminal 1 — backend
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

- **Attendee view:** enter any session code
- **Admin console:** [http://localhost:3000/admin](http://localhost:3000/admin) → Register → Create session → Start

---

## 6. Cloudflare Tunnel (Production / Remote Access)

This exposes your home server over HTTPS without port forwarding.

### Install cloudflared

```bash
# Arch / Manjaro
yay -S cloudflared

# Debian / Ubuntu
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb
```

### Authenticate and create tunnel

```bash
cloudflared tunnel login                          # opens browser, authorizes your domain
cloudflared tunnel create sermon-translator       # note the tunnel ID printed
cloudflared tunnel route dns sermon-translator api.yourdomain.com
```

### Configure the tunnel

Edit `infra/cloudflared.yml`:

```yaml
tunnel: <paste-tunnel-id-here>
credentials-file: /home/<your-username>/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: api.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
```

Update `FRONTEND_ORIGIN` in `backend/.env` to match your Cloudflare Pages URL.

### Test the tunnel

```bash
cloudflared tunnel --config infra/cloudflared.yml run
```

### Install as systemd services (runs on boot)

```bash
# Copy service files
sudo cp infra/systemd/translator-backend.service /etc/systemd/system/
sudo cp infra/systemd/cloudflared.service /etc/systemd/system/

# Edit paths in both files to match your username and repo location
sudo nano /etc/systemd/system/translator-backend.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable --now translator-backend cloudflared
sudo systemctl status translator-backend cloudflared
```

---

## 7. Frontend Deploy (Cloudflare Pages)

```bash
# Build
cd frontend
npm run build

# Deploy via Wrangler (one-time setup)
npx wrangler pages deploy out --project-name sermon-translator
```

Or connect the GitHub repo in the Cloudflare Pages dashboard for automatic deploys on push.

Set the environment variable `NEXT_PUBLIC_API_URL=https://api.yourdomain.com` in the Pages project settings.

---

## 8. End-to-End Verification

1. Open the attendee URL on a phone (cellular, not WiFi to your server) — enter a session code
2. On the admin page, create a session and click **Start**
3. Speak: captions should appear within ~3 seconds
4. Say **"Turn with me to John 3 verse 16"** — a Bible verse popover should appear
5. Switch the language picker mid-stream — the next caption should be in the new language

---

## GPU Memory Reference

| Model | VRAM |
|---|---|
| Whisper `medium` | ~2.5 GB |
| Whisper `large-v3` | ~6 GB |
| NLLB-200 distilled 600M | ~1.5 GB |
| **Total (medium + NLLB)** | **~4 GB** |
| **Total (large-v3 + NLLB)** | **~7.5 GB** |

---

## Troubleshooting

**Backend won't start:** `SECRET_KEY` not set — run `openssl rand -hex 32` and add to `.env`.

**STT import error at startup:** ML extras not installed — run `uv sync --extra ml`.

**Captions appear in English regardless of language picker:** Check that `NLLB_DEVICE=cuda` and the model downloaded correctly.

**WebRTC offer fails:** Browser must be on HTTPS (or localhost) to access the microphone — don't test the admin page over plain HTTP on a remote host.

**Cloudflare tunnel disconnects:** Add `--loglevel debug` to the cloudflared command to diagnose. Ensure the service file `WorkingDirectory` points to the correct path.
