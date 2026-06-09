#!/usr/bin/env bash
set -euo pipefail

# ── Konfiguration ─────────────────────────────────────────────────────────────
LOCAL_ENV="deploy.local.env"
if [[ -f "${LOCAL_ENV}" ]]; then source "${LOCAL_ENV}"; fi

HOST="dedivirt2229.your-server.de"
USER="inform"
PORT="22"
APP_DIR="public_html/app.modellschule.digital"   # Web-Root der Subdomain
STREAMLIT_PORT="8767"

SCP_OPTS="-P ${PORT} -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=no"

scp_up() {
  local src="$1" dst="$2"
  expect -c "
    log_user 1
    set timeout 120
    spawn scp ${SCP_OPTS} ${src} ${USER}@${HOST}:${dst}
    expect -re {password:} { send \"${DEPLOY_PASSWORD}\r\" }
    expect eof
  "
}

echo "▶ Chat-App → https://app.modellschule.digital/chat/"

# ── 1. Tarball bauen ──────────────────────────────────────────────────────────
echo "  → Paket schnüren …"
tar --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='deploy.local.env' \
    --exclude='.venv' \
    --exclude='chat_logs' \
    --exclude='pdf_exports' \
    --exclude='pdf_archiv' \
    --exclude='add ons' \
    --exclude='.claude' \
    --exclude='.idea' \
    --exclude='*.xlsx' \
    -czf /tmp/chat_deploy.tar.gz \
    -C "$(pwd)" .

cp "$(pwd)/.env" /tmp/chat_deploy.env

# ── 2. restart.php generieren ─────────────────────────────────────────────────
RESTART_TMP=$(mktemp /tmp/chat_restart_XXXX.php)
cat > "${RESTART_TMP}" << 'RESTARTEOF'
<?php
header('Content-Type: text/plain; charset=utf-8');
$app      = __DIR__ . '/chat';
$port     = 8767;
$pid_file = $app . '/streamlit.pid';
if (file_exists($pid_file)) {
    $pid = (int) file_get_contents($pid_file);
    if ($pid > 0) { exec("kill $pid 2>/dev/null"); sleep(1); }
    @unlink($pid_file);
}
$streamlit = $app . '/.venv/bin/streamlit';
$log       = $app . '/streamlit.log';
$cmd = "cd $app && nohup $streamlit run app.py"
     . " --server.port $port"
     . " --server.address 127.0.0.1"
     . " --server.headless true"
     . " --server.baseUrlPath /chat"
     . " > $log 2>&1 & echo \$! > $pid_file";
exec($cmd);
sleep(2);
echo file_exists($pid_file)
    ? '✓ Streamlit gestartet (PID: ' . trim(file_get_contents($pid_file)) . ')'
    : '✗ Start fehlgeschlagen – chat/streamlit.log prüfen';
RESTARTEOF

# ── 3. setup.php generieren ───────────────────────────────────────────────────
PHP_TMP=$(mktemp /tmp/chat_setup_XXXX.php)
# Streamlit-Port als Shell-Variable einsetzen, Rest ist PHP (kein Bash-Escaping nötig mit <<'EOF')
SPORT="${STREAMLIT_PORT}"
cat > "${PHP_TMP}" << PHPEOF
<?php
// Chat-App Setup (löscht sich nach Aufruf selbst)
header('Content-Type: text/plain; charset=utf-8');

\$target   = __DIR__ . '/chat';
\$tar      = __DIR__ . '/chat_deploy.tar.gz';
\$env_src  = __DIR__ . '/chat_deploy.env';
\$port     = ${SPORT};

function sh(\$cmd) {
    \$out = []; \$rc = 0;
    exec(\$cmd . ' 2>&1', \$out, \$rc);
    return ['ok' => \$rc === 0, 'out' => implode("\n", \$out)];
}

echo "Target:  \$target\n";

// Verzeichnisse anlegen
foreach (['\$target', '\$target/chat_logs', '\$target/pdf_exports', '\$target/.streamlit'] as \$d) {
    if (!is_dir(\$d)) mkdir(\$d, 0755, true);
}

// Tarball entpacken
\$r = sh("tar -xzf \$tar -C \$target");
echo "untar: " . (\$r['ok'] ? 'OK' : 'FEHLER: ' . \$r['out']) . "\n";
@unlink(\$tar);

// .env kopieren
if (file_exists(\$env_src)) {
    copy(\$env_src, \$target . '/.env');
    echo ".env: OK\n";
    @unlink(\$env_src);
}

// .htaccess für mod_proxy (HTTP + WebSocket)
\$htaccess = 'Options -Indexes
RewriteEngine On

RewriteCond %{HTTP:Upgrade} websocket [NC]
RewriteCond %{HTTP:Connection} upgrade [NC]
RewriteRule ^(.*)\$ ws://127.0.0.1:' . \$port . '/chat/\$1 [P,L]

RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)\$ http://127.0.0.1:' . \$port . '/chat/\$1 [P,L]
';
file_put_contents(\$target . '/.htaccess', \$htaccess);
echo ".htaccess: OK\n";

// Python venv
\$r = sh("cd \$target && python3 -m venv .venv");
echo "venv: " . (\$r['ok'] ? 'OK' : 'FEHLER: ' . \$r['out']) . "\n";

\$r = sh("\$target/.venv/bin/pip install -q --upgrade pip && \$target/.venv/bin/pip install -q -r \$target/requirements.txt");
echo "pip: " . (\$r['ok'] ? 'OK' : 'FEHLER: ' . \$r['out']) . "\n";

// Alten Streamlit-Prozess stoppen
\$pid_file = "\$target/streamlit.pid";
if (file_exists(\$pid_file)) {
    \$pid = (int) file_get_contents(\$pid_file);
    if (\$pid > 0) sh("kill \$pid 2>/dev/null");
    sleep(1);
    @unlink(\$pid_file);
}

// Streamlit starten
\$streamlit = \$target . '/.venv/bin/streamlit';
\$log       = \$target . '/streamlit.log';
\$cmd = "cd \$target && nohup \$streamlit run app.py"
     . " --server.port \$port"
     . " --server.address 127.0.0.1"
     . " --server.headless true"
     . " --server.baseUrlPath /chat"
     . " > \$log 2>&1 & echo \\\$! > \$pid_file";
sh(\$cmd);
sleep(3);

\$ok = file_exists(\$pid_file);
echo "streamlit (:\$port): " . (\$ok ? 'OK (PID: ' . trim(file_get_contents(\$pid_file)) . ')' : 'FEHLER – streamlit.log prüfen') . "\n";

echo "\n✓ Fertig!\n";
echo "  Schüler: https://app.modellschule.digital/chat/\n";
echo "  Admin:   https://app.modellschule.digital/chat/Admin\n";
echo "  Restart: https://app.modellschule.digital/restart_chat.php\n";
register_shutdown_function(function() { sleep(1); @unlink(__FILE__); });
PHPEOF

# ── 4. Hochladen ──────────────────────────────────────────────────────────────
echo "  → Dateien hochladen …"
scp_up "/tmp/chat_deploy.tar.gz"  "${APP_DIR}/chat_deploy.tar.gz"
scp_up "/tmp/chat_deploy.env"     "${APP_DIR}/chat_deploy.env"
scp_up "${RESTART_TMP}"           "${APP_DIR}/restart_chat.php"
scp_up "${PHP_TMP}"               "${APP_DIR}/setup_chat.php"

rm -f "${RESTART_TMP}" "${PHP_TMP}" /tmp/chat_deploy.tar.gz /tmp/chat_deploy.env

echo ""
echo "✓ Upload fertig! Jetzt Setup aufrufen:"
echo "  → https://app.modellschule.digital/setup_chat.php"
echo ""
echo "  Danach erreichbar:"
echo "  Schüler: https://app.modellschule.digital/chat/"
echo "  Admin:   https://app.modellschule.digital/chat/Admin"
echo ""
