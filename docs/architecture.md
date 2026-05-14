# System Architecture

`cpip` represents a paradigm shift in how mobile environments handle heavy dependencies. Instead of trying to force local execution, it bridges the gap between local mobility and cloud horsepower.

## 10-Phase Design

### 1. Shared Infrastructure
Defines the `JSON-RPC 2.0` WebSocket protocol (`shared/protocol.py`), wire models (`shared/models.py`), and custom exception hierarchies.

### 2. Client Runtime
The Termux-resident CLI. Features a cyberpunk-themed rich UI, LRU caching with SQLite, and background sync daemons (`client/daemon.py`) that keep a persistent WebSocket open to the cloud.

### 3. Hybrid Execution Engine
The magic layer. `runtime/hooks.py` intercepts `sys.meta_path` to proxy modules. Method calls are serialized by `runtime/serialization.py` (which handles tensors and numpy arrays gracefully) and routed to the cloud.

### 4. Remote Package Virtualization
Instead of extracting `torch` and using 4GB of phone storage, `virtualization/layers.py` fetches content-addressed `tar.gz` chunks and dynamically links `.so` files using `patchelf`.

### 5. Cloud Backend
A FastAPI monolith (`server/app.py`). Handles JWT authentication, Redis-backed rate limiting, WebSocket connection hubs, and the underlying SQLite/PostgreSQL database.

### 6. Cloud Build Farm
When a user requests a package that isn't built for Android `aarch64`, the `builder/worker.py` dispatches a Docker container utilizing the Android NDK and Rust (`Dockerfile.arm64`) to cross-compile the Python extension on the fly.

### 7. Cloud Execution Engine
Code routed from the client is sandboxed via Docker (`executor/sandbox.py`). Tasks demanding hardware acceleration are routed to `gpu_runtime.py`, while web scraping tasks spin up `browser_runtime.py` (Playwright).

### 8. AI Agent Support
Native tool bindings allow orchestrators to utilize `cpip` dynamically. The `ModelRouter` can evaluate device RAM and model size, deciding whether to load an LLM locally (e.g., via `llama.cpp`) or proxy to the cloud.

### 9. Security Layer
Wheels built by the build farm are cryptographically signed using Ed25519 (`security/signing.py`). All sandboxes use tight seccomp profiles to prevent container escapes.

### 10. Deployment
Fully containerized setup utilizing Docker Compose and Nginx for seamless local development or production scaling.
