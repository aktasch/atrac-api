import os, shutil, struct, subprocess
from enum import Enum
from tempfile import gettempdir
from pathlib import Path
from uuid import uuid4


class atracTypes(str, Enum):
  LP2 = 'LP2'
  LP4 = 'LP4'


# atracdenc encoder mapping. The --bitrate flag does NOT take real kbps —
# values are quantized and clamped by atracdenc's internal table:
#   no flag -> 132 kbps (LP2 default)
#   --bitrate 64 -> 66 kbps (LP4)
# Every other value gets rounded to one of the standard ATRAC3 bitrates.
# So we omit the flag for LP2 and pass exactly 64 for LP4.
encoder_args = {
  'LP2': ('atrac3', None),
  'LP4': ('atrac3', '64'),
}

# Per-type ATRAC3 frame parameters.
# bytes_per_frame is the per-channel frame size; nBlockAlign in the WAV header
# is bytes_per_frame * 2 (stereo). Web MiniDisc Pro reads nBlockAlign at offset 32
# and divides by 2 to recover bytes_per_frame.
type_params = {
  'LP2': (132, 192),
  'LP4': (66, 96),
}

# atracdenc emits OMA (Sony OpenMG Audio) with a fixed 96-byte header.
# Web MiniDisc Pro expects a RIFF/WAVE wrapper with wFormatTag=0x0270 (ATRAC3)
# instead. So we strip the OMA header and rewrap as RIFF/WAVE before returning.
OMA_HEADER_SIZE = 96


def wrap_atrac3_as_riff(frames: bytes, bitrate_kbps: int, bytes_per_frame: int) -> bytes:
  """Wrap raw ATRAC3 frames in a Sony-style RIFF/WAVE/fmt /data container.

  Layout matches what Web MiniDisc Pro's getATRACWAVEncoding() parses:
    offset 20 wFormatTag      = 0x0270  (WAVE_FORMAT_SONY_SCX / ATRAC3)
    offset 22 nChannels       = 2
    offset 24 nSamplesPerSec  = 44100
    offset 32 nBlockAlign     = bytes_per_frame * 2  (client divides by 2)
  """
  avg_bps = bitrate_kbps * 1000 // 8
  fmt_chunk_body = struct.pack('<HHIIHHH',
    0x0270,                # wFormatTag
    2,                     # nChannels
    44100,                 # nSamplesPerSec
    avg_bps,               # nAvgBytesPerSec
    bytes_per_frame * 2,   # nBlockAlign (stereo, client reads/2)
    0,                     # wBitsPerSample
    14,                    # cbSize  (extension follows)
  )
  # 14-byte Sony codec extension. WMD Pro discards these bytes; we just need the
  # extension to exist so parsers that read cbSize don't trip.
  fmt_chunk_body += struct.pack('<HHHHHHH', 1, 0x1000, 0, 0, 0, 0, 0)
  fmt_chunk = b'fmt ' + struct.pack('<I', len(fmt_chunk_body)) + fmt_chunk_body
  data_chunk = b'data' + struct.pack('<I', len(frames)) + frames
  body = b'WAVE' + fmt_chunk + data_chunk
  return b'RIFF' + struct.pack('<I', len(body)) + body


def remove_file(filename, logger):
  try:
    os.remove(filename)
    logger.info(f"Removed {filename}")
  except OSError as e:
    logger.warning(f"Failed to remove {filename}: {e}")


def do_encode(input, type, logger):
  # atracdenc requires .wav input; intermediate output is .aea (OMA container)
  input_wav = Path(gettempdir(), f"{uuid4()}.wav").absolute()
  oma_path = Path(gettempdir(), f"{uuid4()}.aea").absolute()
  shutil.copy(str(input), str(input_wav))

  type_str = type if isinstance(type, str) else type.value
  codec, bitrate = encoder_args[type_str]
  cmd = ['/usr/bin/atracdenc', '-e', codec]
  if bitrate is not None:
    cmd += ['--bitrate', bitrate]
  cmd += ['-i', str(input_wav), '-o', str(oma_path)]
  logger.info(f"Running: {' '.join(cmd)}")

  try:
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            stdin=subprocess.DEVNULL, timeout=300)
  except subprocess.TimeoutExpired as e:
    try: os.remove(input_wav)
    except OSError: pass
    raise RuntimeError("Encoding timed out") from e

  stdout_text = result.stdout.decode('utf-8', errors='ignore') if result.stdout else ''
  stderr_text = result.stderr.decode('utf-8', errors='ignore') if result.stderr else ''
  if stdout_text:
    logger.info(f"atracdenc stdout: {stdout_text}")
  if stderr_text:
    logger.info(f"atracdenc stderr: {stderr_text}")

  try: os.remove(input_wav)
  except OSError: pass

  if result.returncode != 0:
    raise RuntimeError(f"Encoding failed with code {result.returncode}: {stderr_text or stdout_text}")
  if not oma_path.exists():
    raise RuntimeError(f"Encoding produced no output file: {oma_path}")

  # Convert OMA -> RIFF/WAVE AT3 (the format Web MiniDisc Pro expects)
  with open(oma_path, 'rb') as f:
    f.seek(OMA_HEADER_SIZE)
    frames = f.read()
  try: os.remove(oma_path)
  except OSError: pass

  bitrate_kbps, bytes_per_frame = type_params[type_str]
  if len(frames) % bytes_per_frame != 0:
    raise RuntimeError(
      f"OMA payload size {len(frames)} is not a multiple of frame size {bytes_per_frame} for {type_str}"
    )
  riff = wrap_atrac3_as_riff(frames, bitrate_kbps, bytes_per_frame)

  output = Path(gettempdir(), f"{uuid4()}.at3").absolute()
  with open(output, 'wb') as f:
    f.write(riff)

  logger.info(f"Encoding complete: {output} ({len(frames)//bytes_per_frame} frames, {len(riff)} bytes)")
  return output


def do_decode(input, logger):
  input_aea = Path(gettempdir(), f"{uuid4()}.aea").absolute()
  output = Path(gettempdir(), f"{uuid4()}.wav").absolute()
  shutil.copy(str(input), str(input_aea))

  cmd = ['/usr/bin/atracdenc', '-d', '-i', str(input_aea), '-o', str(output)]
  logger.info(f"Running: {' '.join(cmd)}")

  try:
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            stdin=subprocess.DEVNULL, timeout=300)
  except subprocess.TimeoutExpired as e:
    try: os.remove(input_aea)
    except OSError: pass
    raise RuntimeError("Decoding timed out") from e

  stdout_text = result.stdout.decode('utf-8', errors='ignore') if result.stdout else ''
  stderr_text = result.stderr.decode('utf-8', errors='ignore') if result.stderr else ''
  if stdout_text:
    logger.info(f"atracdenc stdout: {stdout_text}")
  if stderr_text:
    logger.info(f"atracdenc stderr: {stderr_text}")

  try: os.remove(input_aea)
  except OSError: pass

  if result.returncode != 0:
    raise RuntimeError(f"Decoding failed with code {result.returncode}: {stderr_text or stdout_text}")
  if not Path(output).exists():
    raise RuntimeError(f"Decoding produced no output file: {output}")

  logger.info(f"Decoding complete: {output}")
  return output
