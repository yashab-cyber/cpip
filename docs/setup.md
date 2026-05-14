# Setup Guide

## Local Client Setup (Android / Termux)

1. Ensure you have Python 3.10+ installed in Termux:
   ```bash
   pkg update
   pkg install python git
   ```

2. Clone and install the `cpip` client:
   ```bash
   git clone https://github.com/yashab-cyber/cpip.git
   cd cpip
   pip install -e .[client]
   ```

3. Initialize the configuration and login (Dev mode bypass):
   ```bash
   cpip config --init
   cpip login
   ```

4. Verify your installation:
   ```bash
   cpip doctor
   ```
   This will run system diagnostics, check SQLite capabilities, and verify network connectivity to the cloud backend.

## Cloud Backend Setup (Server)

If you are hosting the backend yourself, you need a Linux server with Docker and Docker Compose installed. For GPU acceleration, the NVIDIA Container Toolkit is required.

1. Clone the repository on your server:
   ```bash
   git clone https://github.com/yashab-cyber/cpip.git
   cd cpip
   ```

2. Configure environment variables. You can edit the `docker-compose.yml` or create a `.env` file:
   ```env
   JWT_SECRET=your_super_secret_key_here
   CPIP_DEBUG=false
   ```

3. Spin up the stack:
   ```bash
   make docker-up
   ```

4. The server will be exposed on port `8000` by default. Point your Termux client to this URL:
   ```bash
   cpip config --api-url http://your-server-ip:8000
   ```
