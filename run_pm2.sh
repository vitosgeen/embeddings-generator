#!/bin/bash
# Start the PM2 process manager 
# ==============================================================
# 🧠 Vector Service launcher 
# Forces execution under non-root user 
# ==============================================================

read -p "⚠️  Are you sure you want to start the Vector service with PM2? (y/n) " -n 1 -r
echo    # move to a new line
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Aborting."
    exit 1
fi

read -p "⚠️  Do you want to start the service from the current directory ($PWD)? (y/n) " -n 1 -r
echo    # move to a new line
if [[ $REPLY =~ ^[Yy]$ ]]; then
    SERVICE_DIR="$PWD"
else
    echo "❌ Aborting."
    exit 1
fi

echo "🎯 Starting Vector service with PM2 from directory: $SERVICE_DIR"
pm2 start "make run" --name vector-service --interpreter venv/bin/python3 --watch --log-date-format "YYYY-MM-DD HH:mm:ss" --output "$SERVICE_DIR/logs/vector_pm2_out.log" --error "$SERVICE_DIR/logs/vector_pm2_err.log" --merge-logs
# ask about pm2 save
read -p "⚠️  Do you want to save the PM2 process list to start on boot? (y/n) " -n 1 -r
echo    # move to a new line
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pm2 save
    echo "✅ PM2 process list saved."
else
    echo "❌ PM2 process list not saved."
fi