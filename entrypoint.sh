#!/bin/bash

export WINEPREFIX="/wine32"
export WINEARCH="win32"
export DISPLAY=":99"

# Kill any stray wineserver processes from previous runs
pkill -9 wineserver 2>/dev/null || true
sleep 1

# Clean up Wine socket directory if it exists and is stale
rm -rf /tmp/.wine* 2>/dev/null || true
rm -rf /tmp/.X* 2>/dev/null || true

# Start the application
exec uvicorn main:api --host 0.0.0.0 --port 5000 --workers 1 "$@"
