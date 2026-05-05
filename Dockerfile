FROM python:3.11-slim AS builder
WORKDIR /root
ENV ARCH=x86_64
RUN apt-get update && apt-get install -y yasm nasm git curl lbzip2 build-essential
RUN git clone https://github.com/acoustid/ffmpeg-build.git
RUN echo "FFMPEG_CONFIGURE_FLAGS+=(--enable-encoder=pcm_s16le --enable-muxer=wav --enable-filter=loudnorm --enable-filter=aresample --enable-filter=replaygain --enable-filter=volume)" >> ffmpeg-build/common.sh
RUN ffmpeg-build/build-linux.sh
RUN mv ffmpeg-build/artifacts/ffmpeg-*-linux-gnu/bin/ffmpeg .

FROM python:3.11-slim

ENV WINEPREFIX="/wine32"
ENV WINEARCH=win32
ENV LOG_LEVEL=
ENV WINEDEBUG=-all
ENV DEBIAN_FRONTEND=noninteractive

# Enable i386 architecture and install WineHQ's newer Wine (fixes sock_check_pollhup on kernel 6.x)
RUN dpkg --add-architecture i386 \
  && apt-get update \
  && apt-get install -y --no-install-recommends wget gnupg ca-certificates \
  && mkdir -pm755 /etc/apt/keyrings \
  && wget -O /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key \
  && wget -NP /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/debian/dists/bookworm/winehq-bookworm.sources \
  && apt-get update \
  && apt-get install -y --install-recommends winehq-stable \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Initialize the 32-bit Wine prefix (failures here are non-fatal; first runtime call will finalize)
RUN mkdir -p /wine32 && wineboot -i >/dev/null 2>&1 || true

COPY --from=builder /root/ffmpeg /usr/bin/ffmpeg
COPY psp_at3tool.exe /root/psp_at3tool.exe
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN mkdir /uploads
COPY *.py ./

EXPOSE 5000
ENTRYPOINT ["uvicorn"]
CMD ["main:api", "--host", "0.0.0.0", "--port", "5000"]
