import subprocess, logging, shutil
from uuid import uuid4
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from tempfile import gettempdir, NamedTemporaryFile
from utils import atracTypes, do_encode, do_decode, remove_file
from typing import Union

api = FastAPI(title="ATRAC API")
logger = logging.getLogger("uvicorn.info")

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
  filename = file.filename
  logger.info(f"Beginning encode for {filename}")
  with NamedTemporaryFile(suffix='.wav') as input:
    shutil.copyfileobj(file.file, input)
    input.flush()
    output = do_encode(input.name, type, logger)
  background_tasks.add_task(remove_file, output, logger)
  return FileResponse(path=output, filename=Path(filename).stem + '.aea', media_type='audio/aea')


@api.post('/transcode')
def transcode_atrac(
  type: atracTypes,
  background_tasks: BackgroundTasks,
  applyReplaygain: bool = False,
  loudnessTarget: Union[float, None] = Query(default=None, ge=-70, le=-5),
  file: UploadFile = File(),
):
  filename = file.filename
  logger.info(f"Beginning transcode for {filename}")

  transcoderCommands = []
  if loudnessTarget is not None:
    transcoderCommands += ['-af', f'loudnorm=I={loudnessTarget}']
  elif applyReplaygain:
    transcoderCommands += ['-af', 'volume=replaygain=track']
  transcoderCommands += ['-vn', '-map', '0:a', '-ac', '2', '-ar', '44100', '-f', 'wav']

  intermediary = Path(gettempdir(), f"{uuid4()}.wav").absolute()
  with NamedTemporaryFile() as input:
    shutil.copyfileobj(file.file, input)
    input.flush()
    logger.info("Starting ffmpeg...")
    transcoder = subprocess.run(
      ['/usr/bin/ffmpeg', '-i', input.name, *transcoderCommands, str(intermediary)],
      stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    logger.info(transcoder.stdout.decode('utf-8', errors='ignore'))
    if transcoder.returncode != 0:
      raise HTTPException(status_code=500, detail="FFmpeg transcoding failed")
    if not intermediary.exists():
      raise HTTPException(status_code=500, detail="FFmpeg produced no output file")

  logger.info("Starting atracdenc...")
  try:
    output = do_encode(intermediary, type, logger)
  except RuntimeError as e:
    raise HTTPException(status_code=500, detail=str(e))
  finally:
    background_tasks.add_task(remove_file, intermediary, logger)
  background_tasks.add_task(remove_file, output, logger)
  return FileResponse(path=output, filename=Path(filename).stem + '.aea', media_type='audio/aea')


@api.post('/decode')
def decode_atrac(background_tasks: BackgroundTasks, file: UploadFile = File()):
  # atracdenc only decodes ATRAC1 (.aea from MiniDisc SP mode).
  # ATRAC3 (LP2/LP4 OMA output from this server) cannot be round-tripped here.
  filename = file.filename
  logger.info(f"Beginning decode for {filename}")
  with NamedTemporaryFile(suffix='.aea') as input:
    shutil.copyfileobj(file.file, input)
    input.flush()
    try:
      output = do_decode(input.name, logger)
    except RuntimeError as e:
      msg = str(e)
      logger.error(f"Decode failed: {msg}")
      raise HTTPException(
        status_code=415,
        detail=f"Decode failed. atracdenc only decodes ATRAC1 (SP). ATRAC3 (LP2/LP4) is not supported. ({msg})",
      )
  background_tasks.add_task(remove_file, output, logger)
  return FileResponse(path=output, filename=Path(filename).stem + '.wav', media_type='audio/wav')
