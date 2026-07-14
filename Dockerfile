FROM python:3.12-slim

WORKDIR /app

# Copy the metadata first so the dependency layer caches independently of source edits.
COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

# Bake in a set of sample logs so `docker run test-harness` does something
# useful with no arguments and no bind mount.
COPY tests/data/ ./sample_logs/

ENTRYPOINT ["test-harness"]
CMD ["--input", "sample_logs/"]
