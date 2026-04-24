# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Layout

This directory is a wrapper around the actual project at `WealthBot/`. All source code, configs, and tooling live one level down.

**Canonical guidance:** See [`WealthBot/CLAUDE.md`](WealthBot/CLAUDE.md) — read it before working in this repo.

When running commands, `cd WealthBot/` first (or use absolute paths). The inner `CLAUDE.md` documents:

- Backend (FastAPI, Python 3.12) / Frontend (Next.js 16) / ML (ONNX) commands
- Architecture: `app/` (API), `frontend/src/`, `ml/` (training + inference)
- Critical constraints: `Numeric(15,2)` for money, `run_in_threadpool()` for ONNX, `MIN_TRANSACTIONS_FOR_ML = 10` cold-start gate
- Code style (Black/Ruff/MyPy, TS strict) and known gotchas (schema/ORM currency default mismatch, rule-based AI chat, tests require real Postgres)
- Demo access: credentials live in `DEMO_ACCESS.md` (gitignored) or `DEMO_EMAIL`/`DEMO_PASSWORD` env vars — never committed
