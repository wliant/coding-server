# Data Model: Cross-Platform Build Tool

**Feature**: 003-cross-platform-build
**Date**: 2026-03-03

## Overview

This feature introduces no new data entities, database tables, or persistent state. It is a developer tooling migration (Makefile → Taskfile.yml) that modifies only configuration files at the repository root.

## Configuration Entities

### Taskfile.yml (Task Definition File)

The single configuration artifact introduced by this feature.

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Taskfile schema version — always `'3'` |
| `dotenv` | string[] | Global list of `.env` files to load (default: `['.env']`) |
| `tasks` | map | Named task definitions |

### Task (within Taskfile.yml)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `desc` | string | Yes | One-line description shown by `task --list` |
| `summary` | string | No | Multi-line description shown by `task --summary <name>` |
| `cmds` | string[] | Yes | Ordered list of shell commands to execute |
| `deps` | string[] | No | Tasks to run before this task (run concurrently) |
| `dotenv` | string[] | No | Per-task env file override (replaces global `dotenv`) |
| `vars` | map | No | Task-local variables for interpolation |

## Files Changed

| File | Change | Notes |
|------|--------|-------|
| `Taskfile.yml` | Created | Root-level task runner configuration |
| `Makefile` | Deleted | Replaced by `Taskfile.yml` per FR-009 |
| `CLAUDE.md` | Updated | `make <target>` → `task <target>` throughout |
| `README.md` | Created | New file; installation instructions + task reference |
| `.github/workflows/ci.yml` | Created | GitHub Actions CI using `go-task/setup-task@v1` |
| `.gitignore` | Updated | Add `.task/` cache directory |
