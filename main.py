import subprocess, logging, shutil
from uuid import uuid4
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from tempfile import gettempdir, NamedTemporaryFile
from utils import *
from typing import Union

api = FastAPI(
  title="ATRAC API"
)
logger = logging.getLogger("uvicorn.info")
@api.on_event("startup")
async def startup_event():
  api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
  )


@api.get("/")
async def root():
    return RedirectResponse("/docs")

@api.post('/encode')
def encode_atrac(type: atracTypes, background_tasks: BackgroundTasks, file: UploadFile = File()):
  global logger
  filename = file.filename
  logger.info(f"Beginning encode for {filename}")
  with NamedTemporaryFile() as input:
    shutil.copyfileobj(file.file, input)
    input.flush()
    output = do_encode(input.name, type, logger)
  background_tasks.add_task(remove_file, output, logger)
  return FileResponse(path=output, filename=Path(filename).stem + '.at3', media_type='audio/wav')

@api.post('/transcode')
def transcode_atrac(type: atracTypes, background_tasks: BackgroundTasks, applyReplaygain: bool = False, loudnessTarget: Union[float, None] = Query(default=None, ge=-70, le=-5), file: UploadFile = File()):
  global logger
  filename = file.filename
  logger.info(f"Beginning encode for {filename}")

  transcoderCommands = []
  if loudnessTarget is not None:
    transcoderCommands.append('-filter_complex')
    transcoderCommands.append(f'loudnorm=I={loudnessTarget}')
  elif applyReplaygain:
    transcoderCommands.append('-af')
    transcoderCommands.append('volume=replaygain=track')
  transcoderCommands += ['-ac', '2', '-ar', '44100', '-f', 'wav']

  intermediary = Path(gettempdir(), str(uuid4())).absolute()
  with NamedTemporaryFile() as input:
    shutil.copyfileobj(file.file, input)
    input.flush()
    logger.info("Starting ffmpeg...")
    transcoder = subprocess.run([
      '/usr/bin/ffmpeg', '-i',
      Path(input.name),
      *transcoderCommands,
      intermediary], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    logger.info(transcoder.stdout.decode('utf-8', errors='ignore'))
    if transcoder.returncode != 0:
      raise HTTPException(status_code=500, detail="FFmpeg transcoding failed")
    if not Path(intermediary).exists():
      raise HTTPException(status_code=500, detail="FFmpeg produced no output file")

  logger.info("Starting at3tool...")
  output = do_encode(intermediary, type, logger)
  background_tasks.add_task(remove_file, output, logger)
  background_tasks.add_task(remove_file, intermediary, logger)
  return FileResponse(path=output, filename=Path(filename).stem + '.at3', media_type='audio/wav')

@api.post('/decode')
def decode_atrac(background_tasks: BackgroundTasks, file: UploadFile = File()):
  global logger
  filename = file.filename
  logger.info(f"Beginning decode for {filename}")
  output = Path(gettempdir(), str(uuid4())).absolute()
  with NamedTemporaryFile() as input:
    shutil.copyfileobj(file.file, input)
    input.flush()
    result = subprocess.run(['/usr/bin/wine', '/root/psp_at3tool.exe', '-d',
      Path(input.name),
      output])
    if result.returncode != 0:
      raise HTTPException(status_code=500, detail="Decoding failed")
    if not Path(output).exists():
      raise HTTPException(status_code=500, detail="Decoding produced no output file")
  background_tasks.add_task(remove_file, output, logger)
  return FileResponse(path=output, filename=Path(filename).stem + '.wav', media_type='audio/wav')
