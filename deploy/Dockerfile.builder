FROM python:3.11-slim

WORKDIR /app

# Install Docker CLI for spawning sandboxes
RUN apt-get update && apt-get install -y \
    apt-transport-https ca-certificates curl gnupg lsb-release \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .[builder]

COPY builder/ ./builder/
COPY shared/ ./shared/
COPY security/ ./security/

CMD ["python", "-c", "import asyncio; from builder.worker import run_worker; asyncio.run(run_worker())"]
