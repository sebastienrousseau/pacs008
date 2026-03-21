# Contributing to Pacs008

Thank you for your interest in contributing to Pacs008. This guide covers
the development workflow and standards.

## Development Setup

### Prerequisites

- Python 3.9.2+
- [Poetry](https://python-poetry.org/docs/#installation)
- Git with SSH commit signing configured

### Setup

```bash
# Clone and install
git clone git@github.com:sebastienrousseau/pacs008.git
cd pacs008
poetry install

# Verify
poetry run pytest tests/ -q
```

### On macOS

```bash
brew install python@3.12 poetry
```

### On Linux (Debian/Ubuntu)

```bash
sudo apt install python3 python3-pip
pip install poetry
```

### On WSL

```bash
sudo apt install python3 python3-pip
pip install poetry
# Ensure ~/.local/bin is in PATH
```

## Workflow

1. **Fork** the repository
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feat/my-feature
   ```
3. **Make changes** — follow the coding standards below
4. **Run tests** — ensure 99%+ coverage:
   ```bash
   poetry run pytest tests/ -v
   ```
5. **Run linters**:
   ```bash
   poetry run ruff check pacs008/
   poetry run mypy pacs008/
   poetry run black --check pacs008/ tests/
   ```
6. **Sign and commit**:
   ```bash
   git commit -S -m "feat: add my feature"
   ```
7. **Push** and open a pull request

## Commit Signing (Required)

All commits **must** be signed with SSH or GPG.

### SSH Signing

```bash
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519
git config --global commit.gpgsign true
```

### Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add UETR generation for v08+
fix: handle empty IBAN in debtor account
docs: update README with API examples
test: add gold master for v13
refactor: simplify XML data preparer dispatch
```

## Coding Standards

- **Line length:** 79 characters (enforced by Black + Ruff)
- **Type hints:** Required on all public functions (mypy strict)
- **Docstrings:** Required on all public classes and functions
- **Tests:** Every new feature must include tests; maintain 99%+ coverage

## Testing

```bash
# Full suite
poetry run pytest tests/ -v

# By marker
poetry run pytest -m integration      # End-to-end tests
poetry run pytest -m version_compat   # Version compatibility
poetry run pytest -m security         # Security tests

# Single file
poetry run pytest tests/test_version_matrix.py -v
```

## Pull Request Checklist

- [ ] All tests pass (`poetry run pytest`)
- [ ] Coverage remains at 99%+
- [ ] Linters pass (`ruff check`, `mypy`, `black --check`)
- [ ] Commits are signed
- [ ] PR title follows conventional commit format
- [ ] New features include tests and documentation

## License

By contributing, you agree that your contributions will be licensed under
the [Apache License 2.0](LICENSE).
