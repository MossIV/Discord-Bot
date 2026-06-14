# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.14.0
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# [CHANGE 1] apt cache mounts + --no-install-recommends (no more rm -rf needed)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends curl unzip ffmpeg

# [CHANGE 2] Architecture-aware Deno install — avoids slow/unreliable shell script under emulation
ARG TARGETARCH
RUN DENO_ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "aarch64" || echo "x86_64") && \
    curl -fsSL "https://github.com/denoland/deno/releases/latest/download/deno-${DENO_ARCH}-unknown-linux-gnu.zip" \
         -o /tmp/deno.zip && \
    unzip /tmp/deno.zip -d /usr/local/bin && \
    chmod +x /usr/local/bin/deno && \
    rm /tmp/deno.zip

# [CHANGE 3] Upgrade pip first (logical order), with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip

# [CHANGE 4] All pip installs now share the same cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install -U "yt-dlp[default]"

USER appuser

COPY . .
COPY ["./joining voicelines", "/joining voicelines"]

EXPOSE 8000

CMD python ./pythonBot.py