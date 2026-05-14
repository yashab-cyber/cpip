<div align="center">

# ☁️ cpip

**Cloud-Powered Package Intelligence for Android Termux**

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-Beta-yellow.svg)]()

<p align="center">
  <i>Bring desktop-class Python performance and ML capabilities to Android.<br>Zero-config cloud offloading, hybrid execution, and instant package virtualization.</i>
</p>

</div>

---

## ⚡ Overview

`cpip` is a production-grade, cloud-assisted package virtualization system built specifically to solve the hardest problems of Python development on Android/Termux: failing native compilations, extreme memory limits, and lack of GPU acceleration.

Instead of failing to install heavy dependencies like PyTorch, TensorFlow, or Playwright on your phone, `cpip`:
1. **Virtualizes** the package locally without exhausting your storage.
2. **Intercepts** imports transparently via `sys.meta_path` hooks.
3. **Offloads** heavy computations to cloud GPU instances using a seamless JSON-RPC 2.0 WebSocket bridge.

It feels exactly like `pip`, but powered by the cloud.

---

## ✨ Features

- 🚀 **Transparent Cloud Execution**: Write code normally (`import torch; torch.tensor([1])`). `cpip` handles the RPC serialization, cloud GPU execution, and result streaming in the background.
- 📦 **Package Virtualization**: Uses container-inspired layering to stream and cache dependencies dynamically instead of extracting thousands of files locally.
- 🏗️ **Automated Cross-Compilation**: Built-in cloud build farm that seamlessly cross-compiles complex C/C++/Rust extensions for `aarch64`.
- 🤖 **Agent-Ready Architecture**: Built-in orchestration tools allow local/cloud LLMs to autonomously execute PC-level tasks and browser automation via Termux.
- 🛡️ **Zero-Trust Security**: End-to-end Ed25519 signature verification, isolated Docker sandboxing, and strict capability dropping.

---

## 🚀 Installation

### 1. Client Setup (Termux)
Run these commands inside your Termux environment:

```bash
# Clone the repository
git clone https://github.com/yashab-cyber/cpip.git
cd cpip

# Install the client-side tooling
pip install -e .[client]
```

### 2. Cloud Server Setup (Optional for self-hosting)
If you want to run your own cloud backend for extreme privacy or custom GPU hardware:

```bash
# On your server (requires Docker & Docker Compose)
git clone https://github.com/yashab-cyber/cpip.git
cd cpip
make docker-up
```

---

## 💻 Usage

`cpip` is designed to be a drop-in replacement for `pip`, with magical new capabilities.

### Authentication
Connect your Termux client to the cloud backend (dev mode bypasses auth locally):
```bash
cpip login
```

### Standard Installation
Works exactly like pip, but handles complex dependencies better by fetching pre-built Android wheels:
```bash
cpip install requests pandas
```

### Cloud-Accelerated Installation
Force a package to use cloud offloading. This is perfect for heavy ML frameworks:
```bash
cpip install --cloud torch
```

### Interactive Hybrid Shell
Launch the `cpip` REPL where your local device seamlessly communicates with the cloud backend:
```bash
cpip shell
```

```python
# Inside the cpip shell
>>> import torch # Loads as a remote proxy module instantly
>>> x = torch.randn(1000, 1000).cuda() # Executes on cloud GPU
>>> print(x.mean()) # Streams result back to Termux
```

### System Diagnostics
Check the health of your Termux environment, cache sizes, and cloud connection:
```bash
cpip doctor
cpip runtime
```

---

## 📚 Documentation

For deep dives into the architecture, setup guides, and advanced usage, check out the `docs/` folder:

- [System Architecture](docs/architecture.md)
- [Complete Setup Guide](docs/setup.md)
- [Advanced Usage & Agents](docs/usage.md)

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md).

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
