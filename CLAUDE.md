# Project Instructions for AI Agents

This file provides instructions and context for AI coding agents working on this project.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files
- This repo uses embedded `bd` in local-only mode; do not run `bd dolt push` unless a Dolt remote is explicitly configured later
- Embedded `bd` is single-writer; avoid overlapping mutating `bd` commands from multiple agents or shells

## Session Completion

**When ending a work session**, complete the local workflow below.

**LOCAL WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Review local git state**:
   ```bash
   git status
   ```
5. **Commit intentionally when appropriate** - Keep local commits focused and descriptive
6. **Publish only when asked** - If Sir Jolly Roger asks to publish work, use a feature branch and PR workflow; do not push `main`
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Do not treat `git push` as required for local completion in this repo
- Do not run `bd dolt push` in this repo unless a Dolt remote is intentionally configured
- If publishing is requested, never push directly to `main`; use a feature branch and PR
<!-- END BEADS INTEGRATION -->


## Build & Test

_Add your build and test commands here_

```bash
# Example:
# npm install
# npm test
```

## Architecture Overview

**Apana (Parlor)** teaches beginner Mandarin to English-speaking users through short spoken examples with pinyin and translation, entirely on-device.

**Stack:** FastAPI WebSocket server, Gemma 4 E2B via LiteRT-LM, local TTS (mlx-audio on macOS, kokoro-onnx for English on Linux), browser VAD/playback, plain HTML/CSS/JS frontend.

**Design doc:** `doc/plans/2026-04-07-mandarin-teacher-design.md`

## Conventions & Patterns

_Add your project-specific conventions here_
