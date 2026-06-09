#!/usr/bin/env bash
set -euo pipefail

# ── Konfiguration ─────────────────────────────────────────────────────────────
HOST="dedivirt2229.your-server.de"
USER="inform"
PORT="22"
REMOTE_DIR="public_html/app.modellschule.digital/chat"
STREAMLIT_PORT="8767"
LOCAL_ENV="deploy.local.env"

if [[ -f "${LOCAL_ENV}" ]]; then
  # shellcheck disable=SC1090
  source "${LOCAL_ENV}"
fi

SSH="ssh -p ${PORT} -o PreferredAuthentications=password -o PubkeyAuthentication=no"
SCP="scp -P ${PORT} -o PreferredAuthentications=password -o PubkeyAuthentication=no"

run_remote() {
  local cmd="$1"
  expect -c "
    log_user 1
    set timeout 120
    spawn ${SSH} ${USER}@${HOST} {${cmd}}
    expect -re {password:} { send \"${DEPLOY_PASSWORD}\r\" }
    expect eof
  "
}

run_scp() {
  local src="$1"
  local dst="$2"
  expect -c "
    log_user 1
    set timeout 60
    spawn ${SCP} -r ${src} ${USER}@${HOST}:${dst}
    expect -re {password:} { send \"${DEPLOY_PASSWORD}\r\" }
    expect eof
  "
}

echo "▶ Deploying Chat-App nach ${USER}@${HOST}:${REMOTE_DIR}"

# ── 1. Verzeichnisstruktur anlegen ────────────────────────────────────────────
echo "  → Verzeichnisse anlegen …"
run_remote "mkdir -p ${REMOTE_DIR}/chat_logs ${REMOTE_DIR}/pdf_exports ${REMOTE_DIR}/.streamlit"

# ── 2. Dateien übertragen ─────────────────────────────────────────────────────
echo "  → Dateien übertragen …"
for f in app.py requirements.txt chat_config.json; do
  run_scp "${f}" "${REMOTE_DIR}/${f}"
done
run_scp ".streamlit/config.toml" "${REMOTE_DIR}/.streamlit/config.toml"

# .env übertragen (wenn .env.production existiert, sonst .env)
if [[ -f ".env.production" ]]; then
  run_scp ".env.production" "${REMOTE_DIR}/.env"
elif [[ -f ".env" ]]; then
  run_scp ".env" "${REMOTE_DIR}/.env"
else
  echo "  ⚠️  Keine .env-Datei gefunden – bitte manuell auf dem Server anlegen."
fi

# ── 3. Python-Umgebung einrichten & Streamlit starten ─────────────────────────
echo "  → Python-Umgebung + Streamlit …"
run_remote "
  cd ${REMOTE_DIR}
  python3 -m venv .venv 2>/dev/null || true
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt

  # Alten Prozess stoppen (falls läuft)
  if [[ -f streamlit.pid ]]; then
    kill \$(cat streamlit.pid) 2>/dev/null || true
    rm -f streamlit.pid
  fi

  # Streamlit als Daemon starten
  nohup .venv/bin/streamlit run app.py \
    --server.port ${STREAMLIT_PORT} \
    --server.address 127.0.0.1 \
    --server.headless true \
    --server.baseUrlPath /chat \
    > streamlit.log 2>&1 &
  echo \$! > streamlit.pid
  echo 'Streamlit gestartet (PID: '\$(cat streamlit.pid)').'
"

# ── 4. .htaccess für Apache-Proxy (HTTP + WebSocket) ──────────────────────────
echo "  → .htaccess Reverse-Proxy konfigurieren …"
run_remote "cat > ${REMOTE_DIR}/.htaccess << 'HTACCESS'
Options -Indexes
RewriteEngine On

# WebSocket-Proxy (Streamlit braucht das für Echtzeit-Updates)
RewriteCond %{HTTP:Upgrade} websocket [NC]
RewriteCond %{HTTP:Connection} upgrade [NC]
RewriteRule ^(.*)$ ws://127.0.0.1:${STREAMLIT_PORT}/\$1 [P,L]

# HTTP-Proxy
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)$ http://127.0.0.1:${STREAMLIT_PORT}/\$1 [P,L]
HTACCESS
echo '.htaccess gesetzt.'
"

echo ""
echo "✓ Deploy abgeschlossen!"
echo "  URL: https://app.modellschule.digital/chat/"
echo ""
echo "  Hinweis: Apache braucht mod_proxy, mod_proxy_http und mod_proxy_wstunnel."
echo "  Falls /chat nicht erreichbar: Hosting-Panel prüfen."
