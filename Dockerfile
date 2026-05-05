FROM python:3.11-slim AS ffmpeg-builder
WORKDIR /root
ENV ARCH=x86_64
RUN apt-get update && apt-get install -y yasm nasm git curl lbzip2 build-essential
RUN git clone https://github.com/acoustid/ffmpeg-build.git
RUN echo "FFMPEG_CONFIGURE_FLAGS+=(--enable-encoder=pcm_s16le --enable-muxer=wav --enable-filter=loudnorm --enable-filter=aresample --enable-filter=replaygain --enable-filter=volume)" >> ffmpeg-build/common.sh
RUN ffmpeg-build/build-linux.sh
RUN mv ffmpeg-build/artifacts/ffmpeg-*-linux-gnu/bin/ffmpeg .

FROM debian:bookworm-slim AS atracdenc-builder
RUN apt-get update && apt-get install -y --no-install-recommends \
      git cmake g++ make ca-certificates libsndfile1-dev \
  && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN git clone --depth 1 --recurse-submodules --shallow-submodules https://github.com/dcherednik/atracdenc.git
WORKDIR /src/atracdenc/src
RUN cmake . && make -j"$(nproc)"

FROM python:3.11-slim

ENV LOG_LEVEL=
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
  && apt-get install -y --no-install-recommends libsndfile1 \
  && rm -rf /var/lib/apt/lists/*

COPY --from=ffmpeg-builder /root/ffmpeg /usr/bin/ffmpeg
COPY --from=atracdenc-builder /src/atracdenc/src/atracdenc /usr/bin/atracdenc

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir /uploads
COPY *.py ./

EXPOSE 5000
ENTRYPOINT ["uvicorn"]
CMD ["main:api", "--host", "0.0.0.0", "--port", "5000"]
