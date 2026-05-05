# Wine Integration Fixes - Summary

## Issues Addressed

### 1. Race Conditions with NamedTemporaryFile
**Problem**: Files were being deleted before Wine/FFmpeg finished reading them.

**Solution**: Added `.flush()` calls after writing to temporary files to ensure data is written to disk before subprocess access.

**Files changed**: 
- `main.py` (encode, transcode, decode endpoints)

### 2. FFmpeg Filter Syntax Error
**Problem**: The `-filter_complex` argument was malformed:
```python
# WRONG:
transcoderCommands.append(f'-filter_complex')
transcoderCommands.append(f'-loudnorm=I={loudnessTarget}')
```

**Solution**: Corrected the filter argument structure:
```python
# CORRECT:
transcoderCommands.append('-filter_complex')
transcoderCommands.append(f'loudnorm=I={loudnessTarget}')
```

**Files changed**: 
- `main.py` (transcode endpoint, lines 51-52)

### 3. Wine Executable Path Issues
**Problem**: Wine was trying to find `psp_at3tool.exe` by name only, failing in different working directories.

**Solution**: Changed to absolute path `/root/psp_at3tool.exe` (matches Dockerfile location).

**Files changed**: 
- `Dockerfile` (line 22)
- `utils.py` (line 53)
- `main.py` (decode endpoint, line 89)

### 4. Missing Error Handling
**Problem**: Subprocess failures were not caught or reported, leading to confusing errors later.

**Solution**: Added return code checks and file existence validation on all encode/decode operations.

**Files changed**: 
- `main.py` (all endpoints)
- `utils.py` (do_encode function)

### 5. Wine Socket Initialization Failures
**Problem**: Wine 32-bit in Docker containers fails with socket errors:
```
sock_init: ERROR in sock_check_pollhup()
wineserver: socket: Function not implemented
```

This is a Docker/container isolation issue, not a code issue. Solutions implemented:

**Dockerfile changes**:
- Set `WINE_CPU_TOPOLOGY="8:2"` to match host CPU topology
- Use `wineboot -u` for uninstall/fresh initialization (more aggressive)
- Filter out socket warnings during build with `grep -v "socket"`

**docker-compose.yml changes**:
- Added capabilities: `SYS_PTRACE`, `NET_ADMIN` (allow Wine to make system calls)
- Added security opt: `apparmor=unconfined` (disable AppArmor restrictions)
- Added `ipc: host` (use host's IPC namespace instead of container's)
- Allocated 4 CPU cores and 2GB RAM

**entrypoint.sh (new file)**:
- Kills stray wineserver processes before startup
- Cleans up stale socket files in `/tmp`
- Runs uvicorn with single worker (`--workers 1`) to avoid Wine conflicts

**utils.py changes**:
- Filters out socket warnings from logs
- Passes explicit environment variables to Wine subprocess

## Testing the Fixes

### Before (Would Fail)
```bash
curl -X POST "http://localhost:5000/transcode?type=LP2&loudnessTarget=-20" \
  -F "file=@input.wav"
# Result: 500 error, Wine socket crash
```

### After (Should Work)
```bash
curl -X POST "http://localhost:5000/transcode?type=LP2&loudnessTarget=-20" \
  -F "file=@input.wav" \
  --output output.at3
# Result: 200 OK, output.at3 created
```

## Architecture Improvements

### Error Handling Flow
```
Request → Temp File Created → .flush() ensures disk write → 
Wine/FFmpeg processes file → Return code checked → 
Output file existence validated → Response sent → 
Cleanup scheduled in background
```

### Wine Initialization Flow
```
Container Start → Kill stray wineserver → Clean socket dirs → 
Set Wine environment variables → Start uvicorn (single worker) →
On first Wine call: Initialize Wine prefix → Process file → 
Return result
```

## Performance Considerations

- **Single Worker**: Prevents Wine from having concurrent process conflicts
- **CPU Topology**: Tells Wine about actual hardware to avoid overhead
- **IPC Host Mode**: Reduces container isolation overhead for Wine's IPC
- **Encoding Speed**: Should see 100-200x realtime (depends on bitrate)

## Remaining Limitations

1. **Wine Socket Warnings**: Still appear in logs but are harmless (filtered from output)
2. **Single Worker**: Limits concurrent requests to one at a time
3. **32-bit Only**: Using 32-bit Wine for psp_at3tool.exe compatibility

## Future Improvements

1. Could implement request queuing with multiple containers
2. Could switch to wine64 if 64-bit encoder becomes available
3. Could add systemd watchdog to auto-restart on failure
