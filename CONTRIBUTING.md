# Contributing to cad-tui

Thanks for your interest in improving cad-tui. This document covers how the
project is branched, how to set up a dev environment, and what's expected of
a pull request.

## Branch strategy

- `master` — stable, released code. Every commit on `master` corresponds to a
  published PyPI release tagged `vX.Y.Z`.
- `development` — integration branch for the next release. Every commit here
  corresponds to a TestPyPI pre-release tagged `dev-vX.Y.Z`.

Feature work branches off `development` and is merged back via pull request.
`master` only receives merges from `development` when cutting a release.
Direct pushes to `master` are disabled — all changes go through a PR with
passing CI.

## Development setup

```bash
git clone https://github.com/AyirusZone/cad_tui.git
cd cad_tui
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Testing

```bash
pytest -q
pytest --cov=cad_tui --cov-report=term-missing --cov-report=xml --cov-report=html
```

## Linting, formatting, type checking

```bash
ruff check src tests
black --check src tests
mypy src
```

`ruff` and `black` also run automatically on commit once `pre-commit install`
has been run (see `.pre-commit-config.yaml`). Run `black src tests` and
`ruff check --fix src tests` to apply fixes locally.

## Packaging

```bash
python -m build
twine check dist/*
```

## Versioning and releases

cad-tui follows [Semantic Versioning](https://semver.org/). Release
mechanics (tagging, publishing) are documented in the "Release process"
section of [README.md](README.md) — contributors don't need to cut releases
themselves, only maintainers do, once a PR has landed on `development` or
`master`.

## Making a pull request

1. Fork the repo and branch off `development`.
2. Make your change, adding or updating tests as needed.
3. Ensure `ruff`, `black --check`, `mypy`, and `pytest` all pass locally.
4. Open a PR against `development` describing what changed and why.
5. CI must pass before merge; at least one review is required.

By contributing, you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.md).
