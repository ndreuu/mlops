FROM python:3.12-slim
ARG OLLAMA_VERSION=0.40.17
ARG OLLAMA_ARCHIVE_SHA256=1df9d6228bac5a22e420b242708c0d10e5b886db97bab99d446a41760f4e79af
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl zstd libgomp1 libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fL --retry 3 "https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/ollama-linux-amd64.tar.zst" -o /tmp/ollama.tar.zst \
    && echo "${OLLAMA_ARCHIVE_SHA256}  /tmp/ollama.tar.zst" | sha256sum -c - \
    && mkdir -p /opt/ollama \
    && tar --zstd --no-recursion --wildcards --no-wildcards-match-slash -xf /tmp/ollama.tar.zst -C /opt/ollama 'bin/ollama' 'lib/ollama/*' \
    && cp /opt/ollama/bin/ollama /usr/bin/ollama \
    && cp -a /opt/ollama/lib/ollama /usr/lib/ollama \
    && rm -rf /opt/ollama /tmp/ollama.tar.zst
COPY model/weights /models
RUN useradd --uid 10001 --no-create-home app
COPY model/runner.py /opt/runner.py
ENV OLLAMA_HOST=0.0.0.0:11434 OLLAMA_MODELS=/models OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 \
    OLLAMA_CONTEXT_LENGTH=2048 OLLAMA_KEEP_ALIVE=-1 OLLAMA_VULKAN=0 CUDA_VISIBLE_DEVICES=-1 \
    NVIDIA_VISIBLE_DEVICES=void HOME=/tmp PYTHONUNBUFFERED=1 OLLAMA_NO_CLOUD=1 OLLAMA_NOPRUNE=1
USER 10001
EXPOSE 11434 11435
CMD ["python", "/opt/runner.py"]
