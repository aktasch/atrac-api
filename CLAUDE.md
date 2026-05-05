# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ATRAC API is a FastAPI-based microservice that provides audio encoding/decoding and transcoding capabilities for ATRAC audio formats. It wraps the Sony PSP SDK's `psp_at3tool.exe` encoder and uses FFmpeg for transcoding operations. The service is designed primarily for integration with [Web MiniDisc Pro](https://github.com/asivery/webminidisc).

## Architecture

The application consists of two main Python modules:

- **main.py**: FastAPI server with three endpoints
  - `/encode` - Encodes WAV to AT3 with specified ATRAC type
  - `/transcode` - Pre-processes audio with FFmpeg (resampling, loudness normalization, replay gain) then encodes to AT3
  - `/decode` - Decodes AT3 back to WAV
  - All endpoints use background tasks for cleanup of temporary files

- **utils.py**: Shared utilities
  - `atracTypes` enum: Supported ATRAC formats (LP2, LP4, LP105, PLUS48-PLUS352)
  - `bitrates` dict: Bitrate mappings for each ATRAC type
  - `do_encode()`: Wrapper for Wine + psp_at3tool.exe encoder process
  - `remove_file()`: Cleanup helper for temporary files

## Key Technologies

- **FastAPI** (0.90.0): Web framework
- **FFmpeg**: Pre-processing (compiled with custom filters: pcm_s16le, wav, loudnorm, aresample, replaygain, volume)
- **Wine**: Runs the Windows-only psp_at3tool.exe encoder
- **Python 3.11**: Runtime

## Building & Running

### Docker (Recommended)

The app is designed to run in Docker. To build:

1. Obtain `psp_at3tool.exe` from the Sony PSP SDK or similar source
2. Place it in the repo root as `psp_at3tool.exe`
3. `docker build -t mdencoder .`
4. Use `docker-compose.yml`: `docker-compose up -d`

The Dockerfile is a multi-stage build:
- **Builder stage**: Compiles FFmpeg from source with custom encoder/filter flags
- **Runtime stage**: Sets up Wine for Windows executable, installs Python dependencies, copies compiled FFmpeg and psp_at3tool.exe

### Local Development

```bash
pip install -r requirements.txt
uvicorn main:api --reload --host 0.0.0.0 --port 5000
```

- The app will auto-reload on file changes (requires `watchfiles`)
- API docs available at `http://localhost:5000/docs`
- The startup event primes the Wine server with `wineserver -p`

## Important Implementation Details

### File Handling

- Input files are uploaded as `UploadFile` and copied to `NamedTemporaryFile` for processing
- Output files are created in the system temp directory with UUID-based names
- All temporary files are cleaned up via background tasks after the response is sent
- File responses use `media_type='audio/wav'` regardless of actual ATRAC format (for browser compatibility)

### Transcoding Pipeline

The `/transcode` endpoint applies FFmpeg filters *before* encoding:
- Output always resampled to 44.1 kHz, stereo
- If `loudnessTarget` is set: applies loudness normalization filter (`-loudnorm=I={target}`)
- If `applyReplaygain` is True: applies replay gain volume filter
- These are mutually exclusive options

### CORS Configuration

CORS middleware is added in the startup event (not at app initialization), with open settings: `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]`. This is intentional for public API usage.

### Wine Integration

- `psp_at3tool.exe` runs under Wine in 32-bit mode (`WINEARCH=win32`, `WINEPREFIX=/wine32`)
- The `wineserver -p` call on startup initializes the Wine prefix
- Subprocess calls use absolute paths: `/usr/bin/wine`, `/usr/bin/ffmpeg`, `/usr/bin/wineserver`

## Testing & Verification

No automated tests currently exist. Manual testing should verify:
- Encoding: WAV → AT3 with each supported bitrate/type
- Decoding: AT3 → WAV roundtrip
- Transcoding: Various input formats, loudness targets (-20 to -5), replay gain option
- File cleanup: Temp files are removed after requests complete
- Error handling: Invalid file types, unsupported ATRAC types, subprocess failures

## Common Workflows

### Adding a New ATRAC Type

1. Add enum value to `atracTypes` in utils.py (e.g., `PLUS384 = 'PLUS384'`)
2. Add bitrate mapping to `bitrates` dict (e.g., `'PLUS384': 384`)
3. The enum change automatically exposes the new type in FastAPI's OpenAPI schema

### Modifying FFmpeg Filters

Edit the Dockerfile builder stage's FFmpeg configure flags in the line:
```dockerfile
RUN echo "FFMPEG_CONFIGURE_FLAGS+=(--enable-encoder=pcm_s16le ...)" >> ffmpeg-build/common.sh
```

Any new filters or encoders must be explicitly enabled here.

### Debugging Subprocess Issues

- Wine output is not captured (subprocess calls use default stdout/stderr)
- FFmpeg output *is* captured and logged: `logger.info(transcoder.stdout.decode(...))`
- Check container logs: `docker-compose logs -f mdencoder`
- Errors from psp_at3tool.exe won't appear in logs; the process may fail silently

## Dependencies

See requirements.txt for all pinned versions. Key packages:
- `fastapi`, `starlette`, `uvicorn`: Web framework
- `pydantic`: Request/response validation
- `python-multipart`: File upload parsing
- `python-dotenv`: Environment variable loading (note: not used in the code currently)

## Notes for Future Work

- No environment configuration is used despite importing `python-dotenv`; consider using `.env` for LOG_LEVEL, port, host
- The `/transcode` endpoint's filter logic could be refactored for clarity (conditionals building command list)
- FFmpeg filter string formatting could be safer (use `-filter_complex` with quoted values)
- Consider adding request validation for file extensions (see unused `allowed_file()` function)
