# Contributing Guidelines

Thank you for your interest in contributing to MediaFactory! This document provides guidelines for contributing to make the process smooth for everyone.

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md) to ensure a welcoming environment for all contributors.

## Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Add tests if applicable
5. Ensure all tests pass: `uv run pytest`
6. Run code quality checks: `uv run black src/ tests/ && uv run flake8 src/ tests/ --select=E9,F63,F7,F82 --ignore=F821`
7. Commit your changes: `git commit -m 'Add some feature'`
8. Push to your fork: `git push origin feature/your-feature-name`
9. Create a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/MediaFactory.git
cd MediaFactory

# Install uv (if not already installed)
pip install uv

# Install development dependencies
uv sync --group dev

# Run tests
uv run pytest

# Run code quality checks
uv run black src/ tests/
uv run flake8 src/ tests/ --select=E9,F63,F7,F82 --ignore=F821
```

## Code Style

We follow these coding standards:

- **Formatting**: Black (line length 88)
- **Linting**: Flake8
- **Type hints**: MyPy (relaxed mode)
- **Docstrings**: Google style

## Testing

- Write tests for new features
- Ensure existing tests pass: `uv run pytest`
- Maintain test coverage above 80%
- Test on multiple Python versions (3.11, 3.12, 3.13)

## Documentation

- Update docstrings for public APIs
- Add examples for new features
- Update README.md if needed
- Keep CHANGELOG.md up to date

## Pull Request Process

1. Ensure your PR addresses a single issue or feature
2. Include a clear description of changes
3. Reference related issues using `#issue-number`
4. Wait for CI to pass
5. Request review from maintainers
6. Address feedback promptly

## Reporting Issues

When reporting bugs, please include:

- MediaFactory version
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Relevant error messages/logs

## Feature Requests

For new features:

1. Check if it's already planned in issues
2. Create a feature request issue
3. Describe the use case clearly
4. Discuss implementation approach

## Questions?

Feel free to ask questions in:
- GitHub Discussions
- Issues (tagged as "question")
- Project maintainers directly

Thank you for contributing to MediaFactory!
