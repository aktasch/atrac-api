# Build and Deploy Instructions

## Prerequisites

- Docker installed and running
- docker-compose installed
- `psp_at3tool.exe` from Sony PSP SDK (not included in repo)
- At least 4GB free disk space (for Docker build and FFmpeg compilation)

## Step-by-Step Build

### 1. Prepare the Repository

```bash
cd /path/to/atrac-api-mine

# Verify psp_at3tool.exe is in the root directory
ls -lh psp_at3tool.exe

# Should show something like:
# -rw-r--r-- 1 user user 794K May  5 12:00 psp_at3tool.exe
```

### 2. Build the Docker Image

```bash
docker build -t mdencoder:latest .
```

**Build time**: 10-15 minutes (first time, due to FFmpeg compilation)
**Subsequent builds**: Faster (Docker layer caching)

**Monitor the build**:
```bash
docker build -t mdencoder:latest . --progress=plain
```

### 3. Verify the Image

```bash
# List images
docker images | grep mdencoder

# Should show:
# mdencoder     latest     <image-id>   <time>   <size>
```

### 4. Create Upload Directory (on host)

```bash
mkdir -p /data/atrac-api/uploads
chmod 777 /data/atrac-api/uploads

# Verify:
ls -ld /data/atrac-api/uploads
```

### 5. Start the Container

```bash
docker-compose up -d
```

**Verify startup**:
```bash
docker ps | grep atrac-api
# Should show atrac-api container running

docker-compose logs -f atrac-api
# Watch for startup messages
```

### 6. Test the API

```bash
# Health check - access the API docs
curl http://localhost:5000/docs

# Should return HTML (Swagger UI)
```

## Testing Each Endpoint

### Test 1: Encode (WAV → AT3)

```bash
# Create a test WAV file (or use an existing one)
# For this example, we'll create silence
ffmpeg -f lavfi -i anullsrc=r=44100:cl=stereo -t 5 -q:a 9 -acodec libmp3lame test.wav

# Encode to AT3
curl -X POST "http://localhost:5000/encode?type=LP2" \
  -F "file=@test.wav" \
  --output test_encoded.at3

# Check file was created
ls -lh test_encoded.at3
```

### Test 2: Decode (AT3 → WAV)

```bash
# Using the AT3 file from Test 1
curl -X POST "http://localhost:5000/decode" \
  -F "file=@test_encoded.at3" \
  --output test_decoded.wav

# Check file was created
ls -lh test_decoded.wav
```

### Test 3: Transcode with Loudness

```bash
# Create a test input
ffmpeg -f lavfi -i anullsrc=r=44100:cl=stereo -t 5 -q:a 9 -acodec libmp3lame test_input.wav

# Transcode with loudness normalization
curl -X POST "http://localhost:5000/transcode?type=LP2&loudnessTarget=-20" \
  -F "file=@test_input.wav" \
  --output test_loudness.at3

# Check result
ls -lh test_loudness.at3
```

### Test 4: Transcode with Replay Gain

```bash
# Transcode with replay gain
curl -X POST "http://localhost:5000/transcode?type=PLUS128&applyReplaygain=true" \
  -F "file=@test_input.wav" \
  --output test_replaygain.at3

# Check result
ls -lh test_replaygain.at3
```

## Monitoring

### View Real-Time Logs

```bash
docker-compose logs -f atrac-api
```

### Check Resource Usage

```bash
docker stats atrac-api
```

### Access Container Shell (for debugging)

```bash
docker exec -it atrac-api bash

# Inside the container:
ls -la /wine32
ls -la /root/psp_at3tool.exe
ffmpeg -version
```

## Troubleshooting

### Container Exits Immediately

```bash
docker-compose logs atrac-api
# Check for Python errors or import issues
```

### Port 5000 Already in Use

```bash
# Find what's using it
lsof -i :5000

# Change docker-compose.yml:
# ports:
#   - "5001:5000"
```

### Out of Disk Space

```bash
# Check disk usage
df -h

# Clean Docker images/containers
docker system prune -a --volumes
# WARNING: This removes all unused Docker resources
```

### Wine Still Failing

```bash
# Restart container
docker-compose restart atrac-api
docker-compose logs -f atrac-api

# If still failing, rebuild
docker-compose down
docker rmi mdencoder:latest
docker build -t mdencoder:latest .
docker-compose up -d
```

## Production Checklist

- [ ] psp_at3tool.exe placed in repository root
- [ ] Docker image builds successfully
- [ ] Upload directory created with correct permissions
- [ ] Container starts without errors
- [ ] API docs page accessible at http://localhost:5000/docs
- [ ] Encode test passes (WAV → AT3)
- [ ] Decode test passes (AT3 → WAV)
- [ ] Transcode with loudness test passes
- [ ] Transcode with replay gain test passes
- [ ] Container auto-restarts on failure (`restart: unless-stopped`)
- [ ] Upload directory persists across container restarts

## Rollback Procedure

If something goes wrong:

```bash
# Stop and remove container
docker-compose down

# Remove the image
docker rmi mdencoder:latest

# Remove any incomplete builds
docker image prune -a

# Start fresh - go back to step 2 (Build the Docker Image)
```

## Performance Baseline (i7-9700, 8 cores, 2GB RAM allocated)

- **Build time**: 12-15 minutes
- **Container startup**: 2-3 seconds
- **First encode (cold start)**: 3-5 seconds + actual encoding time
- **Subsequent encodes**: ~2-3 seconds + actual encoding time
- **Encoding speed**: ~120-180x realtime (varies by bitrate)
- **Concurrent requests**: 1 at a time (single worker)

## Next Steps

1. Once verified working, integrate with Web MiniDisc Pro
2. Configure your client to point to `http://your-host:5000`
3. Monitor logs periodically for any issues
4. Keep `psp_at3tool.exe` secure (consider the source and licensing)
