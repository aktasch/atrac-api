# ATRAC Encode/Decode Server

A [FastAPI](https://fastapi.tiangolo.com/) service that wraps [atracdenc](https://github.com/dcherednik/atracdenc) for encoding/decoding ATRAC audio. Designed for integration with [Web MiniDisc Pro](https://github.com/asivery/webminidisc).

This fork uses `atracdenc` (native Linux) instead of the original `psp_at3tool.exe` Windows binary under Wine, because Wine's `sock_check_pollhup` fails on Linux kernel 6.x.

## Supported formats

- **LP2** (ATRAC3, 132 kbps)
- **LP4** (ATRAC3, 66 kbps)

ATRAC3+ (`PLUS*`) and `LP105` are not supported by atracdenc.

## Build & run

```bash
docker build -t mdencoder:latest .
docker compose up -d
```

The build pulls and compiles atracdenc and ffmpeg from source, so first build takes ~10-15 min.

## Endpoints

- `POST /encode?type=LP2` — WAV → AEA (ATRAC3)
- `POST /transcode?type=LP2[&loudnessTarget=-20|&applyReplaygain=true]` — any audio → AEA (FFmpeg-preprocessed)
- `POST /decode` — AEA → WAV

API docs available at `/docs`.
