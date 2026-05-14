# Contributing to cpip

First off, thank you for considering contributing to `cpip`! It's people like you that make `cpip` such a great tool for Android/Termux developers.

## Development Setup

1. **Fork the repository** on GitHub.
2. **Clone your fork locally**:
   ```bash
   git clone https://github.com/yashab-cyber/cpip.git
   cd cpip
   ```
3. **Install the development dependencies**:
   ```bash
   pip install -e .[dev]
   ```
4. **Run the local cloud stack** (requires Docker):
   ```bash
   make docker-up
   ```

## Workflow

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/my-awesome-feature
   ```
2. Make your changes and write tests.
3. Format your code (we use `black` and `ruff`):
   ```bash
   make format
   make lint
   ```
4. Run the test suite:
   ```bash
   make test
   ```
5. Push to your fork and submit a Pull Request.

## Pull Request Guidelines

- Ensure your PR description clearly describes the problem and solution. Include the relevant issue number if applicable.
- Keep PRs as small and focused as possible.
- Update documentation and `README.md` if your changes affect user-facing behavior.

## Code of Conduct
Please note that this project is released with a [Contributor Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.
