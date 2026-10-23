FROM python:3.12-slim
LABEL org.opencontainers.image.source="https://github.com/willtheorangeguy/dreeve-hadge-connector" \
      org.opencontainers.image.title="Hadge to Dreeve connector" \
      org.opencontainers.image.description="Import Apple Health workout summaries from Hadge into Dreeve" \
      org.opencontainers.image.licenses="MIT"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .
ENTRYPOINT ["dreeve-hadge-connector"]
CMD ["watch"]
