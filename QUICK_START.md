# Quick Start Guide - ATRAC API

## 30-Second Setup

```bash
# 1. Place encoder
cp psp_at3tool.exe /path/to/atrac-api-mine/

# 2. Create uploads directory
mkdir -p /data/atrac-api/uploads

# 3. Build image
docker build -t mdencoder:latest .

# 4. Start container
docker-compose up -d

# 5. Test API
curl http://localhost:5000/docs
```

## API Endpoints

### Encode (WAV → AT3)
```bash
curl -X POST "http://localhost:5000/encode?type=LP2" \
  -F "file=@input.wav" \
  -o output.at3
```

### Decode (AT3 → WAV)
```bash
curl -X POST "http://localhost:5000/decode" \
  -F "file=@input.at3" \
  -o output.wav
```

### Transcode with Loudness
```bash
curl -X POST "http://localhost:5000/transcode?type=LP2&loudnessTarget=-20" \
  -F "file=@input.wav" \
  -o output.at3
```

### Transcode with Replay Gain
```bash
curl -X POST "http://localhost:5000/transcode?type=PLUS128&applyReplaygain=true" \
  -F "file=@input.wav" \
  -o output.at3
```

## Container Management

```bash
# View logs
docker-compose logs -f atrac-api

# Check status
docker ps | grep atrac-api

# Restart
docker-compose restart atrac-api

# Stop
docker-compose down

# Rebuild
docker-compose down && docker rmi mdencoder:latest && docker build -t mdencoder:latest .
```

## ATRAC Types

| Type | Bitrate | Notes |
|------|---------|-------|
| LP2 | 132 kbps | MiniDisc LP2 (default) |
| LP4 | 66 kbps | MiniDisc LP4 |
| LP105 | 105 kbps | MiniDisc LP105 |
| PLUS64-PLUS352 | 64-352 kbps | ATRAC3+ (various bitrates) |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Port 5000 in use | Change in docker-compose.yml: `"5001:5000"` |
| Container won't start | `docker-compose logs atrac-api` |
| Encoding fails | Ensure input is valid WAV or audio format |
| API not responding | `docker-compose restart atrac-api` |

## System Requirements

- Docker & docker-compose installed
- 2GB RAM minimum
- 4GB free disk space
- `psp_at3tool.exe` from PSP SDK

## Full Documentation

- **DEPLOYMENT.md** - Detailed deployment guide
- **BUILD_INSTRUCTIONS.md** - Step-by-step build & test
- **WINE_FIXES.md** - Technical details of fixes
- **FIXES_SUMMARY.md** - Complete change summary

## Next Steps

1. Run the setup above
2. Check DEPLOYMENT.md for integration with Web MiniDisc Pro
3. Monitor logs: `docker-compose logs -f atrac-api`
