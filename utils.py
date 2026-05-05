import os, shutil, subprocess
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


def remove_file(filename, logger):
  try:
    os.remove(filename)
    logger.info(f"Removed {filename}")
  except OSError as e:
    logger.warning(f"Failed to remove {filename}: {e}")


def do_encode(input, type, logger):
  # atracdenc requires .wav input; output extension is .aea for ATRAC3
  input_wav = Path(gettempdir(), f"{uuid4()}.wav").absolute()
  output = Path(gettempdir(), f"{uuid4()}.aea").absolute()
  shutil.copy(str(input), str(input_wav))

  codec, bitrate = encoder_args[type if isinstance(type, str) else type.value]
  cmd = ['/usr/bin/atracdenc', '-e', codec]
  if bitrate is not None:
    cmd += ['--bitrate', bitrate]
  cmd += ['-i', str(input_wav), '-o', str(output)]
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
  if not Path(output).exists():
    raise RuntimeError(f"Encoding produced no output file: {output}")

  logger.info(f"Encoding complete: {output}")
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
