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
ENV DISPLAY=:99
ENV WINE_CPU_TOPOLOGY="4:2"
RUN dpkg --add-architecture i386
RUN apt-get update && apt-get install -y wine32 wine:i386 cabextract zenity --no-install-recommends
RUN apt-get clean
RUN rm -rf /wine32 && mkdir -p /wine32 && WINEPREFIX=/wine32 WINEARCH=win32 /usr/bin/wine wineboot -u > /dev/null 2>&1 || true
COPY --from=builder /root/ffmpeg /usr/bin/ffmpeg
COPY psp_at3tool.exe /root/psp_at3tool.exe
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN mkdir /uploads
COPY *.py ./
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5000
ENTRYPOINT ["/entrypoint.sh"]
