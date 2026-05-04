# Contributing to max-bot-api

Thanks for your interest! This guide covers the dev loop for both human
and Claude-assisted contributors.

## Setup

```bash
git clone https://github.com/Kitaeza/max-bot-api
cd max-bot-api
uv sync
```

## Inner loop

```bash
uv run pytest                # run tests
uv run ruff check            # lint
uv run ruff format           # format
uv run mypy src tests        # type-check
```

CI runs all four on every PR; please run them locally first.

## Working with Claude

This repo ships with `CLAUDE.md` (project conventions) and
`.claude/settings.json` (safe-default tool permissions). Open the repo in
[Claude Code](https://claude.com/claude-code) and Claude will pick up both
automatically. The committed permissions allow read/test/lint/format/build
without prompting; `git push`, `uv publish`, and other remote actions still
require explicit approval.

If you don't use Claude, just ignore the `.claude/` directory.

## Pull requests

- Branch from `main`. Keep PRs small and focused.
- Tests required for new features and bug fixes.
- New public API additions must update `__init__.py` exports and the
  README feature matrix.
- Update `CHANGELOG.md` under `## [Unreleased]`.
- Ensure CI is green before requesting review.

## Reporting issues

Use the issue templates in `.github/ISSUE_TEMPLATE/`. For API behavior
questions, link the relevant section of [the Max API
docs](https://dev.max.ru/docs-api).

## Scope

v0.1 is intentionally narrow — see [docs/design/0001-v0.1.md](docs/design/0001-v0.1.md).
Out-of-scope features (handlers, FSM, retries, webhook server) belong to
later versions or different libraries entirely. Please open an issue to
discuss before implementing anything not listed in the roadmap.
