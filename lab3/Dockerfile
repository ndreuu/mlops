FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false TOKENIZER_PATH=/opt/tokenizer.json
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --no-create-home app
COPY assets/tokenizer.json /opt/tokenizer.json
RUN echo 'c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539  /opt/tokenizer.json' | sha256sum -c -
COPY app app
USER 10001
EXPOSE 8000
CMD ["uvicorn","app.portal:app","--host","0.0.0.0","--port","8000","--no-access-log","--log-level","warning"]
