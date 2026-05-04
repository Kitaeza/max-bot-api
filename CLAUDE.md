# python-max-bot — guidance for Claude

## What this is

Async Python client for the Max messenger Bot API. Pydantic v2 models,
httpx transport, MIT license. Ships to PyPI as `python-max-bot`.

Spec: `docs/design/0001-v0.1.md` is the source of truth for what's in
scope. Plan: `docs/plans/0001-v0.1-implementation.md`.

## Architecture (one screen)

- `src/max_bot_api/client.py` — `MaxClient` class, all public methods.
- `src/max_bot_api/transport.py` — httpx wrapper, auth header, error
  mapping. Don't add business logic here.
- `src/max_bot_api/exceptions.py` — `MaxError` hierarchy. Add a new
  subclass before mapping a new status code in `_STATUS_MAP`.
- `src/max_bot_api/models/` — Pydantic models, one file per concern
  (messages, attachments, keyboards, chats, updates, uploads).
- `src/max_bot_api/__init__.py` — flat re-export of every public type.
  Update both the imports and `__all__` whenever you expose something
  new.

## Conventions

- **Async-only.** Sync support is explicitly out of scope.
- **Request models** use `extra="forbid"` so user typos surface
  immediately. **Response models** use `extra="ignore"` so server-side
  field additions don't break existing clients.
- **Discriminated unions** for any "type field decides shape" — see
  `attachments.py` and `updates.py` as reference.
- **All optional method args are keyword-only** (`*` before them).
- **Local validation before HTTP.** Mutual-exclusion checks
  (chat_id/user_id), length caps (text), and content presence raise
  `ValueError` before any network call.
- **Auth header is bare** — `Authorization: <token>`, no `Bearer`
  prefix. Confirmed in the Max docs; do not "fix" it.
- **Retries are opt-in via `RetryPolicy`** (added in v0.2). `MaxClient`
  with no `retry=` argument behaves exactly like v0.1 — single attempt
  per call. The retry loop lives in `transport.py`; each `MaxClient`
  method tells the transport whether the call is `idempotent=` so writes
  don't double-apply on 5xx.
- **Spec/plan paths.** Specs go in `docs/design/NNNN-<name>.md`,
  plans in `docs/plans/NNNN-<name>-implementation.md`. Use these even
  when a skill suggests a different default location.

## Testing

- All tests are unit tests using `respx` to mock httpx. **No live API
  hits in CI.**
- Coverage gate is **90%** (configured in `pyproject.toml`).
- One test file per concern — match the source-file split.
- Use `@respx.mock` decorator on async tests; the loop scope is
  `function` (per-test).
- mypy strict needs explicit annotations on empty literals in test
  fixtures: `payload: dict[str, object] = {"members": [], ...}`,
  not `payload = {"members": [], ...}`.

## Common commands

```bash
uv sync                           # install + dev deps
uv run pytest                     # run tests
uv run pytest tests/test_X.py -v  # run a specific file
uv run ruff check                 # lint
uv run ruff format                # format
uv run mypy src tests             # type-check
uv build                          # build sdist + wheel
uv run python -c "..."            # no system `python` — always go through uv
```

## Releasing

- Pushing a `v*` tag fires `release.yml` → builds + publishes to PyPI
  via trusted publisher. Irreversible. Pause for explicit user consent
  before pushing a release tag.
- Smoke-install fresh: `uv pip install --no-cache --reinstall
  python-max-bot` — uv aggressively caches recent wheels and will
  silently pull the prior version.
- PyPI's `/pypi/<pkg>/json` endpoint can lag 1–2 min behind the
  release workflow (CDN). If it shows the old version, wait, don't
  re-publish.

## Style

- Line length 100, ruff rules `E, F, I, N, W, B, UP, SIM`.
- mypy `--strict` (configured in `pyproject.toml`).
- Comments only when the *why* is non-obvious. The Max API docs cover
  the *what*; don't restate them.
- Commit messages: terse subject, body explains *why* not *what*.
  Co-author with Claude on AI-assisted commits.

## Scope guard

If a request would expand v0.1 beyond the design doc, surface it as a
v0.2 candidate in `docs/design/0001-v0.1.md` (Roadmap section) instead
of building it. The "thin, stable, predictable" promise is the
project's reason for existing.
