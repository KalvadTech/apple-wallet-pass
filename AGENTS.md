# AGENTS.md

Guidance for AI coding agents working on this repository.

## Project overview

`apple-wallet-pass` is a Python library that generates Apple Wallet passes (`.pkpass` files). It is a fork (by KalvadTech) of the original Primedigital Global project, modernized to use the `cryptography` library instead of M2Crypto for signing.

A `.pkpass` file is a ZIP archive containing:

- `pass.json` — the pass definition (structure, fields, colors, barcode, etc.)
- `manifest.json` — SHA1 hashes of every file in the archive
- `signature` — a PKCS#7 detached signature (DER encoded) of the manifest
- Image/asset files added by the user (e.g. `icon.png`, `logo.png`)

**Important:** SHA1 hashing is mandated by Apple's pass format. The `S324`/`S303` ruff (bandit) warnings are intentionally suppressed in `apple_pass.py` — do not "fix" them by upgrading the hash algorithm.

## Technology stack

- **Language:** Python `^3.11` (CI tests 3.11, 3.12, 3.13)
- **Packaging/dependency management:** [uv](https://docs.astral.sh/uv/) (PEP 621 `pyproject.toml`, `uv_build` build backend, `src` layout)
- **Local environment:** [mise](https://mise.jdx.dev/) — `.mise.toml` pins Python 3.13 + uv and auto-activates the venv at `.venv/`
- **Runtime dependency:** `cryptography >= 38.0.4` (only one)
- **Dev dependency:** `ruff >=0.8.1,<0.9` (linter), in the PEP 735 `dev` dependency group
- **CI/CD:** GitHub Actions (`.github/workflows/`)

## Repository layout

```
├── pyproject.toml              # PEP 621 project definition, dependencies
├── uv.lock                     # Locked dependency versions
├── ruff.toml                   # Ruff linter configuration
├── .mise.toml                  # mise: Python + uv versions, venv location
├── .editorconfig               # Indentation, line length, isort settings
├── src/
│   ├── __init__.py             # Empty
│   └── apple_wallet_pass/      # The installable package
│       ├── __init__.py         # __version__ / __author__ metadata
│       ├── apple_pass.py       # ApplePass dataclass: pass.json, manifest, signing, zip
│       ├── fields.py           # Field, DateField, NumberField, CurrencyField, Barcode, Location, IBeacon
│       ├── pass_information.py # PassInformation base + BoardingPass, Coupon, EventTicket, Generic, StoreCard
│       └── enums.py            # Alignment, BarcodeFormat, TransitType, DateStyle, NumberStyle
└── .github/
    ├── workflows/build.yml     # Lint + install check on every push/PR
    ├── workflows/publish.yml   # PyPI publish + GitHub release on version tags
    └── pull_request_template.md
```

## Build and test commands

```bash
# Install dependencies into .venv/ (mise users: auto-activated)
uv sync

# Lint (this is what CI runs — there is no separate test step)
uv run ruff check .

# Build distribution archives
uv build
```

There is **no test suite** in this repository: no `tests/` directory, no pytest dependency, and CI only runs `uv sync --locked` plus ruff. If you add tests, you will be introducing the testing setup from scratch — mention this in your change.

## CI and release process

- **Build workflow** (`.github/workflows/build.yml`): runs on every push and pull request, on Python 3.11/3.12/3.13 (ubuntu-latest). Steps: checkout → `astral-sh/setup-uv@v6` (installs uv + the matrix Python) → `uv sync --locked` → `astral-sh/ruff-action@v1`. A change is only mergeable if it installs cleanly and passes ruff.
- **Publish workflow** (`.github/workflows/publish.yml`): runs when a tag matching `*.*.*` is pushed. It builds with `uv build`, publishes to PyPI with `uv publish` using the `PYPI_TOKEN` secret (passed as `UV_PUBLISH_TOKEN`), then creates a GitHub release with notes extracted from `docs/changelog.md`. Note: `docs/changelog.md` does **not** currently exist in the repo, so release-note extraction produces nothing until that file is created. When making a user-facing change, consider whether the changelog file needs to be added/updated and the version in `pyproject.toml` bumped.
- The PR template (`.github/pull_request_template.md`) asks contributors to update documentation and the changelog and to confirm the code is linted.

## Code style guidelines

- Formatting follows `.editorconfig`: UTF-8, LF line endings, final newline, trimmed trailing whitespace, 4-space indent for Python, 2-space indent for `*.{html,css,scss,json,yml}`.
- Line length 88 (isort setting in `.editorconfig`; keep within it even though ruff's line-length rules are not enabled).
- Ruff lint rules enabled (`ruff.toml`): `F` (pyflakes), `S` (bandit security), `ERA` (no commented-out code), `I` (isort import sorting), `C90` (mccabe complexity). The `env` directory is excluded.
- Import ordering follows isort settings in `.editorconfig`: `apple_wallet_pass` is the known first-party package. Existing code uses section heading comments such as `# Standard Library` and `# Third Party Stuff` — keep imports grouped accordingly.
- Type hints are used throughout public APIs; add them to new code.
- Docstrings follow a Google-style `Args:` / `Returns:` / `Raises:` format; match the surrounding style.
- JSON serialization uses Apple's camelCase PassKit keys (`passTypeIdentifier`, `headerFields`, …) while Python attributes use snake_case. Each model class implements a `json_dict()` method that performs this mapping — extend that pattern rather than serializing objects directly. `apple_pass.pass_handler()` is the custom `json.dumps` default that calls `json_dict()`.
- `fields.py` classes use private underscore attributes with `@property` accessors; `pass_information.py` and `apple_pass.py` use `@dataclass`. Follow the pattern of the module you are editing.
- Enum values in `enums.py` are `str` subclasses holding the exact Apple `PK*` constants (e.g. `PKBarcodeFormatQR`) and are marked `@unique`.

## Security considerations

- Creating a pass requires real Apple-issued credentials: a pass certificate (`.pem`), its private key (`.pem`, usually password-protected), and Apple's WWDR intermediate certificate (`.pem`). These must **never** be committed to the repository.
- `ApplePass.create()` reads certificate/key paths and optionally a private-key password. Never hardcode credentials, passwords, or certificate contents in source or examples.
- Signing uses PKCS#7 with SHA1 via the `cryptography` package — this is Apple's required scheme, not a weakness to fix.
- Bandit security rules (`S`) are enabled in ruff; do not blanket-disable them. The only existing suppression is `# ruff: noqa: S324, S303` at the top of `apple_pass.py` for the Apple-mandated SHA1 usage.

## Usage notes for agents

- The package is imported as `apple_wallet_pass` (from `src/`); the distribution name on PyPI is `apple-wallet-pass`.
- Typical flow: build a `PassInformation` subclass (e.g. `EventTicket`), add fields, create an `ApplePass` with it, attach asset files via `add_file(name, bytes_or_BytesIO)`, then call `create(certificate, key, wwdr_certificate, pass_path, password=...)`.
- Known inconsistencies to be aware of (do not blindly "clean up" without checking intent):
  - `src/apple_wallet_pass/__init__.py` still reports `__version__ = "0.0.2"` and `__author__ = "Primedigital Global"`, while `pyproject.toml` says version `0.1.0`, author Loic Tosser (KalvadTech).
  - The README's Usage section is a TODO.
- Apple reference docs (linked from the README): Wallet Developer Guide, PassKit Package Format Reference.
