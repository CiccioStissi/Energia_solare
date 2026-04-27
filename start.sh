#!/usr/bin/env bash
# Avvia RabbitMQ (se non attivo), FastAPI e csv_worker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/server"

# --- Colori ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[START]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; }

# --- 1. RabbitMQ ---
if nc -z localhost 5672 2>/dev/null; then
    log "RabbitMQ già attivo su porta 5672 — skip avvio"
else
    warn "RabbitMQ non risponde su 5672 — tentativo avvio..."
    if command -v rabbitmq-server &>/dev/null; then
        sudo rabbitmq-server -detached 2>/dev/null || true
        echo -n "Attendo RabbitMQ"
        for i in $(seq 1 15); do
            sleep 1
            echo -n "."
            nc -z localhost 5672 2>/dev/null && break
        done
        echo ""
        nc -z localhost 5672 2>/dev/null || { err "RabbitMQ non risponde dopo 15s. Uscita."; exit 1; }
        log "RabbitMQ avviato"
    else
        err "rabbitmq-server non trovato. Installa RabbitMQ o avvialo manualmente."
        exit 1
    fi
fi

# --- Pulizia processi figli alla chiusura ---
cleanup() {
    echo ""
    log "Arresto in corso..."
    kill "$FASTAPI_PID" "$WORKER_PID" 2>/dev/null || true
    wait "$FASTAPI_PID" "$WORKER_PID" 2>/dev/null || true
    log "Tutto fermo."
}
trap cleanup INT TERM

# --- Attiva venv ---
VENV="$SCRIPT_DIR/venv/bin/activate"
if [ -f "$VENV" ]; then
    source "$VENV"
    log "venv attivato"
else
    warn "Nessun venv trovato in $SCRIPT_DIR/venv — uso Python di sistema"
fi

# --- 2. FastAPI ---
log "Avvio FastAPI..."
cd "$SERVER_DIR"
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!
log "FastAPI PID=$FASTAPI_PID  →  http://localhost:8000/docs"

# Breve pausa per lasciare che FastAPI si connetta a RabbitMQ prima del worker
sleep 2

# --- 3. csv_worker ---
log "Avvio csv_worker..."
python -m workers.csv_worker &
WORKER_PID=$!
log "csv_worker PID=$WORKER_PID"

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN} Tutti i servizi attivi. Ctrl+C stop.${NC}"
echo -e "${GREEN}======================================${NC}"

# Attende entrambi i processi
wait "$FASTAPI_PID" "$WORKER_PID"
