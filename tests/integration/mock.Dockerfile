FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /harness
COPY mock_github.py ./
COPY probe_http.py ./
CMD ["python", "-u", "mock_github.py"]
