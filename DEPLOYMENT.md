# ATRAC API Deployment Guide

## System Requirements Met

Your host system is fully compatible:
- **CPU**: Intel i7-9700 (8 cores) — sufficient for Wine 32-bit
- **Architecture**: x86_64 with 32-bit support enabled
- **Memory**: Allocate 2GB per container (configurable in docker-compose.yml)

## Pre-Deployment Checklist

1. **Place the encoder executable**:
   ```bash
   cp psp_at3tool.exe /path/to/atrac-api-mine/psp_at3tool.exe
   ```

2. **Create upload directory** (or use the one in docker-compose.yml):
   ```bash
   mkdir -p /data/atrac-api/uploads
   chmod 777 /data/atrac-api/uploads
   ```

## Building the Docker Image

```bash
cd /path/to/atrac-api-mine
docker build -t mdencoder:latest .
```

**Expected build time**: ~10-15 minutes (FFmpeg compilation takes time)

## Running with Docker Compose

```bash
docker-compose up -d
```

## Verification

```bash
# Check if container is running
docker ps | grep atrac-api

# View logs
docker-compose logs -f atrac-api

# Test the API
curl http://localhost:5000/docs
```

## Expected Log Output

You may see Wine socket warnings like:
```
sock_init: ERROR in sock_check_pollhup()
wineserver: socket: Function not implemented
```

**These are NOT errors** — they are harmless warnings from Wine initialization. The application will still work correctly. The entrypoint script filters these out during normal operation.

## Testing the API

### Encode Endpoint
```bash
curl -X POST "http://localhost:5000/encode?type=LP2" \
  -F "file=@input.wav" \
  --output output.at3
```

### Transcode with Loudness Normalization
```bash
curl -X POST "http://localhost:5000/transcode?type=LP2&loudnessTarget=-20" \
  -F "file=@input.mp3" \
  --output output.at3
```

### Transcode with Replay Gain
```bash
curl -X POST "http://localhost:5000/transcode?type=LP2&applyReplaygain=true" \
  -F "file=@input.wav" \
  --output output.at3
```

### Decode Endpoint
```bash
curl -X POST "http://localhost:5000/decode" \
  -F "file=@input.at3" \
  --output output.wav
```

## Supported ATRAC Types

| Type | Bitrate | Use Case |
|------|---------|----------|
| LP2 | 132 kbps | MiniDisc LP2 mode (default quality) |
| LP4 | 66 kbps | MiniDisc LP4 mode (lower quality) |
| LP105 | 105 kbps | MiniDisc LP105 mode |
| PLUS48 | 48 kbps | ATRAC3+ (lowest) |
| PLUS64 | 64 kbps | ATRAC3+ |
| PLUS96 | 96 kbps | ATRAC3+ |
| PLUS128 | 128 kbps | ATRAC3+ |
| PLUS160 | 160 kbps | ATRAC3+ |
| PLUS192 | 192 kbps | ATRAC3+ |
| PLUS256 | 256 kbps | ATRAC3+ |
| PLUS320 | 320 kbps | ATRAC3+ |
| PLUS352 | 352 kbps | ATRAC3+ (highest) |

## Troubleshooting

### Container Won't Start

```bash
# Check logs for specific errors
docker-compose logs atrac-api

# Restart and check
docker-compose restart atrac-api
docker-compose logs -f atrac-api
```

### Encoding Fails with "Function not implemented"

This is a Wine socket issue in Docker, but the application is designed to handle it. If encoding still fails:

1. Stop and restart the container:
   ```bash
   docker-compose restart atrac-api
   ```

2. Check available disk space in `/tmp`:
   ```bash
   df -h /tmp
   ```

3. Increase Docker memory limit in docker-compose.yml:
   ```yaml
   mem_limit: 4g  # Increase from 2g
   ```

### FFmpeg Transcoding Fails

1. Verify input file format is supported
2. Check FFmpeg built with required filters:
   ```bash
   docker exec atrac-api ffmpeg -filters | grep -E "loudnorm|replaygain"
   ```

### Port Already in Use

If port 5000 is already in use, modify docker-compose.yml:
```yaml
ports:
  - "5001:5000"  # Map to 5001 instead
```

## Performance Notes

- **CPU Allocation**: Set to 4 cores (out of 8 available)
- **Memory**: 2GB is sufficient for most use cases
- **Concurrent Requests**: Single worker (--workers 1) to avoid Wine conflicts
- **Encoding Speed**: ~100-200x realtime (5-10 minutes of audio per second on i7-9700)

## Stopping and Cleanup

```bash
# Stop the container
docker-compose down

# Remove the image
docker rmi mdencoder:latest

# Clean up uploads (be careful!)
rm -rf /data/atrac-api/uploads/*
```

## Integration with Web MiniDisc Pro

The API is compatible with Web MiniDisc Pro. Configure it to point to:
```
http://your-host:5000
```

All endpoints are CORS-enabled for cross-origin requests from the web client.
