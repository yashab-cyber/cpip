FROM python:3.11-slim

# General-purpose builder for pure Python and lightweight packages
RUN apt-get update && apt-get install -y \
    build-essential git curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pip setuptools wheel build twine \
    auditwheel patchelf

WORKDIR /build

ENTRYPOINT ["python", "-m", "build"]
