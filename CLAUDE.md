# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

FastAPI microservice that encodes/decodes ATRAC audio for [Web MiniDisc Pro](https://github.com/asivery/webminidisc). Originally wrapped Sony's `psp_at3tool.exe` under Wine; this fork switched to native [atracdenc](https://github.com/dcherednik/atracdenc) because Wine's `sock_check_pollhup` fails on host kernel 6.x.

Trade-off of the switch: only **LP2** and **LP4** are supported. ATRAC3+ (`PLUS*`) and `LP105` are gone — atracdenc doesn't implement them.

## Architecture

- **main.py** — FastAPI app with three endpoints (`/encode`, `/transcode`, `/decode`). Uploads land in `NamedTemporaryFile`, get `.flush()`'d before subprocess calls (the original code had a race where the file was deleted before the encoder read it). Cleanup runs in `BackgroundTasks` after the response.
- **utils.py** — `do_encode` and `do_decode` shell out to `/usr/bin/atracdenc`. Both copy the input to a temp file with the correct extension (`.wav` for input, `.aea` for ATRAC3 output) because atracdenc dispatches on extension. Both use `stdin=DEVNULL` and `timeout=300` so a hung encoder can't block the request.
- **Dockerfile** — three stages: build ffmpeg from source (custom filter set: `loudnorm`, `replaygain`, `volume`, `aresample`), build atracdenc from source, then a slim runtime stage that copies both binaries.

## Build & run

```bash
docker compose down
docker build -t mdencoder:latest .
docker compose up -d
docker compose logs -f atrac-api
```

First build ~10-15 min (ffmpeg compile is the slow part). The container expects to join the external `proxy-network` Docker network (see docker-compose.yml).

## Important context

- **No psp_at3tool.exe.** Don't reintroduce it or Wine. The host kernel can't run wineserver. The git history has the Wine-based implementation if you ever need to look back.
- **atracdenc CLI is extension-sensitive.** Output extension determines codec; `.aea` for ATRAC3. Don't pass bare UUID paths.
- **The transcode pipeline strips video streams** (`-vn -map 0:a`). MP3s with embedded cover art used to confuse the downstream encoder.
- **No automated tests.** Manual smoke test: encode a WAV, decode it back, transcode an MP3.

## Common tasks

### Adding a new ATRAC type
Only meaningful if atracdenc gains support for it. Add to `atracTypes` enum and `encoder_args` dict in utils.py — the dict tuple is `(codec_name, bitrate_kbps_string)` matching atracdenc's `-e` and `--bitrate` flags.

### Modifying the FFmpeg build
Filters and codecs are enabled in the Dockerfile's `ffmpeg-builder` stage via the `FFMPEG_CONFIGURE_FLAGS` line. Anything not listed there is stripped.

### Debugging a failed encode
Logs include the full `atracdenc` command line plus stdout/stderr. Reproduce manually with:
```bash
docker exec -it atrac-api atracdenc -e atrac3 --bitrate 132 -i /tmp/foo.wav -o /tmp/foo.aea
```
