#!/bin/bash
set -e

export WINEPREFIX="/wine32"
export WINEARCH="win32"
export WINEDEBUG=-all

exec uvicorn main:api --host 0.0.0.0 --port 5000 --workers 1 "$@"
