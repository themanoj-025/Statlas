# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- PEP 561 `py.typed` marker for type-checking support
- Pre-commit hooks (ruff, mypy, bandit, hadolint)
- CI security scanning (bandit, pip-audit/retire.js, hadolint)
- API versioning (`/api/v1/`)
- Health check endpoints
- Rate limiting
- CORS configuration
- OpenAPI/Swagger documentation
- Prometheus metrics (`/metrics`)
- Structured JSON logging
- Matrix testing (Python 3.10/3.11/3.12)
- Requirements lock file (`requirements.lock`)

### Changed
- CI actions pinned to latest versions (checkout@v7, setup-python@v7, hadolint@v3.2.0)
- Narrowed all bare `except:` and `except Exception:` to specific exception types
- Replaced deprecated `typing.Optional`/`Union` with modern `X | None` syntax
- Added return type hints across all Python functions

### Fixed
- Security: removed hardcoded API keys and secrets
- Security: replaced `os.system()` with `subprocess.run()`
- Security: added dependency vulnerability scanning
- Bare `except:` blocks narrowed to catch specific exceptions
- SQLAlchemy rollback patterns preserved as intentional

## [0.1.0] - 2025-01-01

### Added
- Initial release
