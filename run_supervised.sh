#!/bin/bash
# ==============================================================
# 🧠 Vector Service launcher (safe supervisor wrapper)
# Forces execution under non-root user (vitos)
# ==============================================================

set -e

APP_DIR="/home/vitos/Projects/python/embeddings-generator"
USER="vitos"
LOG_DIR="$APP_DIR/logs"
VENV_PATH="$APP_DIR/.venv/bin/activate"
MAKE_CMD="/usr/bin/make run"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# --- Ensure permissions ---
mkdir -p "$LOG_DIR"
chown -R "$USER:$USER" "$LOG_DIR"

# --- Log startup info ---
echo "[$DATE] Starting Vector service under user: $USER" >> "$LOG_DIR/vector_supervisor.log"

# --- Run app as vitos user with full environment ---
exec sudo -u "$USER" -E bash -c "
    source '$VENV_PATH' && \
    cd '$APP_DIR' && \
    export HOME='/home/$USER' && \
    export HF_HOME='/home/$USER/.cache/huggingface' && \
    export PYTHONUNBUFFERED=1 && \
    export PATH='$APP_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin' && \
    $MAKE_CMD >> '$LOG_DIR/vector.log' 2>> '$LOG_DIR/vector.err'
"
