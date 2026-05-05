import os, shutil, subprocess
from enum import Enum
from tempfile import gettempdir, NamedTemporaryFile
from pathlib import Path
from uuid import uuid4


class atracTypes(str, Enum):
  LP2     = 'LP2'
  LP4     = 'LP4'
  LP105   = 'LP105'
  PLUS48  = 'PLUS48'
  PLUS64  = 'PLUS64'
  PLUS96  = 'PLUS96'
  PLUS128 = 'PLUS128'
  PLUS160 = 'PLUS160'
  PLUS192 = 'PLUS192'
  PLUS256 = 'PLUS256'
  PLUS320 = 'PLUS320'
  PLUS352 = 'PLUS352'

bitrates = {
  'LP2':     132,
  'LP4':     66,
  'LP105':   105,
  'PLUS48':  48,
  'PLUS64':  64,
  'PLUS96':  96,
  'PLUS128': 128,
  'PLUS160': 160,
  'PLUS192': 192,
  'PLUS256': 256,
  'PLUS320': 320,
  'PLUS352': 352
}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ['wav', 'at3']


def remove_file(filename, logger): 
  os.remove(filename)
  logger.info(f"Removed {filename}")


def do_encode(input, type, logger):
  output = Path(gettempdir(), str(uuid4())).absolute()
  env = os.environ.copy()
  env['WINEPREFIX'] = '/wine32'
  env['WINEARCH'] = 'win32'
  env['WINEDEBUG'] = '-all'
  result = subprocess.run(['/usr/bin/wine', '/root/psp_at3tool.exe', '-e', '-br', str(bitrates[type]),
    input,
    output], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env)

  stdout_text = result.stdout.decode('utf-8', errors='ignore') if result.stdout else ''

  if stdout_text:
    logger.info(f"at3tool: {stdout_text}")

  if result.returncode != 0:
    logger.error(f"at3tool failed with code {result.returncode} for type {type}")
    raise RuntimeError(f"Encoding failed with code {result.returncode}")

  if not Path(output).exists():
    logger.error(f"No output file created at {output}")
    raise RuntimeError(f"Encoding produced no output file: {output}")

  logger.info(f"Encoding complete: {output}")
  return output
