#!/bin/bash
set -e

export WINEPREFIX="/wine32"
export WINEARCH="win32"
export DISPLAY=":99"

# Kill any stray wineserver processes
pkill -9 wineserver 2>/dev/null || true

# Start the application
exec uvicorn main:api --host 0.0.0.0 --port 5000 "$@"
