FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false TOKENIZER_PATH=/opt/tokenizer.json
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --no-create-home app
COPY assets/tokenizer.json /opt/tokenizer.json
RUN echo 'aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4  /opt/tokenizer.json' | sha256sum -c -
COPY app app
USER 10001
EXPOSE 8000
CMD ["uvicorn","app.portal:app","--host","0.0.0.0","--port","8000","--no-access-log","--log-level","warning"]
