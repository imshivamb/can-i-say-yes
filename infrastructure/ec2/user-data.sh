#!/bin/bash
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3.12-venv python3-pip git
if [ ! -f /swapfile ]; then
  fallocate -l 1G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
fi
swapon /swapfile || true
grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
install -d /opt
if [ ! -d /opt/can-i-say-yes/.git ]; then
  git clone --depth 1 https://github.com/imshivamb/can-i-say-yes.git /opt/can-i-say-yes
else
  git -C /opt/can-i-say-yes pull --ff-only
fi
install -d /opt/can-i-say-yes/data/runtime
if [ ! -f /opt/can-i-say-yes/data/runtime/clock.json ]; then
  printf '%s\n' '{"now":"2026-09-12T09:00:00+05:30","timezone":"Asia/Kolkata"}' \
    > /opt/can-i-say-yes/data/runtime/clock.json
fi
python3.12 - <<'PY'
from pathlib import Path

path = Path("/opt/can-i-say-yes/agent/server.py")
text = path.read_text()
if "unhandled_error" not in text:
    text = text.replace(
        "from fastapi import FastAPI, HTTPException",
        "import traceback\nfrom fastapi import FastAPI, HTTPException, Request\n"
        "from fastapi.responses import JSONResponse",
    )
    marker = 'app = FastAPI(title="Can I Say Yes?", version="0.2.0")\n'
    handler = marker + """

@app.exception_handler(Exception)
async def unhandled_error(_request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        raise exc
    detail = {"detail": str(exc)}
    if os.getenv("CISAY_DEBUG", "").lower() in {"1", "true", "yes"}:
        detail["traceback"] = traceback.format_exc()
    return JSONResponse(status_code=500, content=detail)

"""
    if marker not in text:
        raise SystemExit("server.py FastAPI marker missing")
    path.write_text(text.replace(marker, handler, 1))
PY
python3.12 -m venv /opt/cisay-venv
/opt/cisay-venv/bin/pip install --upgrade pip
/opt/cisay-venv/bin/pip install -e /opt/can-i-say-yes
cat >/etc/systemd/system/cisay.service <<'UNIT'
[Unit]
Description=Can I Say Yes API
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/can-i-say-yes
Environment=CISAY_RECORDED=0
Environment=CISAY_BEDROCK_MODEL=zai.glm-4.7-flash
Environment=AWS_REGION=us-east-1
Environment=CISAY_DATA_DIR=/opt/can-i-say-yes/data
Environment=CISAY_CORS_ORIGINS=https://can-i-say-yes.vercel.app,http://localhost:3000
Environment=CISAY_DEBUG=1
ExecStart=/opt/cisay-venv/bin/uvicorn agent.server:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now cisay
